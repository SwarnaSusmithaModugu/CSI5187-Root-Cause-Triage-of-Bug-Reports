import re
from pathlib import Path

import pandas as pd

from .config import BUGREPORTS_DIR, PROJECT_ROOT


FILENAME_PATTERN = re.compile(
    r"^(?P<owner>[^_]+)_(?P<repo>.+)_issues_(?P<num>\d+)$"
)
EXPECTED_COUNTS = {"concurrency": 122, "memory": 121, "semantic": 126}


def build_labels(output_path: Path | None = None) -> pd.DataFrame:
    rows = []
    parse_failures = []
    for root_cause in EXPECTED_COUNTS:
        class_dir = BUGREPORTS_DIR / root_cause
        for source_file in sorted(class_dir.iterdir()):
            if not source_file.is_file():
                continue
            match = FILENAME_PATTERN.fullmatch(source_file.name)
            if match is None:
                parse_failures.append(str(source_file))
                continue
            owner = match.group("owner")
            repo = match.group("repo")
            issue_number = int(match.group("num"))
            rows.append(
                {
                    "source_file": str(source_file.relative_to(PROJECT_ROOT)),
                    "owner": owner,
                    "repo": repo,
                    "issue_number": issue_number,
                    "root_cause": root_cause,
                    "url": (
                        f"https://github.com/{owner}/{repo}/issues/"
                        f"{issue_number}"
                    ),
                }
            )

    labels = pd.DataFrame(rows)
    if parse_failures:
        raise ValueError(f"Unparseable label files: {parse_failures}")
    if len(labels) != sum(EXPECTED_COUNTS.values()):
        raise ValueError(f"Expected 369 labels, found {len(labels)}")
    actual_counts = labels["root_cause"].value_counts().to_dict()
    if actual_counts != EXPECTED_COUNTS:
        raise ValueError(
            f"Expected class counts {EXPECTED_COUNTS}, found {actual_counts}"
        )

    output_path = output_path or PROJECT_ROOT / "data" / "interim" / "labels.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(output_path, index=False)
    return labels


if __name__ == "__main__":
    labels = build_labels()
    labels["project"] = labels["owner"] + "/" + labels["repo"]
    print("Counts per class:")
    print(labels["root_cause"].value_counts().sort_index().to_string())
    print(f"Distinct projects: {labels['project'].nunique()}")
    print("Top 5 projects:")
    print(labels["project"].value_counts().head(5).to_string())
    for root_cause in EXPECTED_COUNTS:
        sample = labels.loc[labels["root_cause"] == root_cause].iloc[0]
        sample_path = PROJECT_ROOT / sample["source_file"]
        print(f"\n[{root_cause}] {sample_path}")
        print(sample_path.read_text(encoding="utf-8"))
