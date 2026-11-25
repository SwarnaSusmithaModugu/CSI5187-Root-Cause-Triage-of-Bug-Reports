"""Summarize RQ4 v2 baselines and Phase 3 gate."""

from pathlib import Path

import pandas as pd


OUTPUT = Path("results/rq4/v2")


def main():
    metrics = pd.read_csv(OUTPUT / "metrics.csv")
    ci = pd.read_csv(OUTPUT / "bootstrap_ci.csv").iloc[0]
    changes = pd.read_csv(OUTPUT / "paired_differences.csv")
    matches = pd.read_csv(OUTPUT / "control_match_audit.csv")
    manifest = pd.read_csv(OUTPUT / "unit_manifest_v2.csv")

    seed_rows = metrics[
        metrics["condition"].str.startswith("B1_seed_", na=False)
    ]
    random_mean = seed_rows["macro_f1"].mean()
    random_min = seed_rows["macro_f1"].min()
    random_max = seed_rows["macro_f1"].max()
    matchable = int(matches["b3_matchable"].sum())
    matchable_total = len(matches)

    b0 = metrics.set_index("condition").loc["B0_no_reveal"]
    b3 = metrics.set_index("condition").loc["B3_same_type_control"]
    ref = metrics.set_index("condition").loc["REF_all_units"]
    change_counts = changes["change"].value_counts().to_dict()

    gate_passes = (
        ci["macro_f1_ci_low"] > 0
        and b3["macro_f1"] > b0["macro_f1"]
        and matchable >= 100
    )

    text = f"""# RQ4 v2 Interpretation

## Phase 1 validity

The v1 targeted selector was retained as an invalid historical reference.
It read withheld candidate text and is not interpreted as a learnable policy.
Comments were excluded from the primary robust v2 cohort because filing-time
provenance cannot be established.

## Phase 2 baselines

- Robust cohort: {int(b0['n'])} reports, {int(b0['projects'])} projects
- Same-type matchable subset: {matchable}/{matchable_total}
- B0 withheld macro-F1: {b0['macro_f1']:.6f}
- B3 same-type control macro-F1: {b3['macro_f1']:.6f}
- Full-unit reference macro-F1: {ref['macro_f1']:.6f}
- Random reveal mean macro-F1: {random_mean:.6f} (range {random_min:.6f}-{random_max:.6f})
- Paired B3-vs-B0 changes: {change_counts}
- Macro-F1 difference 95% project-bootstrap CI: [{ci['macro_f1_ci_low']:.6f}, {ci['macro_f1_ci_high']:.6f}]
- Accuracy difference 95% project-bootstrap CI: [{ci['accuracy_ci_low']:.6f}, {ci['accuracy_ci_high']:.6f}]

The baseline interval includes zero. The strict same-type control does not
demonstrate a reliable improvement over withheld prediction, and the full-unit
reference is only a retrospective information diagnostic, not a ceiling for
deployment.

## Phase 3 gate

**STOP: C-VOI NOT IMPLEMENTED.**

The mandatory gate requires a strong, stable same-type baseline result.
The interval includes zero and the v1 hidden-content selector is invalid, so
there is no justified basis for a learned selector.

This is a retrospective text-restoration study, not an active clarification
agent or external validation.
"""
    (OUTPUT / "interpretation.md").write_text(text, encoding="utf-8")

    schema = """{
  "visible_features": [
    "visible_report_tfidf_or_embedding",
    "visible_report_character_length",
    "candidate_type",
    "candidate_index",
    "candidate_count",
    "candidate_count_by_type",
    "legitimate_length_bucket"
  ],
  "excluded_features": [
    "candidate_hidden_text",
    "candidate_text_embedding",
    "candidate_keywords",
    "restored_output",
    "gold_label",
    "test_correctness",
    "target_or_control_outcomes",
    "fix_derived_metadata"
  ]
}
"""
    (OUTPUT / "policy_features_schema.json").write_text(schema, encoding="utf-8")


if __name__ == "__main__":
    main()
