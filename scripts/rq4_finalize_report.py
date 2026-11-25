"""Reproduce final RQ4 report tables from immutable saved predictions."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.metrics import precision_recall_fscore_support


LABELS = ["concurrency", "memory", "semantic"]
CONDITIONS = [
    "B0_no_reveal",
    *(f"B1_seed_{seed}" for seed in range(10)),
    "B2_length_control",
    "B3_same_type_control",
    "B4_type_preference",
    "B5_v1_target_reference",
    "REF_all_units",
]
REGISTER_HASH_PATTERN = re.compile(
    r"^\|\s*`(?P<path>[^`]+)`\s*\|.*\|\s*`(?P<digest>[0-9a-f]{64})`\s*\|$",
    re.MULTILINE,
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_register_hashes(register_path):
    text = Path(register_path).read_text(encoding="utf-8")
    return {
        match.group("path"): match.group("digest")
        for match in REGISTER_HASH_PATTERN.finditer(text)
    }


def verify_register(root, register_path):
    expected = read_register_hashes(register_path)
    if not expected:
        raise ValueError(f"No SHA-256 entries found in {register_path}")
    mismatches = []
    for relative_path, expected_hash in expected.items():
        path = Path(root) / relative_path
        if not path.is_file():
            mismatches.append(f"missing registered file: {relative_path}")
        elif sha256(path) != expected_hash:
            mismatches.append(f"hash mismatch: {relative_path}")
    if mismatches:
        raise ValueError("Artifact register validation failed: " + "; ".join(mismatches))
    return expected


def condition_metrics(frame):
    return {
        "n": int(len(frame)),
        "projects": int(frame["project"].nunique()),
        "macro_f1": float(f1_score(
            frame["y_true"], frame["prediction"],
            average="macro", labels=LABELS, zero_division=0,
        )),
        "accuracy": float(accuracy_score(frame["y_true"], frame["prediction"])),
        "confusion_matrix": confusion_matrix(
            frame["y_true"], frame["prediction"], labels=LABELS
        ).tolist(),
    }


def _validate(root, predictions, saved_metrics, folds, control_audit,
              saved_pairs, bootstrap, unit_audit, unit_manifest, gold,
              strict):
    required_conditions = set(CONDITIONS)
    if set(predictions["condition"].unique()) != required_conditions:
        raise ValueError("Prediction conditions do not match the 16 expected conditions")
    if predictions.duplicated(["url", "condition"]).any():
        raise ValueError("Duplicate URL/condition prediction rows")
    if predictions[["url", "project", "fold_id", "y_true", "prediction"]].isna().any().any():
        raise ValueError("Missing prediction identity or label values")
    if not set(predictions["prediction"].unique()).issubset(LABELS):
        raise ValueError("Unexpected predicted label")
    if not set(predictions["y_true"].unique()).issubset(LABELS):
        raise ValueError("Unexpected gold label")
    if predictions.groupby("condition")["url"].nunique().nunique() != 1:
        raise ValueError("Conditions have different report counts")

    identities = predictions.groupby("url").agg(
        project_count=("project", "nunique"),
        fold_count=("fold_id", "nunique"),
        label_count=("y_true", "nunique"),
        model_count=("model_id", "nunique"),
    )
    if identities.max().max() != 1:
        raise ValueError("A report has inconsistent project, fold, label, or model identity")

    if folds.duplicated(["url"]).any():
        raise ValueError("Duplicate URLs in fold map")
    if folds.groupby("project")["fold_id"].nunique().max() != 1:
        raise ValueError("A project spans multiple outer test folds")
    if set(folds["url"]) != set(predictions["url"]):
        raise ValueError("Fold map and prediction cohort URLs differ")
    pred_ids = predictions[["url", "project", "fold_id"]].drop_duplicates()
    fold_ids = folds[["url", "project", "fold_id"]].drop_duplicates()
    if len(pred_ids.merge(fold_ids, how="outer", indicator=True).query("_merge != 'both'")):
        raise ValueError("Prediction project/fold assignments differ from fold_map.csv")

    gold_subset = gold.set_index("url").reindex(folds["url"])
    if gold_subset[["project", "root_cause"]].isna().any().any():
        raise ValueError("Some evaluated reports are absent from frozen gold")
    expected = folds.set_index("url").join(
        gold.set_index("url")[["root_cause"]],
        how="left",
    )
    identity_check = predictions[["url", "project", "y_true"]].drop_duplicates().set_index("url")
    gold_identity = expected[["project", "root_cause"]].rename(
        columns={"root_cause": "y_true"}
    )
    identity_check = identity_check.reindex(gold_identity.index)
    if not identity_check.equals(gold_identity):
        raise ValueError("Saved prediction labels/projects do not align with frozen gold")

    counts = predictions.groupby("condition")["url"].nunique()
    if strict and (len(folds) != 295 or folds["url"].nunique() != 295
                   or folds["project"].nunique() != 58
                   or folds["fold_id"].nunique() != 5):
        raise ValueError("Expected 295 URLs, 58 projects, and five folds")
    if strict and not counts.eq(295).all():
        raise ValueError("Each condition must contain 295 unique reports")

    saved = saved_metrics.set_index("condition")
    if set(saved.index) != required_conditions:
        raise ValueError("Saved metrics do not contain exactly 16 conditions")
    recomputed = {}
    for condition, frame in predictions.groupby("condition", sort=False):
        values = condition_metrics(frame)
        recomputed[condition] = values
        if not np.isclose(
            values["macro_f1"], saved.loc[condition, "macro_f1"],
            atol=1e-6, rtol=0.0,
        ):
            raise ValueError(f"Saved macro-F1 differs for {condition}")
        if not np.isclose(
            values["accuracy"], saved.loc[condition, "accuracy"],
            atol=1e-6, rtol=0.0,
        ):
            raise ValueError(f"Saved accuracy differs for {condition}")

    if control_audit.duplicated("url").any() or set(control_audit["url"]) != set(folds["url"]):
        raise ValueError("Control match audit does not align to cohort")
    matchable = control_audit["b3_matchable"].astype(bool)
    if strict and (int(matchable.sum()) != 252 or int((~matchable).sum()) != 43):
        raise ValueError("B3 match/fallback counts differ from the approved audit")
    for row in control_audit.loc[matchable].itertuples():
        if row.b2_unit_id == row.b3_unit_id:
            raise ValueError(f"B3 did not choose a distinct unit for {row.url}")
        b2_type = "description" if str(row.b2_unit_id).startswith("description") else str(row.b2_unit_id)
        b3_type = "description" if str(row.b3_unit_id).startswith("description") else str(row.b3_unit_id)
        if b2_type != b3_type:
            raise ValueError(f"B3 unit type mismatch for {row.url}")
    if not control_audit.loc[matchable, "b3_unit_id"].astype(str).str.startswith("description").all():
        raise ValueError("Successful B3 matches are not description-only")

    wide = predictions.pivot(index="url", columns="condition", values="prediction")
    if not wide["B2_length_control"].equals(wide["B5_v1_target_reference"]):
        raise ValueError("B2/B5 saved predictions are not identical")
    no_match_urls = control_audit.loc[~matchable, "url"]
    if not wide.loc[no_match_urls, "B0_no_reveal"].equals(
        wide.loc[no_match_urls, "B3_same_type_control"]
    ):
        raise ValueError("B3 no-match fallback predictions differ from B0")

    labels = predictions.drop_duplicates("url").set_index("url")["y_true"]
    b0 = wide["B0_no_reveal"]
    b3 = wide["B3_same_type_control"]
    outcomes = pd.DataFrame({
        "url": wide.index,
        "y_true": labels.reindex(wide.index).values,
        "b0_prediction": b0.values,
        "b3_prediction": b3.values,
    })
    outcomes["b0_correct"] = outcomes["b0_prediction"] == outcomes["y_true"]
    outcomes["b3_correct"] = outcomes["b3_prediction"] == outcomes["y_true"]
    outcomes["paired_change"] = np.select(
        [
            outcomes["b3_correct"] & ~outcomes["b0_correct"],
            ~outcomes["b3_correct"] & outcomes["b0_correct"],
        ],
        ["beneficial", "harmful"],
        default="unchanged",
    )
    saved_pair_index = saved_pairs.set_index("url").sort_index()
    computed_pair_index = outcomes.set_index("url").sort_index()
    for column in ["b0_correct", "b3_correct", "change"]:
        computed_column = "paired_change" if column == "change" else column
        if not saved_pair_index[column].equals(computed_pair_index[computed_column]):
            raise ValueError(f"Saved paired outcome differs for {column}")

    if len(bootstrap) != 1 or int(bootstrap.iloc[0]["resamples"]) != 5000:
        raise ValueError("Expected the archived 5,000-resample paired bootstrap result")

    robust_urls = set(
        unit_manifest.loc[
            unit_manifest["eligible_robust_no_comments"].astype(bool), "url"
        ]
    )
    if robust_urls != set(folds["url"]):
        raise ValueError("Robust no-comments manifest differs from evaluated cohort")
    if "unit_ids_robust_no_comments" in unit_manifest:
        robust_ids = unit_manifest.loc[
            unit_manifest["eligible_robust_no_comments"].astype(bool),
            "unit_ids_robust_no_comments",
        ].fillna("")
        if robust_ids.str.split("|").map(
            lambda ids: "comments_model" in ids
        ).any():
            raise ValueError("comments_model appears in robust candidate IDs")
    primary_units = unit_audit[
        unit_audit["url"].isin(robust_urls)
        & (unit_audit["source_field"] != "comments_model")
    ].copy()
    if primary_units["source_field"].eq("comments_model").any():
        raise ValueError("Comments found in primary unit inventory")
    if strict and (
        len(primary_units) != 2105
        or int(primary_units["overlap_flag"].astype(bool).sum()) != 368
        or primary_units.loc[primary_units["overlap_flag"].astype(bool), "url"].nunique() != 146
    ):
        raise ValueError("Primary unit/overlap counts differ from audited source")
    return recomputed, outcomes, primary_units


def build_report_artifacts(root, output_dir, inputs, register_hashes,
                           revision, script_hash, strict=True):
    output_dir = Path(output_dir).resolve()
    root = Path(root).resolve()
    forbidden = [
        (root / "results" / "rq4" / "v1").resolve(),
        (root / "results" / "rq4" / "v2").resolve(),
    ]
    rq4_root = (root / "results" / "rq4").resolve()
    final_root = (rq4_root / "final").resolve()
    if (output_dir == rq4_root
            or (rq4_root in output_dir.parents and output_dir != final_root)):
        raise ValueError("Report output under results/rq4 must use results/rq4/final")
    if any(output_dir == path or path in output_dir.parents for path in forbidden):
        raise ValueError("Report output must not overwrite v1/v2 archives")

    pred = inputs["predictions"]
    metrics_source = inputs["metrics"]
    folds = inputs["folds"]
    control = inputs["control"]
    saved_pairs = inputs["paired"]
    bootstrap = inputs["bootstrap"]
    unit_audit = inputs["unit_audit"]
    unit_manifest = inputs["unit_manifest"]
    gold = inputs["gold"]
    recomputed, outcomes, primary_units = _validate(
        root, pred, metrics_source, folds, control, saved_pairs, bootstrap,
        unit_audit, unit_manifest, gold, strict,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    full_metrics = {
        condition: condition_metrics(pred[pred["condition"] == condition])
        for condition in CONDITIONS
    }
    prediction_wide = pred.pivot(
        index="url", columns="condition", values="prediction"
    )
    b2_b5_identity_count = int(
        (prediction_wide["B2_length_control"]
         == prediction_wide["B5_v1_target_reference"]).sum()
    )
    ci = bootstrap.iloc[0]
    primary_rows = []

    def add_primary(condition, role, limitation, cohort, metric, delta=None,
                    ci_low=None, ci_high=None):
        primary_rows.append({
            "condition": condition,
            "role": role,
            "cohort": cohort,
            "n_reports": metric["n"],
            "projects": metric["projects"],
            "macro_f1": metric["macro_f1"],
            "accuracy": metric["accuracy"],
            "delta_macro_f1_vs_b0": delta,
            "b3_minus_b0_macro_f1_ci_low": ci_low,
            "b3_minus_b0_macro_f1_ci_high": ci_high,
            "limitation": limitation,
        })

    base = full_metrics["B0_no_reveal"]
    b3 = full_metrics["B3_same_type_control"]
    b3_matchable_count = int(control["b3_matchable"].astype(bool).sum())
    b3_fallback_count = int(len(control) - b3_matchable_count)
    b0_frame = pred[pred["condition"] == "B0_no_reveal"].set_index("url")
    b3_frame = pred[pred["condition"] == "B3_same_type_control"].set_index("url")
    b3_minus_b0 = b3["macro_f1"] - base["macro_f1"]
    add_primary(
        "B0_no_reveal", "Anchor", "Withheld-text reference; retrospective cohort.",
        f"full {len(folds)}-report cohort", base,
    )
    add_primary(
        "B3_same_type_control", "Main matched control",
        (
            "Same-type / nearest-available-length description unit for "
            f"{b3_matchable_count} reports; {b3_fallback_count} fall back to B0. "
            "CI includes zero."
        ),
        f"full {len(folds)}-report cohort with documented fallback", b3, b3_minus_b0,
        float(ci["macro_f1_ci_low"]), float(ci["macro_f1_ci_high"]),
    )

    b3_matched = control.loc[control["b3_matchable"].astype(bool), "url"]
    matched_b0 = condition_metrics(b0_frame.loc[b3_matched].reset_index())
    matched_b3 = condition_metrics(b3_frame.loc[b3_matched].reset_index())
    matchable_subset_rows = [
        {
            "condition": "B0_no_reveal",
            "role": "Descriptive matched-subset baseline",
            "cohort": f"{matched_b0['n']} B3-matchable reports only",
            "n_reports": matched_b0["n"],
            "projects": matched_b0["projects"],
            "macro_f1": matched_b0["macro_f1"],
            "accuracy": matched_b0["accuracy"],
            "delta_macro_f1_vs_b0": None,
            "limitation": (
                "Descriptive only; different cohort; not comparable to "
                "295-report absolute scores."
            ),
        },
        {
            "condition": "B3_same_type_control",
            "role": "Descriptive matched-subset control",
            "cohort": f"{matched_b3['n']} B3-matchable reports only",
            "n_reports": matched_b3["n"],
            "projects": matched_b3["projects"],
            "macro_f1": matched_b3["macro_f1"],
            "accuracy": matched_b3["accuracy"],
            "delta_macro_f1_vs_b0": (
                matched_b3["macro_f1"] - matched_b0["macro_f1"]
            ),
            "limitation": (
                "Descriptive only; different cohort; not comparable to "
                "295-report absolute scores; not a new confirmatory comparison."
            ),
        },
    ]

    seed_conditions = [f"B1_seed_{seed}" for seed in range(10)]
    seed_metrics = [full_metrics[condition] for condition in seed_conditions]
    primary_rows.append({
        "condition": "B1_random_10_seed_summary",
        "role": "Stochastic comparator",
        "cohort": f"{seed_metrics[0]['n']} reports per seed; 10 predeclared seeds",
        "n_reports": seed_metrics[0]["n"],
        "projects": seed_metrics[0]["projects"],
        "macro_f1": float(np.mean([m["macro_f1"] for m in seed_metrics])),
        "accuracy": float(np.mean([m["accuracy"] for m in seed_metrics])),
        "macro_f1_min": float(np.min([m["macro_f1"] for m in seed_metrics])),
        "macro_f1_max": float(np.max([m["macro_f1"] for m in seed_metrics])),
        "accuracy_min": float(np.min([m["accuracy"] for m in seed_metrics])),
        "accuracy_max": float(np.max([m["accuracy"] for m in seed_metrics])),
        "seed_count": len(seed_metrics),
        "limitation": "Mean and range across all seeds; not one paired classifier and no best-seed claim.",
    })
    ref = full_metrics["REF_all_units"]
    add_primary(
        "REF_all_units", "Retrospective context",
        "All allowed source units restored; retrospective reference, not a deployable policy or guaranteed ceiling.",
        f"full {len(folds)}-report cohort", ref,
    )
    primary_table = pd.DataFrame(primary_rows)
    expected_primary_conditions = [
        "B0_no_reveal",
        "B3_same_type_control",
        "B1_random_10_seed_summary",
        "REF_all_units",
    ]
    if primary_table["condition"].tolist() != expected_primary_conditions:
        raise ValueError("Primary report table must contain exactly the four approved rows")
    if (not primary_table["n_reports"].eq(len(folds)).all()
            or not primary_table["projects"].eq(folds["project"].nunique()).all()):
        raise ValueError("Primary report table rows do not share the full cohort")
    if primary_table["condition"].str.startswith("B5_").any():
        raise ValueError("B5 must not appear in the primary report table")
    primary_table.to_csv(output_dir / "table_primary.csv", index=False)
    pd.DataFrame(matchable_subset_rows).to_csv(
        output_dir / "table_matchable_subset.csv", index=False
    )

    supplementary_rows = []
    for condition in seed_conditions + ["B2_length_control", "B4_type_preference"]:
        metric = full_metrics[condition]
        supplementary_rows.append({
            "condition": condition,
            "n_reports": metric["n"],
            "projects": metric["projects"],
            "macro_f1": metric["macro_f1"],
            "accuracy": metric["accuracy"],
            "role": (
                "Random seed; supplementary, not best-seed selection"
                if condition.startswith("B1_")
                else (
                    "Shortest-unit sensitivity baseline"
                    if condition == "B2_length_control"
                    else "Training-fold type-preference sensitivity baseline"
                )
            ),
        })
    pd.DataFrame(supplementary_rows).to_csv(
        output_dir / "table_supplementary.csv", index=False
    )

    invalid = full_metrics["B5_v1_target_reference"]
    pd.DataFrame([{
        "condition": "B5_v1_target_reference",
        "status": "ARCHIVE - EXCLUDE FROM VALID POLICY COMPARISONS",
        "n_reports": invalid["n"],
        "macro_f1_debug_only": invalid["macro_f1"],
        "accuracy_debug_only": invalid["accuracy"],
        "prediction_identity": (
            f"{b2_b5_identity_count}/{len(prediction_wide)} predictions identical to B2"
        ),
        "reason": "V2 source constructs B5 from the same shortest-unit ID as B2; it does not reproduce the v1 hidden-content selector.",
    }]).to_csv(output_dir / "table_invalid_debug.csv", index=False)

    classwise_rows = []
    for condition in ["B0_no_reveal", "B3_same_type_control", "REF_all_units"]:
        frame = pred[pred["condition"] == condition]
        precision, recall, f1, support = precision_recall_fscore_support(
            frame["y_true"], frame["prediction"], labels=LABELS,
            zero_division=0,
        )
        for label, p_value, r_value, f_value, n_value in zip(
            LABELS, precision, recall, f1, support
        ):
            classwise_rows.append({
                "condition": condition,
                "class": label,
                "cohort_n": len(frame),
                "class_support": int(n_value),
                "precision": float(p_value),
                "recall": float(r_value),
                "f1": float(f_value),
            })
    pd.DataFrame(classwise_rows).to_csv(
        output_dir / "table_classwise.csv", index=False
    )

    matchable = control["b3_matchable"].astype(bool)
    abs_delta = control.loc[matchable, "b3_length_delta"].abs()
    overlap = primary_units["overlap_flag"].astype(bool)
    control_rows = [
        ("eligible_reports", len(folds), "reports"),
        ("eligible_projects", folds["project"].nunique(), "projects"),
        ("test_folds", folds["fold_id"].nunique(), "folds"),
        ("B3_matchable", int(matchable.sum()), "reports"),
        ("B3_no_reveal_fallback", int((~matchable).sum()), "reports"),
        ("B3_successful_match_type_description", int(
            control.loc[matchable, "b3_unit_id"].astype(str).str.startswith("description").sum()
        ), "reports"),
        ("B3_abs_length_delta_median", float(abs_delta.median()), "characters"),
        ("B3_abs_length_delta_q1", float(abs_delta.quantile(0.25)), "characters"),
        ("B3_abs_length_delta_q3", float(abs_delta.quantile(0.75)), "characters"),
        ("B3_abs_length_delta_max", float(abs_delta.max()), "characters"),
        ("no_comments_unit_rows", len(primary_units), "units"),
        ("overlap_flagged_units", int(overlap.sum()), "units"),
        ("reports_with_overlap_flags", primary_units.loc[overlap, "url"].nunique(), "reports"),
        ("comments_in_primary_inference_candidates", 0, "units; excluded by source"),
        ("comments_model_rows_in_broad_audit", int(
            unit_audit.loc[
                unit_audit["url"].isin(folds["url"])
                & (unit_audit["source_field"] == "comments_model"),
                "source_field",
            ].count()
        ), "units (must be zero in inference; broader audit contains comments)"),
        ("description_snapshot", "archived; filing-time exactness unverified", "temporal status"),
        ("code_stack_provenance", "extracted from description; overlap possible", "source status"),
        ("metadata_visibility", "candidate type/index/count/length derived from complete archived report", "limitation"),
    ]
    cohort_labels = (
        pred[pred["condition"] == "B0_no_reveal"]["y_true"]
        .value_counts()
        .to_dict()
    )
    for label in LABELS:
        control_rows.append((
            f"cohort_class_{label}",
            int(cohort_labels.get(label, 0)),
            "reports",
        ))
    for source_field, count in primary_units["source_field"].value_counts().items():
        control_rows.append((f"unit_type_{source_field}", int(count), "units"))
    for source_field, count in primary_units.loc[overlap, "source_field"].value_counts().items():
        control_rows.append((f"overlap_flagged_type_{source_field}", int(count), "units"))
    pd.DataFrame(control_rows, columns=["measure", "value", "unit"]).to_csv(
        output_dir / "cohort_and_controls.csv", index=False
    )

    outcomes.to_csv(output_dir / "paired_outcomes.csv", index=False)
    bootstrap.to_csv(output_dir / "bootstrap_ci.csv", index=False)
    input_hash_paths = [
            "data/processed/gold_v1.csv",
            "results/rq4/v2/reveal_predictions.csv",
            "results/rq4/v2/metrics.csv",
            "results/rq4/v2/fold_map.csv",
            "results/rq4/v2/control_match_audit.csv",
            "results/rq4/v2/paired_differences.csv",
            "results/rq4/v2/bootstrap_ci.csv",
            "results/rq4/v2/unit_audit.csv",
            "results/rq4/v2/unit_manifest_v2.csv",
    ]
    input_hashes = {}
    for path in input_hash_paths:
        source_path = root / path
        if source_path.is_file():
            input_hashes[path] = sha256(source_path)
        elif strict:
            raise FileNotFoundError(f"Missing report input file: {source_path}")
        else:
            frame_key = {
                "data/processed/gold_v1.csv": "gold",
                "results/rq4/v2/reveal_predictions.csv": "predictions",
                "results/rq4/v2/metrics.csv": "metrics",
                "results/rq4/v2/fold_map.csv": "folds",
                "results/rq4/v2/control_match_audit.csv": "control",
                "results/rq4/v2/paired_differences.csv": "paired",
                "results/rq4/v2/bootstrap_ci.csv": "bootstrap",
                "results/rq4/v2/unit_audit.csv": "unit_audit",
                "results/rq4/v2/unit_manifest_v2.csv": "unit_manifest",
            }[path]
            serialized = inputs[frame_key].to_csv(index=False).encode("utf-8")
            input_hashes[path] = hashlib.sha256(serialized).hexdigest()
    provenance = {
        "experiment_id": "rq4_final_report_v1",
        "git_revision": revision,
        "report_script": "scripts/rq4_finalize_report.py",
        "report_script_sha256": script_hash,
        "artifact_register": "docs/rq4/RQ4_ARTIFACT_REGISTER.md",
        "registered_file_hashes_verified": len(register_hashes),
        "input_sha256": input_hashes,
        "cohort": {
            "reports": len(folds),
            "projects": int(folds["project"].nunique()),
            "folds": int(folds["fold_id"].nunique()),
        },
        "metrics_recomputed_from": "results/rq4/v2/reveal_predictions.csv",
        "bootstrap": {
            "source": "results/rq4/v2/bootstrap_ci.csv",
            "recomputed": False,
            "resamples": int(bootstrap.iloc[0]["resamples"]),
            "method": bootstrap.iloc[0]["method"],
        },
        "report_cleanup_training_or_selector_runs": False,
        "historical_v1_v2_inputs_modified": False,
    }
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    if len(primary_table) != 4 or len(matchable_subset_rows) != 2:
        raise ValueError("Final report table row counts do not match approved format")
    validation = {
        "status": "PASS",
        "condition_count": len(CONDITIONS),
        "prediction_rows": int(len(pred)),
        "reports_per_condition": int(counts_per_condition(pred).iloc[0]),
        "reports": int(folds["url"].nunique()),
        "projects": int(folds["project"].nunique()),
        "folds": int(folds["fold_id"].nunique()),
        "B3_matches": int(matchable.sum()),
        "B3_fallbacks": int((~matchable).sum()),
        "B2_B5_identical_predictions": int(
            b2_b5_identity_count
        ),
        "paired_B3_beneficial": int((outcomes["paired_change"] == "beneficial").sum()),
        "paired_B3_harmful": int((outcomes["paired_change"] == "harmful").sum()),
        "paired_B3_unchanged": int((outcomes["paired_change"] == "unchanged").sum()),
        "primary_table_rows": int(len(primary_table)),
        "primary_table_conditions": primary_table["condition"].tolist(),
        "matchable_subset_table_rows": len(matchable_subset_rows),
        "matchable_subset_reports": int(matched_b0["n"]),
        "register_hashes_verified": len(register_hashes),
        "training_performed": False,
    }
    (output_dir / "validation.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    return validation


def counts_per_condition(predictions):
    return predictions.groupby("condition")["url"].nunique()


def main():
    root = Path(__file__).resolve().parents[1]
    register = root / "docs" / "rq4" / "RQ4_ARTIFACT_REGISTER.md"
    register_hashes = verify_register(root, register)
    v2 = root / "results" / "rq4" / "v2"
    inputs = {
        "predictions": pd.read_csv(v2 / "reveal_predictions.csv"),
        "metrics": pd.read_csv(v2 / "metrics.csv"),
        "folds": pd.read_csv(v2 / "fold_map.csv"),
        "control": pd.read_csv(v2 / "control_match_audit.csv"),
        "paired": pd.read_csv(v2 / "paired_differences.csv"),
        "bootstrap": pd.read_csv(v2 / "bootstrap_ci.csv"),
        "unit_audit": pd.read_csv(v2 / "unit_audit.csv"),
        "unit_manifest": pd.read_csv(v2 / "unit_manifest_v2.csv"),
        "gold": pd.read_csv(root / "data" / "processed" / "gold_v1.csv"),
    }
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    output_dir = root / "results" / "rq4" / "final"
    validation = build_report_artifacts(
        root=root,
        output_dir=output_dir,
        inputs=inputs,
        register_hashes=register_hashes,
        revision=revision,
        script_hash=sha256(__file__),
        strict=True,
    )
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
