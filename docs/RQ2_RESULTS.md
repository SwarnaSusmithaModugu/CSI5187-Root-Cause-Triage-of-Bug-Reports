# RQ2 Results

## Scope and inputs

RQ2 evaluates report-text sufficiency and selective root-cause prediction using
title plus cleaned description only. The archived text is not verified to be a
filing-time snapshot, so the result is described as title-and-description-only.
Comments, fixes, and fixing commits are excluded.

The frozen gold file contains 369 reports from 61 projects. Human sufficiency
annotations cover 201 reports from 47 projects: 157 sufficient and 44
insufficient. The annotation sample was stratified by root-cause category and
is not naturally representative. Human labels remain the reference; GPT-6 and
Claude Haiku 5.5 annotations are supplementary model comparisons, not training
ground truth.

The root-cause and sufficiency models use project-grouped five-fold
`StratifiedGroupKFold`, seed 42, frozen `all-MiniLM-L6-v2` embeddings, and
logistic regression with balanced class weights. Root-cause training uses all
labeled reports in training projects; sufficiency training uses annotated
reports in training projects. The saved OOF outputs are the evaluation basis.

## Verified results

Root-cause macro-F1 was 0.761 on all 369 OOF reports and 0.756 on the same
201-report annotated subset. The sufficiency classifier had F1 0.861 for the
sufficient class, ROC-AUC 0.794, insufficient-class recall 0.477, and
insufficient-class average precision 0.558 against an insufficient prevalence
of 0.219. The always-sufficient F1 baseline was 0.877.

Human-judged sufficiency was associated with observed root-cause errors:

| Human class | Reports | Errors | Accuracy | Error rate |
| --- | ---: | ---: | ---: | ---: |
| Insufficient | 44 | 16 | 0.636 | 0.364 |
| Sufficient | 157 | 33 | 0.790 | 0.210 |

The observed error-rate difference, insufficient minus sufficient, was 0.153.
A paired project-cluster bootstrap with 2,000 attempts produced a 95% interval
of [-0.022, 0.382], with 2,000 usable replicates, 0 invalid replicates, and
47 distinct projects. This is an association, not a causal effect or proof
that sufficiency improves abstention.

Correctness-ranking ROC-AUC was 0.791 for classifier confidence and 0.614 for
predicted sufficiency. Their Spearman correlation was 0.290.

Selective prediction used the same annotated OOF reports and root-cause
predictions:

| Ranking | AURC | Error at 90% | Error at 80% | Error at 70% |
| --- | ---: | ---: | ---: | ---: |
| Confidence | 0.0897 | 0.215 | 0.199 | 0.156 |
| Sufficiency | 0.1831 | 0.221 | 0.193 | 0.199 |
| Confidence x sufficiency | 0.0978 | 0.227 | 0.199 | 0.142 |

The product heuristic did not improve AURC over confidence. The observed
confidence-minus-combined AURC difference was -0.0081, with bootstrap CI
[-0.0255, 0.0106]. The product is a ranking heuristic, not a calibrated
probability or a novel algorithm. No score combination or threshold was tuned
on these pooled OOF results.

## Evidence-span and truncation audit

The instantiated encoder reports `max_seq_length=256`; the tokenizer reports
`model_max_length=256`. The audit used the same title plus description string
construction as inference and tokenized without re-encoding model outputs.

Across the 369 gold reports, 53 were truncated. Among the 201 annotated
reports, 30 were truncated. Corrected annotated span statuses were:

| Human sufficiency | Empty | Not found | Uncertain | Inside | Partially truncated | Outside |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 42 | 0 | 2 |
| 1 | 0 | 0 | 3 | 151 | 1 | 2 |

All 157 sufficient reports had nonempty supporting spans. Three sufficient
reports had supporting spans partially or wholly beyond the encoder window.
Three additional sufficient spans were marked uncertain because exact location
was ambiguous; the audit does not infer token coverage for these cases. Empty
spans are a separate status and are never counted as inside.

Because nearly all classifiable sufficient spans were inside the encoder
window, no chunked-embedding robustness check was implemented. Truncation is
retained as a bounded threat to validity. A future sensitivity analysis would
need a separately fixed aggregation rule, the same project folds and source
text, and no gold-label leakage.

## Reproducibility artifacts

The evaluator and diagnostics are run from the repository root with:

```powershell
.venv\Scripts\python.exe src\rq2_eval.py
.venv\Scripts\python.exe src\rq2_diagnostics.py
.venv\Scripts\python.exe src\rq2_reliability.py
```

The evaluator preserves:

- `results/rq2_oof.csv`
- `results/rq2_evaluation_subset.csv`

The additive diagnostics produce:

- `results/rq2_embedding_truncation_audit_corrected.csv`
- `results/rq2_diagnostic_summary.csv`
- `results/rq2_correctness_by_human_sufficiency.csv`
- `results/rq2_diagnostic_subset.csv`

The prior audit remains preserved as
`results/rq2_embedding_truncation_audit.csv`. Human annotations and the
independent overlap files remain separate from LLM annotations.

## Limitations

These are grouped out-of-fold results, not an untouched independent test set.
The annotation sample is stratified, the sufficiency construct is subjective,
and the category cross-check does not prove that an evidence span establishes
a diagnosis. The bootstrap is conditional on fixed OOF predictions and does
not include retraining or annotation uncertainty. Human-insufficient reports
had a higher observed error rate, but predicted sufficiency ranked correctness
worse than confidence, and the combined ranking did not improve the primary
AURC comparison.
