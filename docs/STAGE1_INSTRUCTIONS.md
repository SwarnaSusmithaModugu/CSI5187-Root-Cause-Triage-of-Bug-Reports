# CSI5187 Stage 0 and 1: Setup, Dataset Check, Comment Recovery, Cleaning

Instructions for GitHub Copilot (Agent mode) in VS Code. Each step has a prompt to paste, a done-when check, and a stop rule. Run the steps in order. Review every diff before accepting it.

**How to use this file.** Save it in the repo as `docs/STAGE1_INSTRUCTIONS.md`. Open Copilot Chat in Agent mode, attach this file, and paste one step prompt at a time.

**What was learned from the `fault_type_prediction` repo listing (use these facts, do not re-guess):**
- Per-project data lives in folders named `Owner_repo`, each holding `issuesDataWStats.json`. About 103 projects. The same folder also has small (~400 byte) stub files such as `HikariCP.json`. Those are not data, skip them.
- Gold labels are encoded by **folder**: files under `bugreports/concurrency/`, `bugreports/memory/`, `bugreports/semantic/`. Each file has no extension and is named `Owner_repo_issues_N` (for example `Azure_azure-iot-sdk-java_issues_167`). Expected counts: 122, 121, 126.
- Other files to read before trusting anything: `README.md`, `dataset_composition.txt`, `exampleIssue.json`, `config.json`, `dataset_filter_stats.csv`, `keywordSearch/data/*.csv`, `randomly_selected_bugs.csv`, `keyword_memory_concurrency_bugs.csv`, and the three `trainingset_*.csv` files.
- The per-project JSON has **no comments field**. Each issue has `url`, `title`, `body`, `created`, `closed`, `commitsDetails` (with `authoredDateTime` and `commitDateTime`). Comments must be fetched from GitHub.
- Unverified until Copilot reports back: what the `bugreports` files contain, the columns of the `trainingset_*.csv` files, how the semantic class was sampled, and whether all 369 resolve to a project JSON.

---

## Ground rules (also goes into `.github/copilot-instructions.md`, Step 0.3)

1. Never edit anything under `data/raw/`. Raw data is read-only.
2. Never fabricate a number, a label, a comment, or a file. If something is missing, stop and report it.
3. Do not install packages beyond `requirements.txt`. If one is needed, stop and ask.
4. Never print, log, or commit the GitHub token. It lives only in `.env`.
5. Never drop rows silently. Flag them in a column and report counts. The team decides what to remove.
6. Print real outputs (counts, headers, sample rows) and paste them into `docs/DATA_NOTES.md`. Do not summarize from memory.
7. If an expected number differs (369, 122/121/126), stop and report the difference before continuing.

---

## Step 0.1: Create the project

**Prompt:**
> Create a sub project folder `.github/`, `data/raw/`, `data/interim/`, `data/processed/`, `data/comments/`, `src/`, `notebooks/`, `results/`, `tests/`, `docs/`.
> Create a Python 3.10+ virtual environment in `.venv`. Create `requirements.txt` with exactly: pandas, numpy, scipy, scikit-learn, statsmodels, requests, matplotlib, pytest, python-dotenv. Install from it. Create `.gitignore` covering `.venv/`, `__pycache__/`, `.env`, `data/raw/`, `data/comments/raw/`, `.ipynb_checkpoints/`. Create a short `README.md` with the project title "Evidence-Grounded, Calibrated, Selective Root-Cause Triage of Bug Reports", the three team members, and a "How to reproduce" section left as a stub.

**Done when:** `python -c "import pandas, sklearn, requests"` works inside `.venv` and `git status` is clean after the first commit.

## Step 0.2: Copy in the existing code

**Prompt:**
> Copy `load_projects.py`, `rq1_ablation.py`, and `fetch_comments.py` into `src/`. Do not modify them yet. Add an empty `src/__init__.py`. Run `python -m py_compile src/*.py` and report any errors.

**Done when:** all three compile.

## Step 0.3: Guardrail file for Copilot

**Prompt:**
> Create `.github/copilot-instructions.md` containing the seven ground rules from the "Ground rules" section of `docs/STAGE1_INSTRUCTIONS.md`, plus this line: "Gold labels are the 369 hand-labeled reports. They are the only data we train and test on."

**Done when:** the file exists and Copilot Chat references it.

**Your own action (not Copilot):** create a GitHub personal access token (fine-grained, public repositories read-only, no extra scopes) and put `GITHUB_TOKEN=...` in `.env`. Do not paste the token into any chat.

---

## Step 1.1: Get the dataset

**Prompt:**
> Run `git clone --depth 1 https://github.com/AmadeusBugProject/fault_type_prediction data/raw/fault_type_prediction`. Then report: total size on disk, the number of folders that contain an `issuesDataWStats.json`, and the exact paths of these items found with `find`: the folder named `bugreports`, the three `trainingset_*.csv` files, `dataset_composition.txt`, `README.md`, `exampleIssue.json`, `config.json`, and the `keywordSearch/data` folder. Write those paths into `src/config.py` as constants. Do not assume any path.

**Done when:** every path is found and recorded. If the clone is too slow, stop and tell the team to download the Zenodo release (DOI 10.5281/zenodo.3973048) manually into `data/raw/`.

## Step 1.2: Read the documentation before touching data

**Prompt:**
> Read `README.md`, `dataset_composition.txt`, and `config.json` in full, and the first 40 lines of `exampleIssue.json`. Write a plain summary in `docs/DATA_NOTES.md` under "Dataset provenance" that answers only from those files: (a) how the 54,755 and 10,459 figures arise, (b) how the 369 labeled reports were chosen, (c) specifically how each of the three classes was sampled (keyword search versus random selection), (d) what the label source was. Quote the exact sentences you rely on. If a question is not answered in the files, write "not stated" for it.

**Done when:** `DATA_NOTES.md` has the four answers with quotes. **Why this matters:** if concurrency and memory came from keyword search and semantic came from random selection, the classes differ by how they were found, not only by root cause. That is a shortcut a classifier can exploit and the professor already flagged selection bias.

## Step 1.3: Build the gold label table

**Prompt:**
> Walk the three subfolders of `bugreports` (`concurrency`, `memory`, `semantic`). Each file is named `Owner_repo_issues_N` with no extension. Parse with the regex `^(?P<owner>[^_]+)_(?P<repo>.+)_issues_(?P<num>\d+)$` (GitHub owners cannot contain underscores, so the first underscore splits owner from repo). Build a table with columns `source_file`, `owner`, `repo`, `issue_number`, `root_cause` (the folder name), `url` (= `https://github.com/{owner}/{repo}/issues/{issue_number}`). Save it to `data/interim/labels.csv`. Print the counts per class, the number of distinct projects, and the top 5 projects by report count. Assert there are exactly 369 rows and that no file failed to parse. Then print the contents of three sample files, one per class.

**Done when:** 369 rows, counts 122/121/126, zero parse failures. If the counts differ, stop and report.
**Expected values (checked against the repo listing):** 369 distinct urls, 61 distinct projects (not 103, the 103 is the full corpus), largest project `netty/netty` with 73 reports (about 20%), then `elastic/elasticsearch` 32, `redisson/redisson` 26, `spring-projects/spring-boot` 23, `AsyncHttpClient/async-http-client` 14. If Copilot reports different numbers, stop and report.
**Report back:** what the sample files contain (title only, title plus body, something else). If they contain anything about the fix, flag it as leakage.

## Step 1.4: Inspect the trainingset files

**Prompt:**
> Without modifying them, print for each `trainingset_*.csv` the shape, column names, dtypes, and the first 2 rows (truncate long text to 200 characters). Report whether the rows correspond to the 369 gold reports or to a larger set, and whether any column holds the issue url or id. Add a "Trainingset files" section to `docs/DATA_NOTES.md`. Do not use these files as model input yet.

**Done when:** the section lists the columns and says what the files are. They may be feature matrices built by the original authors, which we do not need.

## Step 1.5: Join labels to the project data

**Prompt:**
> Using `src/load_projects.py`, load only the project folders that appear in `data/interim/labels.csv` (read each `issuesDataWStats.json`, ignore the small stub `.json` files). Join to the labels with `join_gold`, which normalizes urls. Print matched versus unmatched counts. For every unmatched label, print the url and the most likely reason by checking: the project folder is missing, the folder exists but the issue number is absent, or the repo was renamed (look for a folder with the same repo name but a different owner). Do not guess a match. Save the matched table to `data/interim/gold_joined.csv`. Run `gold_report` and paste its full output into `docs/DATA_NOTES.md`.

**Done when:** matched is 369 and unmatched is 0, or every unmatched report has a documented reason. Report the share held by the largest project and whether any fold is missing a class.

## Step 1.6: Confirm fix dates

**Prompt:**
> For the joined gold table, report how many of the 369 have a non-null `fix_date` (earliest `authoredDateTime` across linked commits). For each null, fall back to `closed` and mark `fix_date_source` as `closed`, else `commit`. Also compute, for each report, whether `fix_date` is earlier than `created` (a commit authored before the issue was filed) and report that count. Add the numbers to `docs/DATA_NOTES.md`.

**Done when:** the table has `fix_date_source`. **Why:** the comment cut depends on this date. A commit authored before the issue was filed would leave zero usable comments.

---

## Step 2.1: Fetch the comment threads

**Prompt:**
> Create `data/interim/gold_urls.csv` from `gold_joined.csv` with columns `url`, `fix_date`, `closed`. Then run `python src/fetch_comments.py --gold data/interim/gold_urls.csv --out data/comments`. The script reads `GITHUB_TOKEN` from the environment, so load `.env` first (use python-dotenv at the top of a small wrapper, do not print the token). The run is resumable, if it stops, rerun the same command. When it finishes, print the contents of `data/comments/coverage.txt` and `fetch_status.csv` value counts.

**Done when:** `coverage.txt` exists. **Stop rule:** if more than 5 percent of requests return an error other than 404/410, stop and report the status codes. Do not retry in a loop.

## Step 2.2: Audit the comments

**Prompt:**
> Using `data/comments/comments_all.csv`, produce these tables and paste them into `docs/DATA_NOTES.md` under "Comment recovery":
> 1. Coverage per class: how many reports in each of concurrency, memory, semantic have at least one human comment before the fix. If coverage differs a lot by class, flag it, because then the comments field would be informative for the wrong reason.
> 2. The 15 most frequent comment authors with their bot flag, so the team can extend `BOT_LOGINS` in `fetch_comments.py` for automated accounts. Do not change the list yourself.
> 3. Coverage under three cut rules: earliest linked commit authored time (current), earliest commit time (`commitDateTime`), and `closed`. Show the number of reports with at least one pre-cut human comment for each rule.
> 4. Median and 90th percentile of pre-fix comment count and character length.

**Done when:** all four tables are in the notes. **Decision rule for the team (not Copilot):** about 70 percent or more of the 369 with a usable pre-fix human comment, and no large class imbalance in coverage, means live RQ4. Otherwise RQ4 runs in its static form.

## Step 2.3: Scan comments for label leakage

**Prompt:**
> On the pre-fix human comments only, count per class how many contain fix-revealing language, using case-insensitive regexes for: `fix(ed|es)?\s+(in|by|with)`, `(closes|fixes|resolves)\s+#?\d+`, `pull request|\bPR\b`, `commit\s+[0-9a-f]{7,40}`, `\b[0-9a-f]{7,40}\b` (bare SHAs), `merged`, `patch`. Print counts per class and 5 example snippets per pattern (80 characters around the match). Do not delete anything. Save a boolean column `comment_leak_flag` and add the counts to `docs/DATA_NOTES.md`.

**Done when:** counts and examples are in the notes. The team decides after reading them whether to mask flagged spans or exclude flagged comments.

---

## Step 3.1: Clean the text (keep raw, add new columns)

**Prompt:**
> Create `src/clean.py` with a function that takes the gold table and adds columns, never overwriting `title`, `description`, or `comments`:
> - `description_clean`: remove HTML comments (`<!-- ... -->`), normalize unicode (NFKC), strip markdown image syntax, replace urls with `<URL>`, commit SHAs with `<SHA>`, `@mentions` with `<USER>`, and issue references like `#123` with `<REF>`, then collapse whitespace.
> - `code_text`: fenced code blocks and indented code, extracted out of the description.
> - `stack_text`: Java stack frames (`at pkg.Class.method(File.java:12)`) and lines containing `Exception` or `Error`, extracted out.
> - `has_stack`, `has_code`: booleans.
> - `desc_len_chars`, `desc_len_tokens` on `description_clean`.
> Apply the same function to the pre-fix comments to make `comments_clean`. Write unit tests in `tests/test_clean.py` covering at least a url, a SHA, a mention, an HTML comment, a code fence, and a stack frame.

**Done when:** `pytest` passes and the raw columns are unchanged (add a test that checks this).

## Step 3.2: Data quality flags (flag, never delete)

**Prompt:**
> In `src/quality.py` add boolean flag columns to the gold table and print a count table:
> - `flag_empty`: description_clean shorter than 20 characters.
> - `flag_template_only`: description_clean is mostly issue-template headings with no free text.
> - `flag_non_english`: more than 30 percent of alphabetic characters are outside basic Latin (a simple heuristic, do not install a language library).
> - `flag_is_pr`: url contains `/pull/`.
> - `flag_bot_author`: the `user` field looks like a bot.
> - `flag_exact_dup`: another gold report has an identical normalized title plus description.
> - `flag_near_dup`: TF-IDF cosine similarity above 0.9 with another gold report, and list the pairs.
> - `flag_cross_label_dup`: a duplicate or near-duplicate pair with different `root_cause`. Print every such pair in full.
> Add the counts and the cross-label pairs to `docs/DATA_NOTES.md`.

**Done when:** the table and pair listing are in the notes. A cross-label pair is a label conflict and must be reviewed by a human.

## Step 3.3: Selection-artifact (shortcut) check

**Prompt:**
> Find the keyword lists used to select reports (`keywordSearch/data/concurrency.csv`, `memory.csv`, and the constants file) and load them as a set per class. For each of the 369 gold reports, compute whether title plus description contains any keyword from each list. Print, per class, the fraction of reports containing at least one concurrency keyword and at least one memory keyword. Then train a keyword-presence-only baseline (two binary features: any concurrency keyword, any memory keyword) with logistic regression using the project-grouped stratified 5-fold CV from `rq1_ablation.py`, and print macro-F1 and the confusion matrix. Report the result in `docs/DATA_NOTES.md` as "Shortcut baseline".

**Done when:** the result is recorded. **How to read it:** a high macro-F1 from two keyword flags means the classes are partly separable by how they were sampled, so every later model must be compared against this number, and the report must state it as a threat.

## Step 3.4: Write the processed dataset and the gate

**Prompt:**
> Merge the cleaned columns, flags, and `comments_clean` into `data/processed/gold_369.csv`. Required columns: `url, owner, repo, project, issue_number, root_cause, title, description, description_clean, code_text, stack_text, has_stack, has_code, created, closed, fix_date, fix_date_source, comments_clean, n_comments_prefix, comment_leak_flag`, plus all `flag_*` columns. Add `tests/test_gold.py` asserting: 369 rows, class counts 122/121/126, no duplicate urls, no null `root_cause`, no null `project`. Run `pytest`, then run the `run_ablation` function from `src/rq1_ablation.py` on `title` and `description_clean` only (comments not yet included) and save the output to `results/rq1_preliminary.csv`. Finally complete `docs/DATA_NOTES.md` with a "Gate decision" section stating the comment coverage percentage and which RQ4 path applies.

**Done when:** tests pass, `gold_369.csv` exists, and the gate section is filled.

---

## Step 4: Commit and share

1. Commit in small commits, written in your own words, and open a pull request from `stage1-data`.
2. Do not commit `.env`, `data/raw/`, or `data/comments/raw/`. Put the raw comment JSON in the shared team drive as a zip.
3. Send the team `docs/DATA_NOTES.md`. It is the Stage 1 evidence for the professor's "confirm comments" feedback.

## What to watch for (read before accepting any Copilot output)

- **Silent row loss.** After every step the row count should still be 369. If it is not, something dropped rows.
- **Leakage through comments or descriptions** mentioning the fix. Flag first, decide as a team.
- **Class-dependent coverage.** If one class has far fewer comments, the comments field will look useful for the wrong reason.
- **One dominant project.** `netty/netty` alone is about 20% of the gold set. With 5 grouped folds the fold holding netty will be much larger than the others. Report fold sizes, and also report a leave-one-project-out result for netty (train without it, test on it) as a robustness check.
- **Copilot inventing paths or columns.** The listing facts at the top of this file are verified. Everything marked unverified must come from a real printed output.
