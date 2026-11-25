# Final RQ4 Decision

## Decision

| Component | Decision | Basis |
|---|---|---|
| B0 withheld | **KEEP — primary anchor** | 0.598062 macro-F1, 0.596610 accuracy on 295 reports / 58 projects |
| B3 same-type / nearest-available-length | **KEEP — QUALIFY** | 0.607874 macro-F1, 0.610169 accuracy; 252 description matches and 43 B0 fallbacks; paired project-cluster CI includes zero |
| B1 random single-unit reveal | **KEEP — summarized** | 10-seed mean macro-F1 0.609321; range 0.591361–0.630819 |
| REF full restoration | **KEEP — retrospective context only** | 0.627530 macro-F1, 0.627119 accuracy; not a deployable policy or guaranteed ceiling |
| B2 shortest-unit / B4 training-fold type preference | **KEEP — supplementary only** | Macro-F1 0.589120 / 0.588960 |
| B5 v1-target reference | **EXCLUDE from valid policy comparisons** | V2 constructs B5 from the same shortest-unit ID as B2; predictions match 295/295 |
| Historical v1 targeted selector | **EXCLUDE from policy claims** | Source scores held-out candidate text |
| C-VOI / LLM selector | **DO NOT IMPLEMENT** | Existing stop gate was not met |

## Reproduced evaluation

The report-only generator independently checked the saved predictions and
metrics. It verified 4,720 rows across 16 conditions, 295 URLs per condition,
58 projects, five project-separated folds, valid three-class labels, and one
consistent fold model per report across conditions. Every saved macro-F1 and
accuracy matched recomputation within absolute tolerance `1e-6`.

The B3-minus-B0 macro-F1 difference is `+0.009812`; the preserved 5,000
resample paired project-cluster bootstrap 95% percentile interval is
`[-0.036973, +0.049015]`. The accuracy-difference interval is
`[-0.032111, +0.053628]`. The intervals include zero. B3 paired correctness
changes were 25 beneficial, 21 harmful, and 249 unchanged.

B3's 252 successful matches are all description units; the other 43 reports
use the unchanged B0 prediction. The absolute matched character-length
difference had median 30.5, Q1 10.0, Q3 80.75, and maximum 1,912. This is not
a uniformly length-matched control. The 252-report common-cohort comparison is
provided descriptively and is not directly compared with full-cohort scores.

The v2 primary conditions exclude `comments_model`. They use archived
description text that is not verified to be a filing-time snapshot. Candidate
unit type/count/index/length are metadata derived from the complete archived
report, so this is retrospective synthetic text restoration rather than a
demonstrated interactive acquisition workflow. Code and stack excerpts are
derived from the description and can overlap; overlap flags do not prove
independent evidence.

## Exact final-paper findings paragraph

> RQ4 evaluates retrospective restoration of existing report information on 295 reports from 58 projects, excluding comments with uncertain filing-time provenance. The qualified B3 same-type / nearest-available-length description control matched 252 reports and fell back to B0 for 43; on the full cohort, it attained macro-F1 0.608 compared with 0.598 for B0. The paired project-clustered 95% confidence interval for the difference [−0.037, 0.049] includes zero. Random single-unit reveals also varied across seeds, while full restoration reached 0.628 as a descriptive reference. We therefore found no statistically established benefit from the tested single-unit restoration controls. The earlier targeted policy was excluded because it inspected withheld content.

## Acceptance results

- **PASS:** report regeneration recomputed all saved prediction metrics,
  cohort/fold checks, paired outcomes, and full-cohort per-class metrics.
- **PASS:** all 28 registered input hashes matched; historical v1/v2 inputs
  remain unchanged.
- **PASS:** `python -m pytest -q tests` — 17 passed; focused RQ4 tests — 6
  passed; `git diff --check` — clean.
- **QUALIFY:** unscoped `python -m pytest -q` cannot collect one legacy file
  under `data/raw/`; it imports a missing pretrained artifact-detection
  model. This is unrelated to RQ4, and the repository `tests/` suite passes.

## Reproduction and freeze

From the repository root:

```powershell
.venv\Scripts\python.exe scripts\rq4_finalize_report.py
```

The command checks all SHA-256 values in
`docs/rq4/RQ4_ARTIFACT_REGISTER.md`, reads saved v2 predictions, and writes
only derived files under `results/rq4/final/`. It does not fit a model or rerun
a selector. Acceptance details are in `results/rq4/final/validation.json`.

**QUALIFY — RQ4 FROZEN — QUALIFIED RETROSPECTIVE RESULT**
