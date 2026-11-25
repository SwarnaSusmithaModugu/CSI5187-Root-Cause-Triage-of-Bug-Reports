# RQ4: frozen qualified retrospective result

## START HERE

- **Final interpretation:** [FINAL_RQ4_DECISION.md](FINAL_RQ4_DECISION.md)
- **Primary four-row table:** [table_primary.csv](../../results/rq4/final/table_primary.csv)
- **Reproduce derived report:** [rq4_finalize_report.py](../../scripts/rq4_finalize_report.py)
- **Provenance and source audit:** [provenance.json](../../results/rq4/final/provenance.json) · [RQ4_V2_SOURCE_AUDIT.md](RQ4_V2_SOURCE_AUDIT.md)

**Status: FROZEN — QUALIFIED RETROSPECTIVE RESULT.** The observed B3-minus-B0
macro-F1 difference is positive, but the paired project-cluster 95% interval
includes zero. RQ4 does not establish a beneficial policy or deployable
clarification agent.

## Reproduce the final report

From the repository root in PowerShell:

```powershell
.venv\Scripts\python.exe scripts\rq4_finalize_report.py
```

This report-only command verifies registered input hashes and derives tables
from saved v2 predictions. It does not fit models or rerun selectors. It writes
only under `results/rq4/final/`.

| Final artifact | Use |
|---|---|
| `table_primary.csv` | Four common-cohort rows: B0, B3 with 43 documented fallbacks, B1 ten-seed summary, and retrospective REF. |
| `table_matchable_subset.csv` | Two 252-report descriptive rows; different cohort and not comparable to 295-report absolute scores. |
| `table_supplementary.csv` | Ten B1 seed rows plus B2 and B4. |
| `table_classwise.csv` | Full 295-report cohort per-class precision, recall, and F1. |
| `table_invalid_debug.csv` | B5 archive/debug status only; B5 is identical to B2 on all 295 saved predictions and is excluded from valid policy comparisons. |
| `cohort_and_controls.csv` | Cohort, match-length, source overlap, comment exclusion, and metadata-visibility details. |
| `paired_outcomes.csv`, `bootstrap_ci.csv` | Saved paired report outcomes and preserved project-cluster bootstrap interval. |
| `validation.json`, `provenance.json` | Acceptance checks, input hashes, cohort provenance, and no-training confirmation. |

## Historical / detailed audit

These are retained for audit and reproducibility, not as the active result
summary:

- [RQ4_ARTIFACT_REGISTER.md](RQ4_ARTIFACT_REGISTER.md): original 28-entry
  immutable input inventory and producing commands. The canonical copy remains
  at `docs/rq4/` because the finalizer reads that fixed path.
- [RQ4_V2_SOURCE_AUDIT.md](RQ4_V2_SOURCE_AUDIT.md): source-level evidence and
  limitations.
- [RQ4_LEGACY_INVENTORY.md](RQ4_LEGACY_INVENTORY.md): keep/deprecate/review
  recommendations; no files are deleted by this cleanup.
- `results/rq4/`: historical v1 feasibility, predictions, and metrics. The
  v1 targeted selector inspected held-out candidate text; its targeted score
  is invalid for acquisition-policy claims.
- `results/rq4/v2/`: preserved predictions, metrics, folds, unit/match audits,
  paired differences, and bootstrap output. `interpretation.md` is an earlier
  supporting note and is superseded by the final decision where wording
  differs.
- `src/rq4_reveal.py` and `src/rq4_feasibility.py`: preserved v1
  implementation/reproducer; do not rerun as part of report reproduction.
- `src/rq4_v2/`: preserved v2 audit, baseline, evaluation, and interpretation
  code. The baseline generator rewrites files under `results/rq4/v2/` and is
  not part of final-report reproduction.

Do not delete, move, or regenerate registered v1/v2 sources or outputs. B2 and
B4 remain supplementary; B5 and the historical v1 targeted output remain
archive/debug-only. B3 matched 252 description units and fell back to B0 for
43; its matching-length differences were not uniform. Archived description
text is not verified to be a filing-time snapshot, and code/stack excerpts can
overlap description text.
