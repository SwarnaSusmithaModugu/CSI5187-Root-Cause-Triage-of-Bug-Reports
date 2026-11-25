"""Inspect fix-side fields on benchmark-complete issue records."""

import json
from collections import Counter
from pathlib import Path


RAW = Path("data/raw")


def iter_issues():
    for path in RAW.rglob("issuesDataWStats.json"):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        project = data.get("projectName")
        for issue in data.get("issues", []):
            yield project, issue


def main():
    total = 0
    with_commits = 0
    issue_keys = Counter()
    commit_keys = Counter()
    commits_with_message = 0
    sample_messages = []

    for _, issue in iter_issues():
        total += 1
        commit_details = issue.get("commitsDetails") or []
        if not commit_details:
            continue
        with_commits += 1
        for key in issue:
            issue_keys[key] += 1
        for commit in commit_details:
            for key in commit:
                commit_keys[key] += 1
            if commit.get("commitMessage"):
                commits_with_message += 1
                if len(sample_messages) < 5:
                    sample_messages.append(commit["commitMessage"][:200])

    print(f"total issues: {total}")
    print(f"benchmark-complete (has commitsDetails): {with_commits}")
    print(f"issue-level keys on complete issues: {dict(issue_keys.most_common())}")
    print(f"commit-detail keys: {dict(commit_keys.most_common())}")
    print(f"commits with a commitMessage: {commits_with_message}")
    print("sample commit messages:")
    for message in sample_messages:
        print("   ", message.replace("\n", " "))


if __name__ == "__main__":
    main()
