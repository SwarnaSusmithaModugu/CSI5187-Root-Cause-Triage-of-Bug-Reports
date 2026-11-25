# RQ3 Results

## Scope

RQ3 compares project-grouped classical and hybrid root-cause classifiers on the
369-report frozen gold set. The saved experiments use five shuffled
`StratifiedGroupKFold` folds with seed 42. The normal setting uses title, cleaned
description, and leak-masked comments. The masked setting additionally masks
the selection-keyword shortcuts.

The repository contains completed TF-IDF baselines and a nested grouped-CV
hybrid. No SetFit or zero-shot LLM result files or source scripts were found,
so those planned comparisons remain pending and are not described as completed.

## Completed results

| Setting | Method | Macro-F1 | Concurrency | Memory | Semantic |
| --- | --- | ---: | ---: | ---: | ---: |
| Normal | Majority | 0.240 | 0.000 | 0.296 | 0.423 |
| Normal | Linear SVM | 0.689 | 0.656 | 0.723 | 0.689 |
| Normal | KNN | 0.555 | 0.593 | 0.643 | 0.429 |
| Normal | Decision tree | 0.595 | 0.543 | 0.682 | 0.561 |
| Masked | Majority | 0.240 | 0.000 | 0.296 | 0.423 |
| Masked | Linear SVM | 0.667 | 0.622 | 0.667 | 0.712 |
| Masked | KNN | 0.545 | 0.574 | 0.613 | 0.447 |
| Masked | Decision tree | 0.587 | 0.511 | 0.564 | 0.686 |
| Normal | Hybrid | 0.770 | 0.774 | 0.790 | 0.746 |
| Masked | Hybrid | 0.700 | 0.655 | 0.712 | 0.734 |

Normal-to-masked macro-F1 drops were 0.022 for SVM, 0.010 for KNN, and 0.008
for the tree. The hybrid decreased from 0.770 to 0.700 when masked. The normal
hybrid versus plain normal SVM comparison had exact McNemar p=0.0005.

The keyword shortcut baseline is 0.773. It is an artifact baseline, not a
model target or independent test result. The normal hybrid is below that
shortcut baseline, and the masked hybrid remains above the majority baseline
but below the shortcut baseline.

## Reproduction and artifacts

From the repository root:

```powershell
.venv\Scripts\python.exe src\rq3_classical.py
.venv\Scripts\python.exe src\rq3_hybrid.py
```

Both scripts use the frozen `data/processed/gold_v1.csv`, seed 42, and write
these canonical tables:

- `results/rq3/tables/rq3_oof_normal.csv`
- `results/rq3/tables/rq3_oof_masked.csv`
- `results/rq3/tables/rq3_oof_hybrid_normal.csv`
- `results/rq3/tables/rq3_oof_hybrid_masked.csv`

Each table contains 369 OOF rows and its original prediction schema. The
scripts were path-checked without rerunning the expensive model experiments.
No RQ3 figures are currently present; figure directories should be created
only when a reproducible figure source is added.

## Structural-feature correction audit

The public hybrid runner reads nonexistent `description_has_stack` and
`description_has_code` columns and silently backfilled zero values. The frozen
gold instead contains `has_stack` and `has_code`, both derived from
description text by `src/clean.py` and both nonconstant:
135/369 reports have `has_stack=True` and 194/369 have `has_code=True`.
The corrected implementation is
`src/rq3_hybrid_structural_corrected.py`; it is run as a module:

```powershell
.venv\Scripts\python.exe -m src.rq3_hybrid_structural_corrected
```

It preserves the legacy five-fold, seed-42, nested-CV configuration and adds
URL, project, fold, and experiment IDs to separate corrected outputs. The
archived legacy files and scores remain unchanged.

| Setting | Legacy macro-F1 | Corrected macro-F1 | Change | Changed predictions |
| --- | ---: | ---: | ---: | ---: |
| Normal | 0.769849 | 0.767437 | -0.002412 | 8 |
| Masked | 0.700329 | 0.703271 | +0.002942 | 28 |

The normal correction did not improve held-out performance. The masked
correction slightly improved macro-F1, but the paired accuracy bootstrap
interval includes zero in both settings and exact McNemar p-values were 1.0.
The masked and normal feature policies remain different: masked evaluation
removes explicit keyword/exception numeric features, so the masked difference
cannot be attributed to text masking alone.

## Limitations and pending work

These are project-grouped OOF estimates, not an untouched independent test.
The normal setting includes comments after leakage masking, while the masked
setting removes the selected keyword shortcuts; comparisons must retain those
information boundaries. The keyword-selected gold sample and shortcut baseline
limit generalization.

SetFit: blocked/not started. The local environment is Python 3.13.7 with
PyTorch 2.15.0 CPU-only and no `setfit` package installed. No SetFit
predictions or scores were fabricated.

Zero-shot LLM: not started. No publicly available instruction-tuned checkpoint
was downloaded or executed, and no prompt, model revision, parse-failure
statistics, or LLM predictions are claimed.
