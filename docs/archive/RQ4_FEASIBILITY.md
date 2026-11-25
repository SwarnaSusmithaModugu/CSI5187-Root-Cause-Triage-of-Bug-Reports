# RQ4 Controlled Information-Reveal Feasibility

> **Historical feasibility record, not the current RQ4 result.** The 311-report,
> 59-project count below is the original v1 feasibility screen, which included
> candidate comments. The final robust v2 evaluation uses 295 reports across
> 58 projects after excluding comments with unverified filing-time provenance.
> See the [final decision](../final/FINAL_RQ4_DECISION.md) and
> [four-row primary table](../../results/rq4/final/table_primary.csv) for the
> authoritative result.

## Unit and eligibility definition

Candidate units were coherent paragraphs of the original report description
(30-2000 characters), plus eligible `code_text`, `stack_text`, and
`comments_model` fields. Units must be traceable to existing report text.
Fix commits, gold labels, fixing commits, and fix-derived metadata were not
used to select units. The label field was retained only for audit and
evaluation.

The predeclared go criteria were at least 100 eligible reports, 40 projects,
and at least 20 eligible reports in each of concurrency, memory, and semantic.

## Feasibility result

The manifest is `results/rq4/feasibility.csv`. It contains 369 rows and
records eligibility, unit IDs, provenance, and leakage flags.

- Eligible reports: 311
- Eligible projects: 59
- Eligible concurrency: 103
- Eligible memory: 103
- Eligible semantic: 105
- Decision: GO

## Historical v1 result (not a valid targeted-policy comparison)

The archived v1 run used 311 eligible reports and 59 projects. The values below
are retained for historical reproducibility only. Source audit found that its
target selector scored held-out candidate text, so its targeted row is invalid
as evidence for an implementable acquisition policy.

| Historical v1 condition | Reports | Projects | Macro-F1 | Accuracy |
| --- | ---: | ---: | ---: | ---: |
| Withheld | 311 | 59 | 0.611640 | 0.610932 |
| Control | 311 | 59 | 0.618481 | 0.620579 |
| Targeted (invalid selection) | 311 | 59 | 0.626543 | 0.627010 |

Artifacts are `results/rq4/rq4_reveal_predictions.csv` and
`results/rq4/rq4_results.csv`. The v1 targeted value is excluded from valid
policy comparisons. The v1 condition outputs remain archived and are not
reproduced by the v2 B5 reference condition.

## v2 validity audit and baseline stop gate

The v1 implementation used withheld candidate text to select targets, so v1
targeted selection is not retained as a valid acquisition policy. v1 outputs
remain archived unchanged under `results/rq4/`.

The v2 primary cohort excludes `comments_model` because filing-time provenance
is not established. It contains 295 reports across 58 projects after
description/code/stack eligibility recomputation; it is not a newly sampled or
independent dataset. The current four-row primary table reports B0, qualified
B3, the ten-seed B1 summary, and retrospective REF. The same-type control had
macro-F1 `0.607874`, versus `0.598062` withheld. The paired project-cluster
bootstrap 95% interval for the macro-F1 difference was `[-0.036973, 0.049015]`,
and the accuracy interval was `[-0.032111, 0.053628]`; neither establishes a
reliable advantage.

The 10-seed random reveal macro-F1 mean was approximately `0.609321`, spanning
`0.591361` to `0.630819`. Full-unit restoration reached `0.627530` as a
retrospective reference only. The v2 suite stopped at stronger baselines:
C-VOI was not implemented because the v1 selector has a hidden-content defect
and the strict same-type control did not clear the predeclared stop gate.

Complete v2 audit artifacts are under `results/rq4/v2/`.
