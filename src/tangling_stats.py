"""Measure simple commit-tangling indicators in the complete issue pool."""

import json
import re
from pathlib import Path

import pandas as pd


RAW = Path("data/raw")
ISSUE = re.compile(r"#\d+")
MERGE = re.compile(r"\bmerge (pull request|branch|remote|from)\b", re.I)


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def commit_msg(issue):
    return " ".join(
        (commit.get("commitMessage") or "")
        for commit in (issue.get("commitsDetails") or [])
    )


def changed_files(issue):
    files = set()
    for commit in issue.get("commitsDetails") or []:
        for stat in commit.get("commitGitStats") or []:
            if stat.get("filePath"):
                files.add(stat["filePath"])
    return files


def classify(issue):
    message = commit_msg(issue)
    issue_count = len(set(ISSUE.findall(message)))
    file_count = len(changed_files(issue))
    tangled = (
        bool(MERGE.search(message))
        or issue_count > 2
        or file_count > 20
    )
    return tangled, issue_count, file_count


def gold_tangling(gold_path="data/interim/gold_joined.csv"):
    """Classify exactly the URL/project records retained by the gold join."""
    gold = pd.read_csv(gold_path)
    gold_keys = {
        (norm_url(url), project)
        for url, project in zip(gold["url"], gold["project"])
    }
    candidates = {}
    for path in sorted(RAW.rglob("issuesDataWStats.json")):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for issue in data.get("issues", []):
            if not issue.get("commitsDetails"):
                continue
            url = norm_url(issue["url"])
            key = (url, data["projectName"])
            if key in gold_keys:
                candidates.setdefault(url, []).append(
                    (data["projectName"], issue)
                )

    duplicate_urls = sorted(
        url for url, records in candidates.items() if len(records) > 1
    )
    for url in duplicate_urls:
        records = candidates[url]
        signatures = {
            json.dumps(issue.get("commitsDetails"), sort_keys=True)
            for _, issue in records
        }
        projects = [project for project, _ in records]
        print(
            f"duplicate gold URL: {url} records={len(records)} "
            f"projects={projects} commit_data_differ={len(signatures) > 1}"
        )

    gold_rows = []
    for url in sorted(candidates):
        _, issue = candidates[url][0]
        gold_rows.append(classify(issue))
    print(
        f"gold matched: {len(gold_rows)} (expect 369)  "
        f"duplicate urls skipped: {len(duplicate_urls)}"
    )
    assert len(gold_rows) == 369, "gold tangling match is not 369"
    return gold_rows, duplicate_urls


def main():
    rows = []
    for path in RAW.rglob("issuesDataWStats.json"):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for issue in data.get("issues", []):
            if issue.get("commitsDetails"):
                tangled, issue_count, file_count = classify(issue)
                rows.append(
                    {
                        "url": issue.get("url"),
                        "project": data["projectName"],
                        "tangled": tangled,
                        "n_issues": issue_count,
                        "n_files": file_count,
                    }
                )
    frame = pd.DataFrame(rows)
    print(
        f"benchmark-complete: {len(frame)}  "
        f"tangled: {frame['tangled'].mean():.3f}"
    )
    print("tangling rate by project (top 10):")
    print(
        frame.groupby("project")["tangled"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .round(3)
        .to_string()
    )
    gold_rows, _ = gold_tangling()
    print(f"gold tangled: {sum(row[0] for row in gold_rows) / len(gold_rows):.3f}")
    frame.to_csv("results/tangling_stats.csv", index=False)


if __name__ == "__main__":
    main()
