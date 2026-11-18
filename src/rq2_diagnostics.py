"""Post-hoc RQ2 diagnostics using frozen annotations and saved OOF outputs.

This script does not train, refit, re-encode, or overwrite the RQ2 evaluator
outputs. Run it from the repository root after rq2_eval.py has completed.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sentence_transformers import SentenceTransformer
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)


SEED = 42
N_BOOT = 2000
EMBEDDER = "all-MiniLM-L6-v2"
INPUT_DIR = Path("data/interim")
RESULTS_DIR = Path("results")
AUDIT_PATH = RESULTS_DIR / "rq2_embedding_truncation_audit_corrected.csv"
SUMMARY_PATH = RESULTS_DIR / "rq2_diagnostic_summary.csv"


def load_saved_inputs():
    hum = pd.read_csv(INPUT_DIR / "sufficiency_labels.csv")
    subset = pd.read_csv(RESULTS_DIR / "rq2_evaluation_subset.csv")
    oof = pd.read_csv(RESULTS_DIR / "rq2_oof.csv")
    required_hum = {"url", "sufficient", "evidence_span"}
    required_subset = {"url", "project", "correct", "confidence", "p_sufficient"}
    required_oof = {"url", "annotated", "fold", "pred", "confidence", "p_sufficient"}
    for name, frame, required in [
        ("human", hum, required_hum),
        ("evaluation subset", subset, required_subset),
        ("OOF", oof, required_oof),
    ]:
        if not required.issubset(frame.columns):
            raise ValueError(f"{name} missing columns: {required - set(frame.columns)}")
        if frame["url"].isna().any() or frame["url"].duplicated().any():
            raise ValueError(f"{name} has missing or duplicate URLs")

    if len(hum) != 201:
        raise ValueError(f"Expected 201 human annotations, found {len(hum)}")
    if len(subset) != len(hum):
        raise ValueError("Saved evaluation subset and human labels have different sizes")
    if len(oof) != 369 or not oof["url"].is_unique:
        raise ValueError("Saved OOF output is not the expected 369-row unique file")
    if not subset["url"].isin(oof["url"]).all():
        raise ValueError("Evaluation subset contains URLs absent from saved OOF output")
    if not subset["url"].isin(hum["url"]).all():
        raise ValueError("Evaluation subset contains URLs absent from human labels")

    annotated_oof = oof[oof["annotated"]].copy()
    if len(annotated_oof) != 201 or set(annotated_oof["url"]) != set(subset["url"]):
        raise ValueError("Saved OOF annotated rows do not match the evaluation subset")
    return hum, subset, oof


def exact_matches(text, span):
    text_folded = text.casefold()
    span_folded = span.casefold()
    starts = []
    start = text_folded.find(span_folded)
    while start >= 0:
        starts.append(start)
        start = text_folded.find(span_folded, start + 1)
    return starts


def normalized_contains(text, span):
    def compact(value):
        return " ".join(str(value).casefold().split())
    return compact(span) in compact(text)


def span_status(text, span, visible_end):
    span = "" if pd.isna(span) else str(span).strip()
    if not span:
        return "empty", 0, "empty"

    matches = exact_matches(text, span)
    if len(matches) != 1:
        if len(matches) > 1:
            return "uncertain", len(matches), "multiple_exact_matches"
        if normalized_contains(text, span):
            return "uncertain", 0, "normalized_only_match"
        return "not_found", 0, "not_found"

    start = matches[0]
    end = start + len(span)
    if start >= visible_end:
        return "outside_encoder_window", 1, "exact_unique"
    if end > visible_end:
        return "partially_truncated", 1, "exact_unique"
    return "inside_encoder_window", 1, "exact_unique"


def audit_truncation(hum, gold):
    required = {"url", "title", "description_clean"}
    if not required.issubset(gold.columns):
        raise ValueError(f"Gold missing columns: {required - set(gold.columns)}")
    if not gold["url"].is_unique:
        raise ValueError("Gold contains duplicate URLs")

    encoder = SentenceTransformer(EMBEDDER)
    tokenizer = encoder.tokenizer
    limit = int(encoder.max_seq_length)
    tokenizer_limit = int(getattr(tokenizer, "model_max_length", -1))
    if limit <= 0:
        raise ValueError("Encoder max_seq_length is invalid")

    reports = gold[["url", "project", "title", "description_clean"]].copy()
    reports["input_text"] = (
        reports["title"].fillna("") + ". " +
        reports["description_clean"].fillna("")
    )
    data = reports.merge(
        hum[["url", "sufficient", "evidence_span"]],
        on="url", how="left", validate="one_to_one",
    )
    if data["sufficient"].notna().sum() != 201:
        raise AssertionError("Truncation audit does not contain exactly 201 annotated URLs")

    rows = []
    for row in data.itertuples(index=False):
        full = tokenizer(row.input_text, add_special_tokens=True, truncation=False)
        encoded = tokenizer(
            row.input_text,
            add_special_tokens=True,
            max_length=limit,
            truncation=True,
            return_offsets_mapping=True,
        )
        offsets = encoded["offset_mapping"]
        visible_end = max(
            (end for start, end in offsets if end > start), default=0
        )
        annotated = pd.notna(row.sufficient)
        if annotated:
            status, matches, match_mode = span_status(
                row.input_text, row.evidence_span, visible_end
            )
            sufficient = int(row.sufficient)
            nonempty = bool(str(row.evidence_span).strip())
        else:
            status, matches, match_mode = "not_annotated", 0, "not_annotated"
            sufficient, nonempty = np.nan, False
        rows.append({
            "url": row.url,
            "project": row.project,
            "sufficient": sufficient,
            "truncated_report": bool(len(full["input_ids"]) > limit),
            "evidence_span_nonempty": nonempty,
            "span_status": status,
            "span_match_count": matches,
            "span_match_mode": match_mode,
            "wordpiece_count_with_special_tokens": len(full["input_ids"]),
            "encoder_limit": limit,
            "tokenizer_model_max_length": tokenizer_limit,
            "visible_character_end_approx": visible_end,
            "annotated": annotated,
        })

    audit = pd.DataFrame(rows)
    annotated_audit = audit[audit["annotated"]].copy()
    statuses = {
        "empty", "not_found", "uncertain", "inside_encoder_window",
        "partially_truncated", "outside_encoder_window",
    }
    if len(annotated_audit) != 201 or not annotated_audit["url"].is_unique:
        raise AssertionError("Annotated truncation audit must contain 201 unique URLs")
    if not set(annotated_audit["span_status"]).issubset(statuses):
        raise AssertionError("Unknown span status in truncation audit")
    if len(annotated_audit["span_status"]) != annotated_audit["span_status"].notna().sum():
        raise AssertionError("Truncation audit contains unaccounted annotated rows")
    if ((annotated_audit["span_status"] == "empty") &
            annotated_audit["evidence_span_nonempty"]).any():
        raise AssertionError("Empty span was marked nonempty")
    if ((annotated_audit["span_status"] == "inside_encoder_window") &
            ~annotated_audit["evidence_span_nonempty"]).any():
        raise AssertionError("Empty span counted as inside the encoder window")

    audit.to_csv(AUDIT_PATH, index=False)
    print("\n=== Corrected MiniLM truncation/evidence audit ===")
    print(f"Encoder max_seq_length={limit}; tokenizer model_max_length={tokenizer_limit}")
    print(f"Gold reports truncated: {int(audit['truncated_report'].sum())}/{len(audit)}")
    print(f"Annotated reports truncated: {int(annotated_audit['truncated_report'].sum())}/201")
    print("Annotated span status by human sufficiency:")
    print(annotated_audit.groupby(["sufficient", "span_status"]).size().to_string())
    sufficient_nonempty = annotated_audit[
        (annotated_audit["sufficient"] == 1) &
        annotated_audit["evidence_span_nonempty"]
    ]
    truncated_support = sufficient_nonempty[
        sufficient_nonempty["span_status"].isin(
            ["partially_truncated", "outside_encoder_window"]
        )
    ]
    print(f"Sufficient reports with nonempty spans: {len(sufficient_nonempty)}")
    print(f"Sufficient reports with partially/wholly truncated spans: {len(truncated_support)}")
    print(f"Saved: {AUDIT_PATH}")
    return audit


def bootstrap_error_difference(data, n_boot=N_BOOT, seed=SEED):
    projects = pd.unique(data["project"])
    by_project = {project: np.flatnonzero(data["project"].to_numpy() == project)
                  for project in projects}
    rng = np.random.default_rng(seed)
    replicates = []
    invalid = 0
    for _ in range(n_boot):
        sampled = rng.choice(projects, size=len(projects), replace=True)
        indices = np.concatenate([by_project[project] for project in sampled])
        boot = data.iloc[indices]
        if set(boot["sufficient"]) != {0, 1}:
            invalid += 1
            continue
        rates = boot.groupby("sufficient")["error"].mean()
        replicates.append(float(rates.loc[0] - rates.loc[1]))
    if not replicates:
        raise ValueError("No usable project-bootstrap replicates contained both classes")
    lo, hi = np.percentile(replicates, [2.5, 97.5])
    return float(lo), float(hi), len(replicates), invalid, len(projects)


def diagnostic_summary(hum, subset):
    data = subset[["url", "project", "correct", "confidence", "p_sufficient"]].merge(
        hum[["url", "sufficient"]], on="url", how="left", validate="one_to_one",
        indicator=True,
    )
    if len(data) != len(subset) or not data["_merge"].eq("both").all():
        raise AssertionError("Saved OOF predictions and labels are not aligned 1:1")
    data = data.drop(columns="_merge")
    if len(data) != 201 or data["url"].duplicated().any():
        raise AssertionError("Diagnostic join must contain 201 unique reports")
    data["error"] = 1 - data["correct"].astype(int)
    if not np.isfinite(data[["confidence", "p_sufficient"]].to_numpy()).all():
        raise ValueError("Saved diagnostic scores contain nonfinite values")

    group = data.groupby("sufficient", sort=True).agg(
        reports=("url", "size"),
        errors=("error", "sum"),
        accuracy=("correct", "mean"),
    ).reset_index()
    group["error_rate"] = 1 - group["accuracy"]
    rates = group.set_index("sufficient")["error_rate"]
    observed_difference = float(rates.loc[0] - rates.loc[1])
    lo, hi, usable, invalid, projects = bootstrap_error_difference(data)

    label = data["sufficient"].to_numpy(dtype=int)
    probability = data["p_sufficient"].to_numpy(dtype=float)
    correct = data["correct"].to_numpy(dtype=int)
    hard = (probability >= 0.5).astype(int)
    report = classification_report(
        label, hard, labels=[0, 1],
        target_names=["insufficient", "sufficient"],
        output_dict=True, zero_division=0,
    )
    ap = average_precision_score(1 - label, 1 - probability)
    roc = roc_auc_score(label, probability)
    always_f1 = 2 * label.sum() / (len(label) + label.sum())
    correctness_conf = roc_auc_score(correct, data["confidence"])
    correctness_suff = roc_auc_score(correct, probability)
    rho = spearmanr(data["confidence"], probability).statistic

    print("\n=== Saved-OOF sufficiency/error diagnostic ===")
    print(group.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print(f"Observed error-rate difference (insufficient - sufficient): {observed_difference:.3f}")
    print(f"Project bootstrap 95% CI: [{lo:.3f}, {hi:.3f}]; "
          f"usable={usable}; invalid={invalid}; projects={projects}")
    print("Insufficient-class confusion matrix (rows=human, cols=model):")
    print(confusion_matrix(label, hard, labels=[0, 1]))
    print(f"Insufficient precision={report['insufficient']['precision']:.3f}; "
          f"recall={report['insufficient']['recall']:.3f}; "
          f"F1={report['insufficient']['f1-score']:.3f}; AP={ap:.3f}")
    print(f"Always-sufficient F1={always_f1:.3f}; prevalence={(label == 0).mean():.3f}")
    print(f"Sufficiency ROC-AUC={roc:.3f}; correctness ROC-AUC confidence={correctness_conf:.3f}; "
          f"sufficiency={correctness_suff:.3f}; Spearman={rho:.3f}")

    rows = []
    for row in group.itertuples(index=False):
        rows.append({"metric": f"group_{row.sufficient}_reports", "value": row.reports})
        rows.append({"metric": f"group_{row.sufficient}_errors", "value": row.errors})
        rows.append({"metric": f"group_{row.sufficient}_accuracy", "value": row.accuracy})
        rows.append({"metric": f"group_{row.sufficient}_error_rate", "value": row.error_rate})
    rows.extend([
        {"metric": "error_rate_difference_insufficient_minus_sufficient", "value": observed_difference},
        {"metric": "error_rate_bootstrap_ci_low", "value": lo},
        {"metric": "error_rate_bootstrap_ci_high", "value": hi},
        {"metric": "bootstrap_attempts", "value": N_BOOT},
        {"metric": "bootstrap_usable_replicates", "value": usable},
        {"metric": "bootstrap_invalid_replicates", "value": invalid},
        {"metric": "distinct_projects", "value": projects},
        {"metric": "insufficient_precision", "value": report["insufficient"]["precision"]},
        {"metric": "insufficient_recall", "value": report["insufficient"]["recall"]},
        {"metric": "insufficient_f1", "value": report["insufficient"]["f1-score"]},
        {"metric": "insufficient_average_precision", "value": ap},
        {"metric": "always_sufficient_f1", "value": always_f1},
        {"metric": "sufficiency_roc_auc", "value": roc},
        {"metric": "correctness_roc_auc_confidence", "value": correctness_conf},
        {"metric": "correctness_roc_auc_sufficiency", "value": correctness_suff},
        {"metric": "spearman_confidence_p_sufficient", "value": rho},
    ])
    pd.DataFrame(rows).to_csv(SUMMARY_PATH, index=False)
    print(f"Saved: {SUMMARY_PATH}")


def main():
    hum, subset, oof = load_saved_inputs()
    gold = pd.read_csv("data/processed/gold_v1.csv")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    audit_truncation(hum, gold)
    diagnostic_summary(hum, subset)


if __name__ == "__main__":
    main()
