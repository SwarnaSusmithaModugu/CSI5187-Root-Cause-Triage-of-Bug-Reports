# Dataset notes

## Setup inventory

The code clone has no corpus; the release was extracted from the downloaded
dataset archive into `data/raw/`.

## Dataset inventory

The extracted dataset is available under `data/raw/`.

- Total size: 533,423,127 bytes (0.497 GiB)
- Files: 2,906
- Project folders containing `issuesDataWStats.json`: 103
- Gold label folders: `data/raw/mlClassifier/data/bugreports/{concurrency,memory,semantic}`
- Label files: 122 concurrency, 121 memory, 126 semantic
- Dataset documentation: `data/raw/mlClassifier/data/dataset_composition.txt`
- Project data: `data/raw/githubanalysis/data`
- Keyword data: `data/raw/keywordSearch/data`
- Configuration: `data/raw/config.json`
- Example issue: `data/raw/exampleIssue.json`

## Gold label table

`data/interim/labels.csv` was generated using the required filename pattern.
The verification output is:

```text
concurrency    122
memory         121
semantic       126
total rows     369
distinct URLs  369
distinct projects 61
```

Top five projects by report count:

```text
netty/netty                          73
elastic/elasticsearch                32
redisson/redisson                    26
spring-projects/spring-boot         23
AsyncHttpClient/async-http-client   14
```

The sample label files contain the issue title followed by the issue body.
The observed samples include diagnostic stack traces, code, and URLs; no fix
content was inferred or added.

## Trainingset files

The three trainingset files are larger feature/data tables, not the 369-row
gold table:

```text
trainingset_concurrency.csv: 5528 data rows
trainingset_memory.csv:      3370 data rows
trainingset_semantic.csv:    2640 data rows
```

Their headers include `created`, `user`, `body`, `closed`, `commitsDetails`,
`url`, `labels`, and `title`, along with commit and repository statistics.

The provenance overlap check found:

```text
gold urls: 369
trainingset_concurrency.csv: rows=122 urls=122 overlap_with_gold=122
    gold concurrency inside this file: 122
    gold memory inside this file: 0
    gold semantic inside this file: 0
trainingset_memory.csv: rows=121 urls=121 overlap_with_gold=121
    gold concurrency inside this file: 0
    gold memory inside this file: 121
    gold semantic inside this file: 0
trainingset_semantic.csv: rows=128 urls=126 overlap_with_gold=126
    gold concurrency inside this file: 0
    gold memory inside this file: 0
    gold semantic inside this file: 126
gold projects: 61  shared with trainingset: 61
```

Therefore, these files are not an independent silver training set. They
contain all 369 gold reports and must not be used for training or evaluation
without an explicit overlap-removal decision.

## Dataset provenance

The source README states:

> The full data set consists of 54755 "bug" labeled issues reports collected
> from 103 open source projects hosted on GitHub.

It also states:

> From these, 10459 issues are used based on filter criteria described in
> "Root cause prediction based on bug reports" (commits available, changes in
> production java code, only dealing with a single issue, less than 10
> commits, max. 20 files changed per commit, max. 250 LOC changed per file).

The README states:

> A training set was created from above described benchmark, using keyword
> search on commit message combined with random selection followed by manual
> examination of those bugs.

Class-specific sampling is stated in the dataset composition file as:

```text
keyword search memory: (119, 5)
random selected memory: (2, 5)
keyword search concurrency: (118, 5)
random selected concurrency: (4, 5)
keyword search semantic: (173, 5)
keyword search semantic with confidence above 7: (150, 5)
keyword search semantic sample size: (7, 5)
random selected semantic: (126, 5)
random selected semantic with confidence above 7: (119, 5)
full semantic training set: (126, 5)
```

The three final class counts are 122 concurrency, 121 memory, and 126
semantic. The documents identify manual examination/classification as the
labeling process, but do not state a separate label source beyond that:
**label source: not stated**.

## Gold join

The join to the project issue JSON completed successfully:

```text
labels: 369  matched to issue json: 369  unmatched: 0
fix_date from commit: 369  from closed: 0  fix authored before issue created: 25
projects: 61  largest: netty/netty=73 (20%)
wrote data\interim\gold_joined.csv rows=369
```

All 369 reports matched. Twenty-five reports have a commit authored date
earlier than the issue creation date; this is recorded for the comment-cut
audit rather than silently corrected.
