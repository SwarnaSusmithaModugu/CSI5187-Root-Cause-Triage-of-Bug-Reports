# RQ4 Legacy File Inventory and Deprecation Proposals

## Scope

This is a documentation-only inventory of RQ4 source, historical outputs,
supporting notes, and current derived reporting. It proposes deprecation and
navigation changes only. No file is deleted, moved, or rewritten by this
inventory. Hash-registered files remain byte-for-byte archival.

The registered RQ4 sources and outputs were untracked at revision
`dcf9a752116317161d90992046e8134d25c7877f`; the register identifies their
preserved bytes. The cleanup does not switch branches or move those files.

## Inventory

| File(s) | Status | Evidence and proposal |
|---|---|---|
| `docs/final/FINAL_RQ4_DECISION.md` | **KEEP — authoritative** | Contains the qualified final interpretation, confidence interval spanning zero, B3 match/fallback counts, and approved reproduction command. Use it as the sole current interpretation. |
| `results/rq4/final/table_primary.csv` | **KEEP — current primary table** | Derived from saved v2 predictions by `scripts/rq4_finalize_report.py`; contains only the four 295-report conditions after this cleanup. Link from root `README.md` and `docs/final/RQ4_README.md`. |
| `results/rq4/final/table_matchable_subset.csv` | **KEEP — supplementary descriptive table** | Contains B0/B3 on the 252 B3-matchable reports and explicitly warns the cohort differs from the 295-report primary cohort. |
| `results/rq4/final/table_supplementary.csv` | **KEEP — supplementary** | Contains ten B1 seed rows and the B2/B4 sensitivity baselines. |
| Other `results/rq4/final/*` report outputs | **KEEP — current derived evidence** | Classwise metrics, invalid/debug B5 record, cohort/controls, paired outcomes, preserved bootstrap, validation, and provenance are produced by the report-only finalizer. |
| `scripts/rq4_finalize_report.py`, `tests/test_rq4_finalize_report.py` | **KEEP — current reporting pipeline** | The finalizer reads saved predictions and validates the artifact register; its focused test asserts output roles/cohorts, source identities, bootstrap preservation, and archive safety. |
| `docs/rq4/RQ4_ARTIFACT_REGISTER.md`, `docs/final/RQ4_V2_SOURCE_AUDIT.md` | **KEEP — immutable audit record** | Register records 28 hashed inputs and source scripts; source audit supports only a qualified retrospective result. The canonical register stays at its finalizer-required path. |
| `docs/final/RQ4_README.md`, `docs/final/RQ4_POST_FREEZE_CHANGELOG.md`, `docs/final/RQ4_LEGACY_INVENTORY.md` | **KEEP — navigation / change record** | Current entry point, pre/post-freeze provenance, and non-destructive archive recommendations. |
| `docs/archive/RQ4_FEASIBILITY.md` | **KEEP — historical feasibility note; deprecate as a result entry point** | Its 311-report/59-project and v1 condition table describe the original feasibility run, which included candidate comments. It links to the current decision and primary table. |
| `results/rq4/feasibility.csv` | **KEEP — historical v1 feasibility archive** | Hash-registered as the original 369-report feasibility inventory; its 311/59 eligibility counts are not the v2 primary cohort. |
| `results/rq4/rq4_reveal_predictions.csv`, `results/rq4/rq4_results.csv` | **KEEP — historical v1 archive; deprecate policy interpretation** | Hash-registered v1 outputs. `src/rq4_reveal.py` inspected held-out candidate text in the targeted selector, so those targeted values are not valid acquisition-policy evidence. |
| `src/rq4_reveal.py` | **KEEP — historical reproducer and shared helper dependency** | V1 targeted selection is invalid, but `src/rq4_v2/baselines.py` imports shared unit/removal helpers from it. Do not delete or rerun it as part of final-report reproduction. |
| `src/rq4_feasibility.py` | **KEEP — historical reproducer and shared helper dependency** | V2 audit code imports its description-unit helper, and `tests/test_rq4_feasibility.py` exercises its logic. |
| `src/rq4_v2/__init__.py`, `audit.py`, `baselines.py`, `evaluate.py` | **KEEP — source for registered v2 evidence** | Their commands and output hashes are recorded in the artifact register. `baselines.py` writes into the preserved v2 archive; none is needed to reproduce the report-only tables. |
| `src/rq4_v2/interpret.py` | **KEEP — historical artifact reproducer; deprecate as current interpretation** | Produces the registered earlier interpretation and policy schema. The schema declaration is not proof of selector behavior; the source audit and final decision supersede interpretation wording where it conflicts. |
| `results/rq4/v2/reveal_predictions.csv`, `metrics.csv`, `fold_map.csv`, `control_match_audit.csv`, `paired_differences.csv`, `bootstrap_ci.csv`, `unit_audit.csv`, `unit_manifest_v2.csv`, `run_manifest.json`, `subgroup_metrics.csv` | **KEEP — immutable v2 evidence** | Hash-registered inputs to the finalizer and source audit. The saved bootstrap is preserved, not re-searched or retuned. |
| `results/rq4/v2/audit.md`, `experiment_protocol.md`, `interpretation.md`, `policy_features_schema.json` | **KEEP — historical supporting artifacts; deprecate as current conclusions** | Hash-registered. The current README points to the source audit and final decision instead. Leave these bytes unchanged; the old interpretation is not the final policy conclusion. |
| `tests/test_rq4_feasibility.py`, `tests/test_rq4_v2.py`, `tests/test_rq4_v2_baselines.py` | **KEEP — source and archive checks** | Exercise unit extraction, v2 audit/baseline construction, and saved predictions. Retain to protect archived source behavior. |
| `docs/final/DATA_NOTES.md`, root `README.md` | **KEEP — project-facing navigation and scope** | DATA_NOTES distinguishes RQ4's 311/59 historical screen from 295/58 v2 and lists each other RQ's actual input boundary. Root README links to active documentation and the current primary table without changing RQ wording. |

## Deprecation recommendations

1. Treat the v1 targeted score and old v2 `interpretation.md` as archive-only;
   never use them as current policy comparisons.
2. Keep the v1 feasibility report visible only as a historical feasibility
   record. Route readers seeking the conclusion through the current RQ4 README.
3. Keep all v2 source/results and registered supporting notes for
   reproducibility, but describe `audit.md`, `experiment_protocol.md`, and
   `interpretation.md` as historical supporting artifacts, not entry points.
4. Do not label any listed files **DUPLICATE**: no exact duplicate was proven
   unused, unregistered, and separately backed up. Any future deletion requires
   a separate review and explicit authorization.

No deletion or storage migration is authorized by this inventory.
