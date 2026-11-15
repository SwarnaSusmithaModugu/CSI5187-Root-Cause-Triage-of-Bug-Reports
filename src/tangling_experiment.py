"""Prepare comparable author-label sheets for unfiltered and focused silver."""

import json
from pathlib import Path

import pandas as pd

from . import labeling_functions as lf


RAW = Path("data/raw")


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def context(urls):
    output = {}
    for path in sorted(RAW.rglob("issuesDataWStats.json")):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for issue in data.get("issues", []):
            url = norm_url(issue["url"])
            if url in urls:
                output[url] = (
                    lf._commit_msg(issue)[:300],
                    lf._changed_paths(issue)[:300],
                    lf._changed_methods(issue)[:300],
                )
    return output


def build_sheet(source, destination, seed=42):
    silver = pd.read_csv(source)
    sample = (
        silver.sort_values("silver_conf", ascending=False)
        .groupby("root_cause")
        .head(20)
        .sample(frac=1, random_state=seed)
        .head(40)
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
                "my_label": "",
            }
        )
    pd.DataFrame(rows).to_csv(destination, index=False)
    print(f"wrote {destination} with {len(rows)} rows")


def main():
    build_sheet(
        "data/processed/silver_unfiltered.csv",
        "data/interim/review_unfiltered.csv",
    )
    build_sheet(
        "data/processed/silver_focused.csv",
        "data/interim/review_focused.csv",
    )


if __name__ == "__main__":
    main()
