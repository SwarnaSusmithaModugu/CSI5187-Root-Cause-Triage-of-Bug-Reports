# RQ4 v2 Audit

## Implementation audit

| Check | Status | Evidence |
|---|---|---|
| Hidden-content selector | FAIL | `src/rq4_reveal.py` calls `decision_function` on test candidate unit text and contains the hidden unit text in v1 target selection. |
| V1 unit label use | FAIL | `src/rq4_reveal.py` fits a training text classifier using report root-cause labels and candidate unit text. It is not a predeclared utility policy and unit labels do not establish value. |
| Same-report model | PASS | B0/B1/B2/B3/B4/B5 use one withheld-fitted model per outer test report in v1 construction, except selector-specific invalid v1 actions. |
| Comments time boundary | UNKNOWN | `src/build_processed.py:35-54` applies fix/closed comment cutoffs, but filing-time timestamps are unavailable. Comments are excluded from the primary robust v2 cohort. |
| Code/stack provenance | MIXED | `src/clean.py:25-63` extracts code and stack text from the archived description. `src/build_processed.py:86-100` renames extracted fields. These units can duplicate description content. |
| Unit offsets | PARTIAL | Unit audit stores offsets for exact description extracts; code/stack offsets are source-linked to description where found. |
| Project boundaries | PASS | Reuse one 5-fold `StratifiedGroupKFold(seed=42)` mapping for the robust v2 cohort. |
| V1 archive | PASS | v1 CSV files were not overwritten. New artifacts are under `results/rq4/v2/`. |

## Remediation

The v1 targeted selector is invalid as a learnable acquisition policy because it
reads withheld candidate text. It is retained only as a historical reference
and is not used as a valid v2 method. Phase 3 C-VOI is blocked until the
Phase 2 baselines pass leakage and matching gates.

## Cohorts

- Robust no-comments eligible reports: 295
- Robust projects: 58
- Fold mapping SHA-256: 8fe391d5f558acae3112f64ff957e479353aa79c531cd46cb7d8c68433961c1a
