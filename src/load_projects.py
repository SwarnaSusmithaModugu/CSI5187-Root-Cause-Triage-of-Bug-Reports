"""Load Amadeus per-project JSON files into one flat DataFrame.

Each project file is a dict: projectName, bugLabels, captureTime, issues[].
projectName lives at file level, so we attach it to every issue (needed for grouped CV).
Leakage columns (labels, closed, ttf, commits, commitsDetails) are NOT kept as model inputs.
"""
import json
from pathlib import Path
import pandas as pd

KEEP = ["url", "project", "title", "description", "created", "closed", "fix_date"]  # closed + fix_date only used to cut comments

def earliest_fix(issue):
    """earliest authored time over the linked commits, or None. naive strings, treated as utc"""
    ts = [c.get("authoredDateTime") or c.get("commitDateTime") for c in issue.get("commitsDetails", [])]
    ts = [t for t in ts if t]
    return min(ts) if ts else None

def load_project_file(path):
    d = json.load(open(path, encoding="utf-8"))
    rows = []
    for i in d["issues"]:
        rows.append({
            "url": i["url"],
            "project": d["projectName"],
            "title": i.get("title") or "",
            "description": i.get("body") or "",
            "created": i.get("created"),
            "closed": i.get("closed"),
            "has_commits": bool(i.get("commits")),
            "fix_date": earliest_fix(i),
        })
    return pd.DataFrame(rows)

def load_all(data_dir):
    """Load every project file under data_dir (json or txt, nested folders ok).
    Files that are not a project dict (readmes etc) are skipped and listed."""
    frames, skipped = [], []
    for p in sorted(list(Path(data_dir).rglob("*.json")) + list(Path(data_dir).rglob("*.txt"))):
        try:
            frames.append(load_project_file(p))
        except (ValueError, KeyError, TypeError):
            skipped.append(p.name)
    print(f"projects loaded: {len(frames)}  skipped: {len(skipped)} {skipped[:5]}")
    return pd.concat(frames, ignore_index=True)

def norm_url(u):
    """lowercase, https, no trailing slash, so the same issue matches across files"""
    u = str(u).strip().lower().replace("http://", "https://").rstrip("/")
    return u

def join_gold(df, labels_df):
    """labels_df needs columns: url, root_cause. TODO Stage 1: build it from fault_type_prediction.
    Inner join keeps only the hand-labeled reports (should be 369). Prints what failed to match."""
    a, b = df.copy(), labels_df[["url", "root_cause"]].copy()
    a["_k"], b["_k"] = a["url"].map(norm_url), b["url"].map(norm_url)
    out = a.merge(b.drop(columns="url"), on="_k", how="inner").drop(columns="_k")
    lost = set(b["_k"]) - set(a["_k"])
    print(f"gold labels: {len(b)}  matched: {len(out)}  unmatched: {len(lost)}")
    if lost:
        print("first unmatched:", sorted(lost)[:5])
    return out

def gold_report(g, n_splits=5):
    """sanity check on the joined gold table before any RQ1 number is trusted"""
    print("class counts:", g["root_cause"].value_counts().to_dict(), "(expect 122/121/126)")
    pc = g["project"].value_counts()
    print(f"projects: {len(pc)}  largest: {pc.index[0]} = {pc.iloc[0]} reports ({100*pc.iloc[0]/len(g):.0f}%)")
    if len(pc) < n_splits:
        print("WARNING: fewer projects than folds, grouped CV will fail")
    if pc.iloc[0] / len(g) > 0.25:
        print("WARNING: one project holds over 25% of the gold set, folds will be lopsided")
    from sklearn.model_selection import StratifiedGroupKFold
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
    for k, (tr, te) in enumerate(cv.split(g, g["root_cause"], g["project"])):
        print(f"fold {k}: test n={len(te)}", g.iloc[te]["root_cause"].value_counts().to_dict())

def attach_comments(df, comments_df):
    """comments_df columns: url, comment_text, comment_created.
    keep only comments posted before the earliest linked fix (fix_date, else closed).
    later comments often name the fix and leak the label."""
    cut = df[["url", "fix_date", "closed"]].copy()
    cut["cut"] = pd.to_datetime(cut["fix_date"].fillna(cut["closed"]), utc=True, errors="coerce")
    c = comments_df.merge(cut[["url", "cut"]], on="url", how="inner")
    c["comment_created"] = pd.to_datetime(c["comment_created"], utc=True, errors="coerce")
    c = c[c["comment_created"] < c["cut"]].sort_values("comment_created")
    agg = c.groupby("url")["comment_text"].apply(lambda x: " ".join(x)).rename("comments")
    out = df.merge(agg, on="url", how="left")
    out["comments"] = out["comments"].fillna("")
    return out
