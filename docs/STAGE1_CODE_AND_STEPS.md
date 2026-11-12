# CSI5187 Stage 1: Code and Steps (single file)

Continues from where you are now: setup done, `data/interim/labels.csv` built with 369 rows.
Each section has the code (with its target path) and the instructions to run it. Do the sections in order.

**Rules for Copilot (repeat if it drifts):**
- Do not rewrite `load_projects.py`, `rq1_ablation.py`, or `fetch_comments.py`. They are mine, not part of the dataset. If missing from `src/`, ask me for them, do not reimplement.
- Never fabricate a number, label, path, or comment. If something is missing, stop and report.
- Never delete rows. Flag them in a column and report counts.
- Raw data under `data/raw/` is read-only.
- After every section the gold row count must still be 369. If not, stop.

Confirmed paths (from your extraction, do not re-guess):
- Labels folders: `data/raw/mlClassifier/data/bugreports/{concurrency,memory,semantic}`
- Trainingset files: `data/raw/mlClassifier/data/trainingset_*.csv`
- Dataset doc: `data/raw/mlClassifier/data/dataset_composition.txt`
- Keyword lists: `data/raw/keywordSearch/data/`
- Project JSON: each project folder holds `issuesDataWStats.json` (found under `data/raw/`)
- `config.json` and `exampleIssue.json` under `data/raw/`

---

## Section A: Fix the notes and check silver overlap

First correct `docs/DATA_NOTES.md`: the "Setup inventory" section says 0 files found and parsing stopped, which contradicts the rest. Replace it with one line: the code clone has no corpus, so the release was extracted from the zip, and record where the zip came from (Zenodo DOI 10.5281/zenodo.3973048 or the repo's `AmadeusGithubBugDataset.zip`).

Then write provenance answers by reading the docs, and run the overlap check below. The overlap matters because the three `trainingset_*.csv` files (5528 + 3370 + 2640 rows) are a ready-made larger labeled set. If the 369 gold reports are not inside them, they are a clean silver training set. If they overlap, the overlap must be removed before any training.

**`src/provenance.py`**
```python
"""Check overlap between the 369 gold reports and the trainingset_*.csv files,
and print heads of the provenance docs so the answers can be quoted by hand."""
import re
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
TRAIN_DIR = RAW / "mlClassifier" / "data"
LABELS = Path("data/interim/labels.csv")

def norm_url(u):
    return str(u).strip().lower().replace("http://", "https://").rstrip("/")

def find_one(name):
    hits = list(RAW.rglob(name))
    return hits[0] if hits else None

def overlap_check():
    gold = pd.read_csv(LABELS)
    gold_urls = set(gold["url"].map(norm_url))
    gold_by_class = {c: set(g["url"].map(norm_url)) for c, g in gold.groupby("root_cause")}
    print(f"gold urls: {len(gold_urls)}")
    for f in sorted(TRAIN_DIR.glob("trainingset_*.csv")):
        df = pd.read_csv(f)
        url_col = next((c for c in df.columns if c.lower() == "url"), None)
        if url_col is None:
            print(f"{f.name}: NO url column, columns = {list(df.columns)[:12]}")
            continue
        turls = set(df[url_col].map(norm_url))
        inter = gold_urls & turls
        print(f"{f.name}: rows={len(df)} urls={len(turls)} overlap_with_gold={len(inter)}")
        for c, s in gold_by_class.items():
            print(f"    gold {c} inside this file: {len(s & turls)}")
    # project overlap: do the trainingset files share projects with gold?
    def proj(u):
        m = re.search(r"github\.com/([^/]+/[^/]+)/", u + "/")
        return m.group(1).lower() if m else None
    gold_projects = {proj(u) for u in gold_urls}
    all_train = set()
    for f in TRAIN_DIR.glob("trainingset_*.csv"):
        df = pd.read_csv(f)
        uc = next((c for c in df.columns if c.lower() == "url"), None)
        if uc:
            all_train |= {proj(u) for u in df[uc].map(norm_url)}
    print(f"gold projects: {len(gold_projects)}  shared with trainingset: {len(gold_projects & all_train)}")

def print_doc_heads():
    for name, n in [("config.json", 50), ("exampleIssue.json", 60),
                    ("dataset_composition.txt", 80), ("README.md", 120)]:
        p = find_one(name)
        print(f"\n===== {name} =====  ({p})")
        if p:
            print("\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:n]))

if __name__ == "__main__":
    print_doc_heads()
    print("\n----- OVERLAP -----")
    overlap_check()
```

**Run and prompt:**
> Run `python -m src.provenance`. Then add a "Dataset provenance" section to `docs/DATA_NOTES.md` answering only from the printed docs, with exact quotes: (a) how 54,755 and 10,459 arise, (b) how the 369 were chosen, (c) how each class was sampled (keyword search or random), (d) the label source, (e) what the trainingset files are and how their labels were assigned. Write "not stated" where the docs do not say. Record the overlap numbers. Replace the contradictory "Setup inventory" section with the one-line correction.

**Stop rule:** if gold reports appear inside the trainingset files, report the count per class and do not plan to train on those files until the overlap is removed.

---

## Section B: Build the gold join

Load the issue JSON for the 61 gold projects, join to the labels, and derive the fix dates. This confirms the labels connect to the issue metadata, which is the gate before spending API calls.

**`src/build_gold.py`**
```python
"""Join the 369 labels to their issue JSON, derive fix dates, save gold_joined.csv.
Reads issuesDataWStats.json per project. Fails loudly on anything unexpected (no silent drops)."""
import json
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
LABELS = Path("data/interim/labels.csv")
OUT = Path("data/interim/gold_joined.csv")

def norm_url(u):
    return str(u).strip().lower().replace("http://", "https://").rstrip("/")

def index_project_files():
    """folder name (lowercased) -> path of its issuesDataWStats.json"""
    idx = {}
    for p in RAW.rglob("issuesDataWStats.json"):
        idx[p.parent.name.lower()] = p
    return idx

def earliest(dates):
    dates = [d for d in dates if d]
    return min(dates) if dates else None

def load_issues(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = []
    for i in d.get("issues", []):
        cd = i.get("commitsDetails", []) or []
        rows.append({
            "url": i["url"],
            "project": d["projectName"],
            "title": i.get("title") or "",
            "description": i.get("body") or "",
            "user": i.get("user"),
            "created": i.get("created"),
            "closed": i.get("closed"),
            "has_commits": bool(i.get("commits")),
            "fix_authored": earliest(c.get("authoredDateTime") for c in cd),
            "fix_committed": earliest(c.get("commitDateTime") for c in cd),
        })
    return pd.DataFrame(rows)

def main():
    labels = pd.read_csv(LABELS)
    labels["_k"] = labels["url"].map(norm_url)
    need = (labels["owner"].astype(str) + "_" + labels["repo"].astype(str)).str.lower().unique()
    idx = index_project_files()
    missing_proj = [p for p in need if p not in idx]
    if missing_proj:
        print(f"WARNING: {len(missing_proj)} gold project folders not found: {missing_proj[:10]}")
    frames = [load_issues(idx[p]) for p in need if p in idx]
    allissues = pd.concat(frames, ignore_index=True)
    allissues["_k"] = allissues["url"].map(norm_url)
    allissues = allissues.drop_duplicates("_k")

    joined = labels.merge(allissues.drop(columns=["url"]), on="_k", how="left", suffixes=("", "_iss"))
    matched = joined["title"].notna().sum()
    print(f"labels: {len(labels)}  matched to issue json: {matched}  unmatched: {len(labels) - matched}")
    for _, r in joined[joined["title"].isna()].iterrows():
        folder = f"{r['owner']}_{r['repo']}".lower()
        reason = "project folder missing" if folder not in idx else "issue number not in project json"
        print(f"  UNMATCHED {r['url']} -> {reason}")

    joined["fix_date"] = joined["fix_authored"].fillna(joined["closed"])
    joined["fix_date_source"] = joined["fix_authored"].notna().map({True: "commit", False: "closed"})
    pre_file = (pd.to_datetime(joined["fix_date"], errors="coerce", utc=True)
                < pd.to_datetime(joined["created"], errors="coerce", utc=True)).sum()
    print(f"fix_date from commit: {(joined['fix_date_source']=='commit').sum()}  "
          f"from closed: {(joined['fix_date_source']=='closed').sum()}  "
          f"fix authored before issue created: {pre_file}")
    pc = joined["project"].value_counts()
    print(f"projects: {pc.notna().sum()}  largest: {pc.index[0]}={pc.iloc[0]} ({100*pc.iloc[0]/len(joined):.0f}%)")
    joined.drop(columns=["_k"]).to_csv(OUT, index=False)
    print(f"wrote {OUT} rows={len(joined)}")

if __name__ == "__main__":
    main()
```

**Run and prompt:**
> Run `python -m src.build_gold`. Paste the full printed output into `docs/DATA_NOTES.md` under "Gold join". Expected: matched 369, unmatched 0, projects 61, largest netty/netty about 20%. If matched is not 369, stop and list every unmatched url with its reason. Do not proceed to comments until this is 369.

---

## Section C: Fetch comments

Only after the join is 369. You create the token, Copilot runs the fetch.

**Your action:** create a fine-grained GitHub token (public repositories, read-only), put `GITHUB_TOKEN=...` in `.env`, confirm `.env` is gitignored. Do not paste the token into chat.

**`src/run_fetch.py`**
```python
"""Load .env, build gold_urls.csv, then call fetch_comments.run. Keeps the token out of argv."""
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import fetch_comments as F

def main():
    load_dotenv()
    if not os.environ.get("GITHUB_TOKEN"):
        raise SystemExit("GITHUB_TOKEN not set in .env")
    g = pd.read_csv("data/interim/gold_joined.csv")
    Path("data/interim").mkdir(parents=True, exist_ok=True)
    g[["url", "fix_date", "closed"]].to_csv("data/interim/gold_urls.csv", index=False)
    F.run("data/interim/gold_urls.csv", "data/comments")

if __name__ == "__main__":
    main()
```

**Run and prompt:**
> Run `python -m src.run_fetch` from the repo root so `src/fetch_comments.py` is importable. It is resumable, rerun the same command if it stops. When done, print `data/comments/coverage.txt` and the value counts of `data/comments/fetch_status.csv`.

**Stop rule:** if more than 5% of requests return an error other than 404 or 410, stop and report the status codes. Do not loop retries.

---

## Section D: Audit comments and leakage

**`src/audit_comments.py`**
```python
"""Coverage per class, top authors, three cut rules, leakage scan. Writes tables, deletes nothing."""
import re
from pathlib import Path
import pandas as pd

def norm_url(u):
    return str(u).strip().lower().replace("http://", "https://").rstrip("/")

def load():
    com = pd.read_csv("data/comments/comments_all.csv")
    gold = pd.read_csv("data/interim/gold_joined.csv")
    com["_k"] = com["url"].map(norm_url)
    gold["_k"] = gold["url"].map(norm_url)
    com = com.merge(gold[["_k", "root_cause", "fix_authored", "fix_committed", "closed"]], on="_k", how="left")
    com["comment_created"] = pd.to_datetime(com["comment_created"], utc=True, errors="coerce")
    for c in ["fix_authored", "fix_committed", "closed"]:
        com[c] = pd.to_datetime(com[c], utc=True, errors="coerce")
    return com, gold

def coverage(com, gold):
    human = com[~com["is_bot"].astype(bool)]
    print("=== coverage per class: reports with >=1 human comment before fix_authored ===")
    for rule in ["fix_authored", "fix_committed", "closed"]:
        pre = human[human["comment_created"] < human[rule]]
        per = pre.groupby("root_cause")["_k"].nunique()
        tot = gold.assign(_k=gold["url"].map(norm_url)).groupby("root_cause")["_k"].nunique()
        covered = pre["_k"].nunique()
        print(f"cut={rule}: total reports with usable pre-cut human comment = {covered}/{len(gold)} "
              f"({100*covered/len(gold):.0f}%) ; per class { {k:int(per.get(k,0)) for k in tot.index} }")

def authors(com):
    print("\n=== top 15 comment authors ===")
    print(com.groupby(["author", "is_bot"]).size().sort_values(ascending=False).head(15).to_string())

def lengths(com):
    human = com[~com["is_bot"].astype(bool)]
    pre = human[human["comment_created"] < human["fix_authored"]]
    n = pre.groupby("_k").size()
    ln = pre.assign(L=pre["comment_text"].str.len()).groupby("_k")["L"].sum()
    print(f"\npre-fix human comment count: median={n.median()} p90={n.quantile(.9)}")
    print(f"pre-fix char length: median={ln.median()} p90={ln.quantile(.9)}")

def leakage(com):
    pats = {
        "fix_in_by_with": r"fix(ed|es)?\s+(in|by|with)",
        "closes_fixes_resolves": r"(closes|fixes|resolves)\s+#?\d+",
        "pr": r"pull request|\bPR\b",
        "commit_word_sha": r"commit\s+[0-9a-f]{7,40}",
        "bare_sha": r"\b[0-9a-f]{7,40}\b",
        "merged": r"\bmerged\b",
        "patch": r"\bpatch\b",
    }
    human = com[~com["is_bot"].astype(bool)]
    pre = human[human["comment_created"] < human["fix_authored"]].copy()
    pre["text"] = pre["comment_text"].fillna("")
    print("\n=== leakage scan (pre-fix human comments) ===")
    flag = pd.Series(False, index=pre.index)
    for name, pat in pats.items():
        m = pre["text"].str.contains(pat, case=False, regex=True, na=False)
        flag |= m
        print(f"{name}: {m.sum()} comments ; per class { pre[m].groupby('root_cause').size().to_dict() }")
        for s in pre.loc[m, "text"].head(3):
            mm = re.search(pat, s, re.I)
            if mm:
                a, b = max(0, mm.start()-40), min(len(s), mm.end()+40)
                print("    …", s[a:b].replace("\n", " "))
    leak_urls = pre.loc[flag, "_k"].nunique()
    print(f"reports with any leak-flagged pre-fix comment: {leak_urls}")

if __name__ == "__main__":
    com, gold = load()
    coverage(com, gold)
    authors(com)
    lengths(com)
    leakage(com)
```

**Run and prompt:**
> Run `python -m src.audit_comments` and paste every table into `docs/DATA_NOTES.md` under "Comment recovery". From the author table, list any automated accounts to add to `BOT_LOGINS` in `fetch_comments.py`, but do not edit the list yourself, show me the candidates.

**Gate decision (team, not Copilot):** about 70% or more of the 369 with a usable pre-fix human comment, and no large gap between classes, means live RQ4. Otherwise RQ4 runs static. Record the decision in the notes.

---

## Section E: Clean text (new columns only)

**`src/clean.py`**
```python
"""Non-destructive cleaning. Adds columns, never overwrites title/description/comments."""
import re, unicodedata
import pandas as pd

CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
INDENT_CODE = re.compile(r"(?:^(?: {4}|\t).*\n?)+", re.MULTILINE)
STACK_FRAME = re.compile(r"^\s*at\s+[\w.$<>]+\(.*?\)\s*$", re.MULTILINE)
EXC_LINE = re.compile(r"^.*?\b[\w.]*(Exception|Error)\b.*$", re.MULTILINE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
MENTION = re.compile(r"(?<!\w)@[A-Za-z0-9_-]+")
REF = re.compile(r"(?<!\w)#\d+")
WS = re.compile(r"\s+")

def extract(pattern, text):
    found = pattern.findall(text)
    return pattern.sub(" ", text), (found if isinstance(found, list) else [])

def clean_text(raw):
    if not isinstance(raw, str):
        return {"clean": "", "code": "", "stack": "", "has_code": False, "has_stack": False}
    t = unicodedata.normalize("NFKC", raw)
    t = HTML_COMMENT.sub(" ", t)
    t = MD_IMAGE.sub(" ", t)
    code_blocks = CODE_FENCE.findall(t); t = CODE_FENCE.sub(" ", t)
    ind = INDENT_CODE.findall(t); t = INDENT_CODE.sub(" ", t)
    stack = STACK_FRAME.findall(t); t = STACK_FRAME.sub(" ", t)
    exc = EXC_LINE.findall(t); t = EXC_LINE.sub(" ", t)
    t = URL.sub("<URL>", t)
    t = SHA.sub("<SHA>", t)
    t = MENTION.sub("<USER>", t)
    t = REF.sub("<REF>", t)
    t = WS.sub(" ", t).strip()
    code = " ".join(code_blocks + ind)
    stack_text = " ".join(stack + [e if isinstance(e, str) else "" for e in exc])
    return {"clean": t, "code": code, "stack": stack_text,
            "has_code": bool(code.strip()), "has_stack": bool(stack_text.strip())}

def add_clean_columns(df, src_col, prefix):
    out = df[src_col].apply(clean_text).apply(pd.Series)
    df[f"{prefix}_clean"] = out["clean"]
    df[f"{prefix}_code"] = out["code"]
    df[f"{prefix}_stack"] = out["stack"]
    df[f"{prefix}_has_code"] = out["has_code"]
    df[f"{prefix}_has_stack"] = out["has_stack"]
    df[f"{prefix}_len_chars"] = df[f"{prefix}_clean"].str.len()
    df[f"{prefix}_len_tokens"] = df[f"{prefix}_clean"].str.split().apply(len)
    return df
```

**`tests/test_clean.py`**
```python
from src.clean import clean_text

def test_url_sha_mention_ref():
    r = clean_text("see https://x.com/a and @bob fixes #12 at deadbeef1234567")
    assert "<URL>" in r["clean"] and "<USER>" in r["clean"] and "<REF>" in r["clean"]
    assert "http" not in r["clean"]

def test_html_comment_removed():
    assert "secret" not in clean_text("text <!-- secret --> more")["clean"]

def test_code_fence_extracted():
    r = clean_text("before ```java\nint x=1;\n``` after")
    assert r["has_code"] and "int x=1" in r["code"] and "int x=1" not in r["clean"]

def test_stack_extracted():
    r = clean_text("boom\n    at com.foo.Bar.run(Bar.java:12)\nend")
    assert r["has_stack"] and "Bar.java" in r["stack"]

def test_non_string_safe():
    assert clean_text(None)["clean"] == ""
```

**Prompt:**
> Add `src/clean.py` and `tests/test_clean.py`. Run `pytest tests/test_clean.py -q`. All pass before continuing.

---

## Section F: Quality flags (flag, never delete)

**`src/quality.py`**
```python
"""Boolean flag columns for quality issues. Nothing is removed."""
import re
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def add_flags(df):
    text = (df["title"].fillna("") + " " + df["description_clean"].fillna("")).str.strip()
    df["flag_empty"] = df["description_clean"].fillna("").str.len() < 20
    heading = df["description_clean"].fillna("").str.count(r"(?i)steps to reproduce|expected|actual|environment")
    df["flag_template_only"] = (heading >= 2) & (df["description_len_tokens"] < 25)
    def nonlatin(s):
        s = str(s); alpha = [c for c in s if c.isalpha()]
        if not alpha: return 0.0
        return sum(ord(c) > 127 for c in alpha) / len(alpha)
    df["flag_non_english"] = text.apply(nonlatin) > 0.30
    df["flag_is_pr"] = df["url"].str.contains("/pull/", na=False)
    df["flag_bot_author"] = df["user"].astype(str).str.lower().str.contains(r"bot|\[bot\]|ci|jenkins", na=False)
    norm = text.str.lower().str.replace(r"\s+", " ", regex=True)
    df["flag_exact_dup"] = norm.duplicated(keep=False) & (norm.str.len() > 0)

    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vec.fit_transform(text)
    sim = cosine_similarity(X)
    np.fill_diagonal(sim, 0)
    near = (sim > 0.9)
    df["flag_near_dup"] = near.any(axis=1)
    pairs, cross = [], []
    labels = df["root_cause"].values
    for i, j in zip(*np.where(np.triu(near))):
        pairs.append((df.iloc[i]["url"], df.iloc[j]["url"], round(float(sim[i, j]), 3),
                      labels[i], labels[j]))
        if labels[i] != labels[j]:
            cross.append(pairs[-1])
    df["flag_cross_label_dup"] = False
    cross_urls = {u for p in cross for u in p[:2]}
    df.loc[df["url"].isin(cross_urls), "flag_cross_label_dup"] = True
    print("flag counts:")
    for c in [c for c in df.columns if c.startswith("flag_")]:
        print(f"  {c}: {int(df[c].sum())}")
    print(f"near-dup pairs: {len(pairs)}  cross-label pairs: {len(cross)}")
    for p in cross:
        print("  CROSS-LABEL:", p)
    return df, pairs, cross
```

**Prompt:**
> Add `src/quality.py`. After the gold table is assembled in the next section, run it, paste the flag counts and every cross-label pair into `docs/DATA_NOTES.md`. A cross-label near-duplicate is a label conflict, list it for human review, do not resolve it automatically.

---

## Section G: Shortcut (selection-bias) baseline

**`src/shortcut_baseline.py`**
```python
"""Can two keyword-presence features alone separate the classes? If yes, selection bias is real."""
import re
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score, confusion_matrix

KW_DIR = Path("data/raw/keywordSearch/data")

def load_keywords(fname):
    p = KW_DIR / fname
    try:
        df = pd.read_csv(p, header=None)
        words = df.iloc[:, 0].astype(str)
    except Exception:
        words = pd.Series(p.read_text(encoding="utf-8", errors="replace").splitlines())
    return {w.strip().lower() for w in words if w.strip() and not w.startswith("#")}

def main():
    gold = pd.read_csv("data/processed/gold_369.csv")
    conc = load_keywords("concurrency.csv")
    mem = load_keywords("memory.csv")
    text = (gold["title"].fillna("") + " " + gold["description"].fillna("")).str.lower()
    def has_any(t, kws): return int(any(re.search(r"\b" + re.escape(k) + r"\b", t) for k in kws))
    X = np.array([[has_any(t, conc), has_any(t, mem)] for t in text])
    y = gold["root_cause"].values
    groups = gold["project"].values
    print("fraction with a concurrency keyword, by class:")
    print(pd.Series(X[:, 0], index=y).groupby(level=0).mean().to_dict())
    print("fraction with a memory keyword, by class:")
    print(pd.Series(X[:, 1], index=y).groupby(level=0).mean().to_dict())
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    preds = np.empty(len(y), dtype=object)
    for tr, te in cv.split(X, y, groups):
        clf = LogisticRegression(max_iter=1000).fit(X[tr], y[tr])
        preds[te] = clf.predict(X[te])
    print("shortcut macro-F1:", round(f1_score(y, preds, average="macro"), 3))
    print("confusion matrix (concurrency, memory, semantic):")
    print(confusion_matrix(y, preds, labels=["concurrency", "memory", "semantic"]))

if __name__ == "__main__":
    main()
```

**Prompt:**
> Run `python -m src.shortcut_baseline` after the processed gold file exists. Record the macro-F1 and matrix in `docs/DATA_NOTES.md` as "Shortcut baseline". Every later model must beat this number, and it goes in the threats section.

---

## Section H: Build the processed gold file

**`src/build_processed.py`**
```python
"""Assemble data/processed/gold_369.csv from the joined gold, comments, cleaning, and flags."""
from pathlib import Path
import pandas as pd
from src.clean import add_clean_columns
from src.quality import add_flags

def norm_url(u):
    return str(u).strip().lower().replace("http://", "https://").rstrip("/")

def prefix_comments():
    """Concatenate human comments posted before fix_authored, per report."""
    com = pd.read_csv("data/comments/comments_all.csv")
    gold = pd.read_csv("data/interim/gold_joined.csv")
    com["_k"] = com["url"].map(norm_url)
    g = gold.assign(_k=gold["url"].map(norm_url))[["_k", "fix_authored", "closed"]]
    com = com.merge(g, on="_k", how="left")
    com["comment_created"] = pd.to_datetime(com["comment_created"], utc=True, errors="coerce")
    cut = pd.to_datetime(com["fix_authored"].fillna(com["closed"]), utc=True, errors="coerce")
    human = com[(~com["is_bot"].astype(bool)) & (com["comment_created"] < cut)]
    agg = human.sort_values("comment_created").groupby("_k")["comment_text"].apply(lambda s: " ".join(s.astype(str)))
    cnt = human.groupby("_k").size()
    return agg.rename("comments"), cnt.rename("n_comments_prefix")

def main():
    gold = pd.read_csv("data/interim/gold_joined.csv")
    gold["_k"] = gold["url"].map(norm_url)
    try:
        comments, counts = prefix_comments()
        gold = gold.merge(comments, on="_k", how="left").merge(counts, on="_k", how="left")
    except FileNotFoundError:
        print("no comments file yet, comments left empty")
        gold["comments"] = ""; gold["n_comments_prefix"] = 0
    gold["comments"] = gold["comments"].fillna("")
    gold["n_comments_prefix"] = gold["n_comments_prefix"].fillna(0).astype(int)

    gold = add_clean_columns(gold, "description", "description")
    gold = add_clean_columns(gold, "comments", "comments")
    gold, pairs, cross = add_flags(gold)

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    gold.drop(columns=["_k"]).to_csv("data/processed/gold_369.csv", index=False)
    assert len(gold) == 369, f"row count changed: {len(gold)}"
    print(f"wrote data/processed/gold_369.csv rows={len(gold)} cols={gold.shape[1]}")

if __name__ == "__main__":
    main()
```

**`tests/test_gold.py`**
```python
import pandas as pd

def test_gold():
    g = pd.read_csv("data/processed/gold_369.csv")
    assert len(g) == 369
    assert g["root_cause"].value_counts().to_dict() == {"semantic": 126, "concurrency": 122, "memory": 121}
    assert g["url"].nunique() == 369
    assert g["root_cause"].notna().all()
    assert g["project"].notna().all()
```

**Prompt:**
> Run `python -m src.build_processed`, then `pytest tests/test_gold.py -q`. Then run the preliminary RQ1: build a temporary frame with `description` set to `description_clean` and no `comments` column, call `run_ablation` from `src/rq1_ablation.py` on it, and save to `results/rq1_preliminary.csv`. This uses title and cleaned description only, comments are added later. Paste the result.

---

## Section I: Commit

**Prompt:**
> Stage the new `src/` files, `tests/`, `docs/DATA_NOTES.md`, and the `data/interim` and `data/processed` CSVs (not `data/raw`, not `data/comments/raw`, not `.env`). Commit in small commits in your own words, then open a pull request from `stage1-data`. Confirm `git status` shows no raw data or secrets staged.

---

## Read before accepting any output
- Row count must stay 369 after every section.
- The provenance overlap (Section A) decides whether the trainingset files are a free silver set or a leakage risk. Do not train on them until that is settled.
- `netty/netty` is about 20% of the gold set, so report fold sizes and a leave-one-project-out check on netty later.
- A high shortcut-baseline F1 means the classes are partly separable by how they were sampled. That is a threat to report, not a result to celebrate.
- Cross-label near-duplicates are label conflicts for human review.
