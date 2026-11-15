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

## 2. Gold join and comment recovery

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

## 3. RQ1 final

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

## 4. RQ3 classical and hybrid

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

## 5. Silver: final design, per-LF validation, focused build

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

## 6. Commit tangling sub-finding

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

## 7. Threats to validity

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
