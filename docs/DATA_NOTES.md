# Dataset and experiment notes

## 1. Dataset provenance and freeze

The extracted release contains 54,755 issues from 103 projects. Of these,
19,641 have `commitsDetails`; the stricter source benchmark cites 10,459
issues. The 369-report gold set contains 122 concurrency, 121 memory, and 126
semantic reports across 61 projects and 369 unique URLs.

The source training tables overlap completely with the gold labels and are
not independent silver data. The dataset was selected using keyword search
and manual examination, so keyword presence is a selection artifact rather
than an independent test target.

The frozen gold file is `data/processed/gold_v1.csv`:

```text
rows=369  columns=43
sha256_16=5ae3365e515e22ce
comments with a fix-revealing phrase masked: 143
empty descriptions kept: 21
bot authors kept: 5
exact/near/cross-label duplicates: 0/0/0
```

Raw `comments_clean` remains available for inspection; models use
`comments_model`. The frozen-file test passed.

## 2. RQ2 sufficiency and selective abstention

The supplied evaluator was added as `src/rq2_eval.py`. It uses frozen
`all-MiniLM-L6-v2` embeddings, project-grouped five-fold OOF evaluation, and
the paired project-cluster bootstrap described in the evaluator. The required
runtime dependency `sentence-transformers` was added to `requirements.txt`
and installed in the repository `.venv`.

The evaluator was syntax-checked successfully and run from the repository
root with:

```text
.venv\Scripts\python.exe src\rq2_eval.py
```

The completed human file passed structural validation: 201 unique URLs with
the required columns `url`, `sufficient`, `inferred_category`,
`evidence_span`, and `missing_info`. It contains 157 sufficient and 44
insufficient reports (sufficient rate 0.781). The sample is stratified by gold
root-cause class and spans 47 projects; it is not naturally representative.

The v3 protocol setup produced the following annotation templates:

```text
data/interim/sufficiency_sheet.csv
data/interim/pilot_overlap_template.csv
```

The generated sheets contain no root-cause labels. The completed master is
Human A; `pilot_A.csv` is the independent Human B overlap, `pilot_B.csv` is
GPT-6, and `pilot_C.csv` is Claude Haiku 5.5. All four sources aligned on the
same 50 URLs. These LLM comparisons are supplementary model agreement, not
inter-human reliability, and LLM labels remain separate from the human master.

Pilot agreement on 50 aligned reports:

```text
comparison                         agreement  Cohen kappa
Human A vs Human B                    0.960       0.864
Human A vs GPT-6                      0.860       0.636
Human A vs Claude Haiku 5.5            0.960       0.875
GPT-6 vs Claude Haiku 5.5              0.900       0.749
```

Human A and Human B matched on 48/50 sufficiency judgments. The LLM results
do not establish model accuracy or replace independent human labels. The
comparison outputs are `results/rq2_annotation_comparison/agreement_summary.csv`,
`confusion_matrices.csv`, and `disagreements.csv`; 11 reports had at least one
pairwise disagreement.

The completed RQ2 evaluation ran with five project-grouped folds, random state
42, title plus cleaned description, and the frozen `all-MiniLM-L6-v2` encoder:

```text
Gold reports: 369
Annotated/evaluated: 201
Evaluation projects: 47
Human sufficient-rate: 0.781
Root-cause macro-F1, all gold OOF: 0.761
Root-cause macro-F1, annotated subset: 0.756
Construct cross-check: 137/157 = 0.873 category matches among sufficient reports
Sufficient reports by gold class: memory=58, semantic=53, concurrency=46
Sufficiency classifier F1 at p>=0.5: 0.861
Sufficiency classifier ROC-AUC: 0.794
```

Selective prediction used the same 201 annotated held-out reports and the same
root-cause predictions:

```text
policy       AURC    error@90%  error@80%  error@70%
confidence   0.0897    0.215      0.199      0.156
sufficiency  0.1831    0.221      0.193      0.199
combined     0.0978    0.227      0.199      0.142
```

Observed paired project-bootstrap differences, baseline minus combined:

```text
baseline      metric  observed delta       95% bootstrap CI
confidence    AURC       -0.0081          [-0.0255, +0.0106]
confidence    err@80%   +0.0000          [-0.0357, +0.0292]
sufficiency   AURC       +0.0853          [+0.0444, +0.1187]
sufficiency   err@80%   -0.0062          [-0.0255, +0.0323]
```

The pilot does not support a claim that the combined ranking improves on
classifier confidence: its AURC is slightly worse and the interval includes
zero. It improves observed AURC over sufficiency-only, while the error@80%
comparison is inconclusive. The product remains a parameter-free ranking
heuristic, not a calibrated probability or novel algorithm. Sufficiency F1 and
ROC-AUC above were computed from the saved held-out `p_sufficient` scores; the
evaluator itself reports selective-ranking metrics and does not fit a calibrated
probability model.

The archived text is treated as title-and-description-only, not a verified
filing-time snapshot. These are grouped OOF results rather than an untouched
independent test set. Human sufficiency labels remain a judgment construct,
and the category cross-check is not proof that evidence spans establish the
diagnosis. Results were written to `results/rq2_oof.csv` and
`results/rq2_evaluation_subset.csv`.

## 3. Gold join and comment recovery

All 369 gold URLs joined to project issue JSON. Twenty-five fix dates
preceded issue creation dates and were retained as an audit note.

Comment recovery completed without request errors:

```text
issues requested: 369
fetch ok: 369
issues with any comment: 286
comments total: 1939
human comments before fix: 254/369 (69%)
```

Coverage was 254/369 using authored dates, 262/369 using commit dates, and
252/369 using closed dates. The authored-date coverage led to the static RQ4
decision. A leakage scan found 106 reports with at least one flagged pre-fix
comment; 143 comment values were masked in the frozen model field.

## 4. RQ1 final

Project-grouped five-fold results using title, cleaned description, and
leak-masked comments:

```text
setting                    mode    macro_f1
full                       -       0.689
loo_title                  hard    0.618
loi_title                  hard    0.619
loo_description_clean      hard    0.669
loi_description_clean      hard    0.533
loo_comments_model         hard    0.655
loi_comments_model         hard    0.441
loo_title                  length  0.629
loi_title                  length  0.639
loo_description_clean      length  0.682
loi_description_clean      length  0.544
loo_comments_model         length  0.641
loi_comments_model         length  0.457
full_keyword_masked        mask    0.667
```

The normal-to-masked drop was 0.022. The keyword shortcut baseline is 0.773,
so the content result is below the artifact baseline. The masked result is
above the preliminary title/description result of 0.655. Comment-only
results are lower bounds because comments cover 69% of reports.

After fixing the InfoGain stopword bug, the top terms were:

```text
url, user, issue, fix, problem, using, thanks, version, code, use, like, case
```

These are report-vocabulary terms, not the C/M selection keywords.

## 5. RQ3 classical and hybrid

The detailed RQ3 report is [`docs/RQ3_RESULTS.md`](RQ3_RESULTS.md). The four
saved OOF tables are organized under `results/rq3/tables/`; their schemas and
369-row contents are unchanged. SetFit and zero-shot LLM comparisons are not
present in this repository and remain pending.

Grouped five-fold classical results:

```text
setting  method    macro-F1  concurrency  memory  semantic
normal   majority  0.240     0.000        0.296   0.423
normal   svm       0.689     0.656        0.723   0.689
normal   knn       0.555     0.593        0.643   0.429
normal   tree      0.595     0.543        0.682   0.561
masked   majority  0.240     0.000        0.296   0.423
masked   svm       0.667     0.622        0.667   0.712
masked   knn       0.545     0.574        0.613   0.447
masked   tree      0.587     0.511        0.564   0.686
```

Normal-to-masked drops were SVM 0.022, KNN 0.010, and tree 0.008.

The nested grouped-CV hybrid added word and character features, structural
features, and explicit keyword/exception features in normal mode:

```text
normal hybrid: macro-F1=0.770
  per-class: concurrency=0.774, memory=0.790, semantic=0.746
masked hybrid: macro-F1=0.700
  per-class: concurrency=0.655, memory=0.712, semantic=0.734
hybrid-normal vs plain-SVM McNemar exact p=0.0005
```

The masked hybrid remains above majority (0.240) and below the keyword
artifact baseline (0.773).

## 6. Silver: final design, per-LF validation, focused build

Silver is restricted to concurrency and memory; semantic remains gold-only.
The pool is the 19,641 benchmark-complete issue records. Only fix-side LFs
meeting 0.70 accuracy on gold are trusted.

Final context-anchored validation:

```text
lf                    coverage  accuracy_where_fires  fires
lf_commit_keywords    0.339     0.920                  125
lf_changed_paths      0.035     0.538                   13
lf_changed_methods    0.111     0.610                   41
lf_exception_type     0.125     0.543                   46
lf_report_keywords    0.455     0.702                  168
trusted fix LFs: lf_commit_keywords
```

The source-file/non-bug filter produced 486 rows before focus filtering:
244 concurrency and 242 memory. The focused build adds merge detection,
at most two referenced issues, at most 20 changed files, and the real-source
requirement. It removed 6,451 of 19,270 wild reports and produced:

```text
focused silver: 454 rows
concurrency: 212
memory: 242
near-duplicates removed against gold: 0
```

Both `silver_unfiltered.csv` and `silver_focused.csv` are preserved for the
before/after validation. The 40-row sheets
`review_unfiltered.csv` and `review_focused.csv` contain blank `my_label`
fields. Author labeling is pending; no precision result has been fabricated.

## 7. Commit tangling sub-finding

Tangling is defined here as a merge commit, more than two referenced issue
numbers, or more than 20 changed files. The contrast is prominent:

```text
wild benchmark-complete pool: 17.3% tangled
gold:                         1.6% tangled
```

The gold check matched exactly 369 records using `(normalized URL, project)`
from `gold_joined.csv`. Two duplicate URLs were found; both duplicate commit
payloads were identical and the first deterministic record was retained.

Top wild project tangling rates were:

```text
mozilla/MozStumbler                  0.900
Netflix/Hystrix                      0.714
eclipse/kura                         0.662
apache/incubator-dolphinscheduler    0.624
apache/druid                         0.553
junit-team/junit4                    0.540
antlr/antlr4                         0.500
eclipse/deeplearning4j               0.493
oracle/graal                         0.480
hazelcast/hazelcast                  0.479
```

The before/after precision comparison is pending author labels in the two
40-row sheets. It must be reported as single-annotator author validation,
not two-coder agreement.

## 8. Threats to validity

- Gold labels and the 0.773 keyword baseline reflect keyword-selected
  sampling, so gold precision may overstate wild-pool precision.
- Grouped-by-project cross-validation is retained; random CV was not used.
- Comments cover only 69% of reports under the authored-date cutoff.
- The silver labels are weak supervision from commit evidence, not
  independent ground truth.
- Tangled commits can mix concerns and transfer a misleading keyword across
  several issues; the focus filter is a practical mitigation, not a novel
  tangling detector.
- The structure-only probe reached 0.39 macro-F1 versus 0.29 random, but its
  signal was dominated by fix size and confounded with class-dependent
  sampling, so it was not adopted.
- LLM validation and author labels for the silver review sheets remain
  pending; no LLM agreement or precision statistic is reported.

## 9. RQ2 diagnostic closure

The saved-OOF diagnostics were run without refitting or overwriting the
existing predictions:

```text
.venv\Scripts\python.exe src\rq2_diagnostics.py
```

The corrected audit instantiated the local `all-MiniLM-L6-v2` model and found
`max_seq_length=256` and tokenizer `model_max_length=256`. It reproduced the
title-plus-cleaned-description construction and found 53/369 truncated gold
reports and 30/201 truncated annotated reports. For annotated reports, the
status counts by human sufficiency were:

```text
sufficient=0: inside=42, outside=2
sufficient=1: inside=151, uncertain=3, partially_truncated=1, outside=2
```

All 157 sufficient reports had nonempty spans. Three sufficient reports had
supporting spans partially or wholly beyond the encoder window, and three
additional spans were conservatively marked uncertain because exact location
was ambiguous. Empty spans are tracked separately and are never counted as
inside. The corrected per-report audit is
`results/rq2_embedding_truncation_audit_corrected.csv`; the previous audit is
preserved unchanged.

The saved-OOF error association was:

```text
class          reports  errors  accuracy  error_rate
insufficient       44      16     0.636       0.364
sufficient        157      33     0.790       0.210
observed difference, insufficient - sufficient: 0.153
project bootstrap 95% CI: [-0.022, 0.382]
bootstrap attempts/usable/invalid: 2000/2000/0
distinct projects: 47
```

The insufficiency confusion matrix remained `[[21, 23], [21, 136]]`; the
insufficient class had precision 0.500, recall 0.477, F1 0.488, and AP 0.558.
The always-sufficient F1 baseline was 0.877. The diagnostic summary is saved
at `results/rq2_diagnostic_summary.csv`.

The evidence audit shows that nearly all classifiable sufficient spans were
inside the encoder window, so no chunked-embedding sensitivity check was
implemented. Truncation remains a bounded threat to validity. The narrow RQ2
finding is that human-insufficient reports had a higher observed error rate,
while predicted sufficiency ranked correctness worse than confidence and the
confidence-times-sufficiency policy did not improve the primary AURC result.
This is an association, not a causal claim. Full results are in
`docs/RQ2_RESULTS.md`.
