import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.rq4_finalize_report import (
    CONDITIONS,
    build_report_artifacts,
    condition_metrics,
)


def report_fixture(root):
    labels = ["concurrency", "memory", "semantic", "concurrency", "memory"]
    folds = pd.DataFrame({
        "url": [f"u{i}" for i in range(5)],
        "project": [f"p{i}" for i in range(5)],
        "fold_id": list(range(5)),
    })
    gold = folds.assign(root_cause=labels)
    rows = []
    for condition in CONDITIONS:
        for i, row in folds.iterrows():
            rows.append({
                **row.to_dict(),
                "model_id": f"model_{row['fold_id']}",
                "y_true": labels[i],
                "prediction": labels[i],
                "condition": condition,
            })
    predictions = pd.DataFrame(rows)
    metrics = pd.DataFrame([
        {"condition": condition, **condition_metrics(
            predictions[predictions["condition"] == condition]
        )}
        for condition in CONDITIONS
    ])
    control = folds.assign(
        n_units=2,
        b2_unit_id="description_p0",
        b2_char_len=40,
        b3_unit_id=["description_p1"] * 4 + [None],
        b3_matchable=[True] * 4 + [False],
        b3_char_len=[42] * 4 + [None],
        b3_length_delta=[2] * 4 + [None],
    )
    b0 = predictions[predictions["condition"] == "B0_no_reveal"]
    b3 = predictions[predictions["condition"] == "B3_same_type_control"]
    paired = b0[["url", "project", "fold_id", "y_true", "prediction"]].rename(
        columns={"prediction": "prediction_b0"}
    ).merge(
        b3[["url", "prediction"]].rename(
            columns={"prediction": "prediction_b3"}
        ),
        on="url",
    )
    paired["b0_correct"] = paired["prediction_b0"] == paired["y_true"]
    paired["b3_correct"] = paired["prediction_b3"] == paired["y_true"]
    paired["change"] = "unchanged"
    units = pd.DataFrame([
        {
            "url": row.url,
            "unit_id": f"description_p{i}",
            "source_field": "description",
            "overlap_flag": False,
        }
        for row in folds.itertuples()
        for i in range(2)
    ])
    manifest = folds.assign(
        eligible_robust_no_comments=True,
    )
    bootstrap = pd.DataFrame([{
        "comparison": "B3_same_type_control_minus_B0",
        "macro_f1_ci_low": -0.1,
        "macro_f1_ci_high": 0.1,
        "accuracy_ci_low": -0.1,
        "accuracy_ci_high": 0.1,
        "resamples": 5000,
        "method": "paired project-cluster bootstrap",
    }])
    return {
        "predictions": predictions,
        "metrics": metrics,
        "folds": folds,
        "control": control,
        "paired": paired,
        "bootstrap": bootstrap,
        "unit_audit": units,
        "unit_manifest": manifest,
        "gold": gold,
    }


def test_reporting_generator_is_report_only_and_preserves_archives(tmp_path):
    root = tmp_path
    archive_paths = [
        root / "results" / "rq4" / "v1" / "historic.csv",
        root / "results" / "rq4" / "v2" / "historic.csv",
    ]
    for path in archive_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unchanged\n", encoding="utf-8")
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in archive_paths
    }

    script_path = Path(__file__).parents[1] / "scripts" / "rq4_finalize_report.py"
    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "sklearn.metrics" in imported_modules
    assert not any(
        module and module.startswith("sklearn.") and module != "sklearn.metrics"
        for module in imported_modules
    )
    assert not any(
        isinstance(node, ast.Attribute) and node.attr in {"fit", "fit_transform"}
        for node in ast.walk(tree)
    )

    inputs = report_fixture(root)
    result = build_report_artifacts(
        root=root,
        output_dir=root / "report",
        inputs=inputs,
        register_hashes={},
        revision="fixture",
        script_hash="fixture",
        strict=False,
    )
    assert result["status"] == "PASS"
    assert result["primary_table_rows"] == 4
    assert result["matchable_subset_table_rows"] == 2
    assert result["matchable_subset_reports"] == 4
    assert (root / "report" / "table_primary.csv").is_file()
    primary = pd.read_csv(root / "report" / "table_primary.csv")
    assert primary["condition"].tolist() == [
        "B0_no_reveal",
        "B3_same_type_control",
        "B1_random_10_seed_summary",
        "REF_all_units",
    ]
    assert primary["n_reports"].tolist() == [5, 5, 5, 5]
    assert primary["projects"].tolist() == [5, 5, 5, 5]
    assert not primary["condition"].str.startswith("B5_").any()
    assert not primary["cohort"].str.contains("matchable reports only").any()

    matchable_subset = pd.read_csv(
        root / "report" / "table_matchable_subset.csv"
    )
    assert matchable_subset["condition"].tolist() == [
        "B0_no_reveal",
        "B3_same_type_control",
    ]
    assert matchable_subset["n_reports"].tolist() == [4, 4]
    assert matchable_subset["cohort"].str.contains(
        "B3-matchable reports only"
    ).all()
    assert matchable_subset["limitation"].str.contains(
        "descriptive only; different cohort; not comparable to "
        "295-report absolute scores",
        case=False,
        regex=False,
    ).all()

    supplementary = pd.read_csv(root / "report" / "table_supplementary.csv")
    assert {f"B1_seed_{seed}" for seed in range(10)}.issubset(
        set(supplementary["condition"])
    )
    assert {"B2_length_control", "B4_type_preference"}.issubset(
        set(supplementary["condition"])
    )
    assert not supplementary["condition"].isin(
        ["B3_same_type_control", "B5_v1_target_reference"]
    ).any()

    invalid_debug = pd.read_csv(root / "report" / "table_invalid_debug.csv")
    assert invalid_debug["condition"].tolist() == ["B5_v1_target_reference"]
    assert invalid_debug["prediction_identity"].str.contains(
        "identical to B2"
    ).all()

    classwise = pd.read_csv(root / "report" / "table_classwise.csv")
    assert classwise.groupby("condition")["cohort_n"].unique().apply(
        lambda values: list(values) == [5]
    ).all()
    assert classwise.groupby("condition")["class_support"].sum().eq(5).all()

    for condition in ["B0_no_reveal", "B3_same_type_control", "REF_all_units"]:
        metric = condition_metrics(
            inputs["predictions"][
                inputs["predictions"]["condition"] == condition
            ]
        )
        row = primary.loc[primary["condition"] == condition].iloc[0]
        assert row["macro_f1"] == metric["macro_f1"]
        assert row["accuracy"] == metric["accuracy"]
    expected_b1_mean = np.mean([
        condition_metrics(
            inputs["predictions"][
                inputs["predictions"]["condition"] == f"B1_seed_{seed}"
            ]
        )["macro_f1"]
        for seed in range(10)
    ])
    b1_row = primary.loc[
        primary["condition"] == "B1_random_10_seed_summary"
    ].iloc[0]
    assert b1_row["macro_f1"] == expected_b1_mean

    bootstrap_output = pd.read_csv(root / "report" / "bootstrap_ci.csv")
    pd.testing.assert_frame_equal(bootstrap_output, inputs["bootstrap"])
    provenance = json.loads(
        (root / "report" / "provenance.json").read_text(encoding="utf-8")
    )
    assert provenance["input_sha256"][
        "results/rq4/v2/reveal_predictions.csv"
    ] == hashlib.sha256(
        inputs["predictions"].to_csv(index=False).encode("utf-8")
    ).hexdigest()
    assert provenance["input_sha256"][
        "results/rq4/v2/bootstrap_ci.csv"
    ] == hashlib.sha256(
        inputs["bootstrap"].to_csv(index=False).encode("utf-8")
    ).hexdigest()

    assert not (root / "results" / "rq4" / "v1" / "table_primary.csv").exists()
    assert not (root / "results" / "rq4" / "v2" / "table_primary.csv").exists()
    after = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in archive_paths
    }
    assert before == after
