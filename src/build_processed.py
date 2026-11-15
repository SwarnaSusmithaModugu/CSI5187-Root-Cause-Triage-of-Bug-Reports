"""Assemble the non-destructive processed 369-report gold dataset."""

import re
from pathlib import Path

import pandas as pd

from .clean import add_clean_columns
from .quality import add_flags


LEAKAGE_PATTERNS = [
    r"fix(ed|es)?\s+(in|by|with)",
    r"(closes|fixes|resolves)\s+#?\d+",
    r"pull request|\bPR\b",
    r"commit\s+[0-9a-f]{7,40}",
    r"\b[0-9a-f]{7,40}\b",
    r"\bmerged\b",
    r"\bpatch\b",
]


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def prefix_comments():
    comments = pd.read_csv("data/comments/comments_all.csv")
    gold = pd.read_csv("data/interim/gold_joined.csv")
    comments["_k"] = comments["url"].map(norm_url)
    gold_keys = gold.assign(_k=gold["url"].map(norm_url))[
        ["_k", "fix_authored", "closed"]
    ]
    comments = comments.merge(gold_keys, on="_k", how="left")
    comments["comment_created"] = pd.to_datetime(
        comments["comment_created"], utc=True, errors="coerce"
    )
    cut = pd.to_datetime(
        comments["fix_authored"].fillna(comments["closed"]),
        utc=True,
        errors="coerce",
    )
    human = comments[
        (~comments["is_bot"].astype(bool))
        & (comments["comment_created"] < cut)
    ].copy()
    human["comment_text"] = human["comment_text"].fillna("")
    human["comment_leak_match"] = False
    for pattern in LEAKAGE_PATTERNS:
        human["comment_leak_match"] |= human["comment_text"].str.contains(
            pattern, case=False, regex=True, na=False
        )
    grouped = (
        human.sort_values("comment_created")
        .groupby("_k")["comment_text"]
        .apply(lambda values: " ".join(values.astype(str)))
    )
    counts = human.groupby("_k").size()
    leaks = human.groupby("_k")["comment_leak_match"].any()
    return (
        grouped.rename("comments"),
        counts.rename("n_comments_prefix"),
        leaks.rename("comment_leak_flag"),
    )


def main():
    gold = pd.read_csv("data/interim/gold_joined.csv")
    gold["_k"] = gold["url"].map(norm_url)
    comments, counts, leaks = prefix_comments()
    gold = (
        gold.merge(comments, on="_k", how="left")
        .merge(counts, on="_k", how="left")
        .merge(leaks, on="_k", how="left")
    )
    gold["comments"] = gold["comments"].fillna("")
    gold["n_comments_prefix"] = gold["n_comments_prefix"].fillna(0).astype(int)
    gold["comment_leak_flag"] = gold["comment_leak_flag"].fillna(False).astype(bool)

    gold = add_clean_columns(gold, "description", "description")
    gold = add_clean_columns(gold, "comments", "comments")
    gold = gold.rename(
        columns={
            "description_code": "code_text",
            "description_stack": "stack_text",
            "description_has_code": "has_code",
            "description_has_stack": "has_stack",
            "description_len_chars": "desc_len_chars",
            "description_len_tokens": "description_len_tokens",
            "comments_clean": "comments_clean",
        }
    )
    gold, pairs, cross_label_pairs = add_flags(gold)
    if len(gold) != 369:
        raise ValueError(f"Expected 369 rows, found {len(gold)}")

    required = [
        "url", "owner", "repo", "root_cause", "title", "description",
        "description_clean", "code_text", "stack_text", "has_stack",
        "has_code", "created", "closed", "fix_date", "fix_date_source",
        "comments_clean", "n_comments_prefix", "comment_leak_flag",
    ]
    missing = [column for column in required if column not in gold.columns]
    if missing:
        raise ValueError(f"Missing processed columns: {missing}")
    output = Path("data/processed/gold_369.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    gold.drop(columns=["_k"]).to_csv(output, index=False)
    print(
        f"wrote {output} rows={len(gold)} cols={gold.shape[1]} "
        f"near_pairs={len(pairs)} cross_label_pairs={len(cross_label_pairs)}"
    )


if __name__ == "__main__":
    main()
