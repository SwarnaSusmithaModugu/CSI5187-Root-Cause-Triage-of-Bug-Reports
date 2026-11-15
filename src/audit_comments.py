"""Audit recovered comments for coverage, authorship, and fix leakage."""

import re

import pandas as pd


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def load():
    comments = pd.read_csv("data/comments/comments_all.csv")
    gold = pd.read_csv("data/interim/gold_joined.csv")
    comments["_k"] = comments["url"].map(norm_url)
    gold["_k"] = gold["url"].map(norm_url)
    comments = comments.merge(
        gold[["_k", "root_cause", "fix_authored", "fix_committed", "closed"]],
        on="_k",
        how="left",
    )
    comments["comment_created"] = pd.to_datetime(
        comments["comment_created"], utc=True, errors="coerce"
    )
    for column in ["fix_authored", "fix_committed", "closed"]:
        comments[column] = pd.to_datetime(
            comments[column], utc=True, errors="coerce"
        )
    return comments, gold


def coverage(comments, gold):
    human = comments[~comments["is_bot"].astype(bool)]
    print("=== coverage per class: reports with >=1 human comment before cut ===")
    totals = gold.groupby("root_cause")["_k"].nunique()
    for rule in ["fix_authored", "fix_committed", "closed"]:
        pre = human[human["comment_created"] < human[rule]]
        per_class = pre.groupby("root_cause")["_k"].nunique()
        covered = pre["_k"].nunique()
        values = {
            label: int(per_class.get(label, 0)) for label in totals.index
        }
        print(
            f"cut={rule}: total={covered}/{len(gold)} "
            f"({100 * covered / len(gold):.0f}%) ; per class {values}"
        )


def authors(comments):
    print("\n=== top 15 comment authors ===")
    print(
        comments.groupby(["author", "is_bot"])
        .size()
        .sort_values(ascending=False)
        .head(15)
        .to_string()
    )


def lengths(comments):
    human = comments[~comments["is_bot"].astype(bool)]
    pre = human[human["comment_created"] < human["fix_authored"]]
    counts = pre.groupby("_k").size()
    chars = (
        pre.assign(length=pre["comment_text"].fillna("").str.len())
        .groupby("_k")["length"]
        .sum()
    )
    print(
        f"\npre-fix human comment count: median={counts.median()} "
        f"p90={counts.quantile(.9)}"
    )
    print(
        f"pre-fix char length: median={chars.median()} "
        f"p90={chars.quantile(.9)}"
    )


def leakage(comments):
    patterns = {
        "fix_in_by_with": r"fix(ed|es)?\s+(in|by|with)",
        "closes_fixes_resolves": r"(closes|fixes|resolves)\s+#?\d+",
        "pr": r"pull request|\bPR\b",
        "commit_word_sha": r"commit\s+[0-9a-f]{7,40}",
        "bare_sha": r"\b[0-9a-f]{7,40}\b",
        "merged": r"\bmerged\b",
        "patch": r"\bpatch\b",
    }
    human = comments[~comments["is_bot"].astype(bool)]
    pre = human[human["comment_created"] < human["fix_authored"]].copy()
    pre["text"] = pre["comment_text"].fillna("")
    print("\n=== leakage scan (pre-fix human comments) ===")
    flagged = pd.Series(False, index=pre.index)
    for name, pattern in patterns.items():
        matches = pre["text"].str.contains(
            pattern, case=False, regex=True, na=False
        )
        flagged |= matches
        print(
            f"{name}: {matches.sum()} comments ; per class "
            f"{pre[matches].groupby('root_cause').size().to_dict()}"
        )
        for text in pre.loc[matches, "text"].head(5):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                print("    ...", text[start:end].replace("\n", " "))
    print(
        "reports with any leak-flagged pre-fix comment: "
        f"{pre.loc[flagged, '_k'].nunique()}"
    )


if __name__ == "__main__":
    comments, gold = load()
    coverage(comments, gold)
    authors(comments)
    lengths(comments)
    leakage(comments)
