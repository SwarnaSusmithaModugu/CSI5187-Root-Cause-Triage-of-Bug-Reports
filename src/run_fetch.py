"""Load .env and run the researcher-provided resumable comment fetcher."""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from . import fetch_comments


def main():
    load_dotenv()
    if not os.environ.get("GITHUB_TOKEN"):
        raise SystemExit("GITHUB_TOKEN not set in .env")

    gold_path = Path("data/interim/gold_joined.csv")
    output_dir = Path("data/comments")
    gold = pd.read_csv(gold_path)
    if len(gold) != 369 or gold["url"].nunique() != 369:
        raise ValueError("Expected 369 rows and 369 unique URLs in gold_joined.csv")

    gold[["url", "fix_date", "closed"]].to_csv(
        "data/interim/gold_urls.csv", index=False
    )
    fetch_comments.run("data/interim/gold_urls.csv", output_dir)


if __name__ == "__main__":
    main()
