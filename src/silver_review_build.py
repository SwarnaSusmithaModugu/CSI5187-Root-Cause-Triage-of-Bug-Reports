"""Create a two-coder wild-silver review sheet."""

import json
from pathlib import Path

import pandas as pd

from . import labeling_functions as LF


RAW = Path("data/raw")


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def context(url_set):
    contexts = {}
    for path in RAW.rglob("issuesDataWStats.json"):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for issue in data.get("issues", []):
            url = norm_url(issue["url"])
            if url in url_set:
                contexts[url] = (
                    LF._commit_msg(issue)[:300],
                    LF._changed_paths(issue)[:300],
                    LF._changed_methods(issue)[:300],
                )
    return contexts


def main():
    silver = pd.read_csv("data/processed/silver.csv")
    sample = (
        silver.sort_values("silver_conf", ascending=False)
        .groupby("root_cause")
        .head(23)
        .sample(frac=1, random_state=42)
        .head(45)
    )
    contexts = context(set(sample["url"].map(norm_url)))
    rows = []
    for _, row in sample.iterrows():
        message, paths, methods = contexts.get(
            norm_url(row["url"]), ("", "", "")
        )
        rows.append(
            {
                "url": row["url"],
                "silver_label": row["root_cause"],
                "silver_conf": row["silver_conf"],
                "commit_message": message,
                "changed_paths": paths,
                "changed_methods": methods,
                "coder_a": "",
                "coder_b": "",
            }
        )
    output = pd.DataFrame(rows)
    output.to_csv("data/interim/silver_review.csv", index=False)
    print(
        f"wrote data/interim/silver_review.csv with {len(output)} rows "
        "for two coders"
    )
    print(
        "coders fill coder_a and coder_b with "
        "concurrency/memory/semantic/unsure, judging from the FIX only"
    )


if __name__ == "__main__":
    main()
