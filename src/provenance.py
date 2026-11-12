"""Check gold/training overlap and print provenance document excerpts."""

import re
from pathlib import Path

import pandas as pd


RAW = Path("data/raw")
TRAIN_DIR = RAW / "mlClassifier" / "data"
LABELS = Path("data/interim/labels.csv")


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def find_one(name):
    hits = list(RAW.rglob(name))
    return hits[0] if hits else None


def overlap_check():
    gold = pd.read_csv(LABELS)
    gold_urls = set(gold["url"].map(norm_url))
    gold_by_class = {
        root_cause: set(group["url"].map(norm_url))
        for root_cause, group in gold.groupby("root_cause")
    }
    print(f"gold urls: {len(gold_urls)}")
    training_urls = set()
    for path in sorted(TRAIN_DIR.glob("trainingset_*.csv")):
        frame = pd.read_csv(path)
        url_column = next(
            (column for column in frame.columns if column.lower() == "url"),
            None,
        )
        if url_column is None:
            print(
                f"{path.name}: NO url column, "
                f"columns = {list(frame.columns)[:12]}"
            )
            continue
        urls = set(frame[url_column].map(norm_url))
        training_urls |= urls
        overlap = gold_urls & urls
        print(
            f"{path.name}: rows={len(frame)} urls={len(urls)} "
            f"overlap_with_gold={len(overlap)}"
        )
        for root_cause, class_urls in gold_by_class.items():
            print(
                f"    gold {root_cause} inside this file: "
                f"{len(class_urls & urls)}"
            )

    def project(url):
        match = re.search(r"github\.com/([^/]+/[^/]+)/", url + "/")
        return match.group(1).lower() if match else None

    gold_projects = {project(url) for url in gold_urls}
    training_projects = {project(url) for url in training_urls}
    print(
        f"gold projects: {len(gold_projects)}  "
        f"shared with trainingset: {len(gold_projects & training_projects)}"
    )


def print_doc_heads():
    for name, line_count in [
        ("config.json", 50),
        ("exampleIssue.json", 60),
        ("dataset_composition.txt", 80),
        ("README.md", 120),
    ]:
        path = find_one(name)
        print(f"\n===== {name} =====  ({path})")
        if path:
            lines = path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            print("\n".join(lines[:line_count]))


if __name__ == "__main__":
    print_doc_heads()
    print("\n----- OVERLAP -----")
    overlap_check()
