"""Join the 369 labels to issue JSON and derive fix dates."""

import json
from pathlib import Path

import pandas as pd


RAW = Path("data/raw")
LABELS = Path("data/interim/labels.csv")
OUT = Path("data/interim/gold_joined.csv")


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def index_project_files():
    index = {}
    for path in RAW.rglob("issuesDataWStats.json"):
        index[path.parent.name.lower()] = path
    return index


def earliest(dates):
    present = [date for date in dates if date]
    return min(present) if present else None


def load_issues(path):
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    rows = []
    for issue in data.get("issues", []):
        commit_details = issue.get("commitsDetails", []) or []
        rows.append(
            {
                "url": issue["url"],
                "project": data["projectName"],
                "title": issue.get("title") or "",
                "description": issue.get("body") or "",
                "user": issue.get("user"),
                "created": issue.get("created"),
                "closed": issue.get("closed"),
                "has_commits": bool(issue.get("commits")),
                "fix_authored": earliest(
                    commit.get("authoredDateTime") for commit in commit_details
                ),
                "fix_committed": earliest(
                    commit.get("commitDateTime") for commit in commit_details
                ),
            }
        )
    return pd.DataFrame(rows)


def main():
    labels = pd.read_csv(LABELS)
    labels["_k"] = labels["url"].map(norm_url)
    needed_projects = (
        labels["owner"].astype(str)
        + "_"
        + labels["repo"].astype(str)
    ).str.lower().unique()
    project_index = index_project_files()
    missing_projects = [
        project for project in needed_projects if project not in project_index
    ]
    if missing_projects:
        print(
            f"WARNING: {len(missing_projects)} gold project folders not found: "
            f"{missing_projects[:10]}"
        )

    frames = [
        load_issues(project_index[project])
        for project in needed_projects
        if project in project_index
    ]
    all_issues = pd.concat(frames, ignore_index=True)
    all_issues["_k"] = all_issues["url"].map(norm_url)
    all_issues = all_issues.drop_duplicates("_k")

    joined = labels.merge(
        all_issues.drop(columns=["url"]),
        on="_k",
        how="left",
        suffixes=("", "_iss"),
    )
    matched = joined["title"].notna().sum()
    print(
        f"labels: {len(labels)}  matched to issue json: {matched}  "
        f"unmatched: {len(labels) - matched}"
    )
    for _, row in joined[joined["title"].isna()].iterrows():
        folder = f"{row['owner']}_{row['repo']}".lower()
        reason = (
            "project folder missing"
            if folder not in project_index
            else "issue number not in project json"
        )
        print(f"  UNMATCHED {row['url']} -> {reason}")

    joined["fix_date"] = joined["fix_authored"].fillna(joined["closed"])
    joined["fix_date_source"] = joined["fix_authored"].notna().map(
        {True: "commit", False: "closed"}
    )
    created = pd.to_datetime(joined["created"], errors="coerce", utc=True)
    authored = pd.to_datetime(
        joined["fix_authored"], errors="coerce", utc=True
    )
    pre_file = (authored < created).sum()
    print(
        f"fix_date from commit: {(joined['fix_date_source'] == 'commit').sum()}  "
        f"from closed: {(joined['fix_date_source'] == 'closed').sum()}  "
        f"fix authored before issue created: {pre_file}"
    )
    project_counts = joined["project"].value_counts()
    print(
        f"projects: {project_counts.notna().sum()}  largest: "
        f"{project_counts.index[0]}={project_counts.iloc[0]} "
        f"({100 * project_counts.iloc[0] / len(joined):.0f}%)"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joined.drop(columns=["_k"]).to_csv(OUT, index=False)
    print(f"wrote {OUT} rows={len(joined)}")


if __name__ == "__main__":
    main()
