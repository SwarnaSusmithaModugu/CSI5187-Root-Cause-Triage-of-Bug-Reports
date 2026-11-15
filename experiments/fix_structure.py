"""Extract fix-structure features and test their root-cause signal on gold."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold


RAW = Path("data/raw")


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def fix_features(issue):
    commits = issue.get("commitsDetails") or []
    insertions = deletions = lines = method_count = 0
    total = updated = inserted = moved = deleted = 0
    files = set()
    test_files = java_files = 0

    for commit in commits:
        for git_stat in commit.get("commitGitStats") or []:
            file_path = git_stat.get("filePath") or ""
            files.add(file_path)
            insertions += git_stat.get("insertions") or 0
            deletions += git_stat.get("deletions") or 0
            lines += git_stat.get("lines") or 0
            if "test" in file_path.lower():
                test_files += 1
            if file_path.endswith(".java"):
                java_files += 1
        for spoon_stat in commit.get("commitSpoonAstDiffStats") or []:
            for method in spoon_stat.get("spoonMethods") or []:
                method_count += 1
                total += method.get("TOT") or 0
                updated += method.get("UPD") or 0
                inserted += method.get("INS") or 0
                moved += method.get("MOV") or 0
                deleted += method.get("DEL") or 0

    file_count = len(files)
    features = {
        "n_commits": len(commits),
        "n_files": file_count,
        "ins": insertions,
        "del": deletions,
        "net": insertions - deletions,
        "lines": lines,
        "n_methods": method_count,
        "ast_TOT": total,
        "ast_UPD": updated,
        "ast_INS": inserted,
        "ast_MOV": moved,
        "ast_DEL": deleted,
        "test_files": test_files,
        "java_files": java_files,
        "frac_test": test_files / file_count if file_count else 0.0,
        "pkgG": len(issue.get("changesInPackagesGIT") or []),
        "pkgS": len(issue.get("changesInPackagesSPOON") or []),
    }
    denominator = total or 1
    features.update(
        {
            "r_upd": updated / denominator,
            "r_ins": inserted / denominator,
            "r_mov": moved / denominator,
            "r_del": deleted / denominator,
            "del_ins_ratio": deletions / (insertions or 1),
        }
    )
    return features


def index_issues():
    index = {}
    for path in RAW.rglob("issuesDataWStats.json"):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for issue in data.get("issues", []):
            if issue.get("commitsDetails"):
                index[norm_url(issue["url"])] = issue
    return index


def main():
    gold = pd.read_csv("data/processed/gold_369.csv")
    issue_index = index_issues()
    rows, labels, groups = [], [], []
    missing = 0
    for _, row in gold.iterrows():
        issue = issue_index.get(norm_url(row["url"]))
        if issue is None:
            missing += 1
            continue
        rows.append(fix_features(issue))
        labels.append(row["root_cause"])
        groups.append(row["project"])

    features = pd.DataFrame(rows).fillna(0.0)
    target = np.array(labels)
    group_values = np.array(groups)
    print(f"gold with fix stats: {len(features)}  missing: {missing}")
    print("feature means by class:")
    print(
        features.assign(cls=target)
        .groupby("cls")
        .mean()
        .round(2)
        .T.to_string()
    )

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    predictions = np.empty(len(target), dtype=object)
    baseline = np.empty(len(target), dtype=object)
    for train, test in cv.split(features, target, group_values):
        classifier = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
        )
        classifier.fit(features.iloc[train], target[train])
        predictions[test] = classifier.predict(features.iloc[test])

        dummy = DummyClassifier(strategy="stratified", random_state=42)
        dummy.fit(features.iloc[train], target[train])
        baseline[test] = dummy.predict(features.iloc[test])

    print(f"\nfix-structure macro-F1: {f1_score(target, predictions, average='macro'):.3f}")
    print(f"random baseline macro-F1: {f1_score(target, baseline, average='macro'):.3f}")
    class_labels = ["concurrency", "memory", "semantic"]
    print(
        "per-class F1:",
        dict(
            zip(
                class_labels,
                f1_score(
                    target,
                    predictions,
                    average=None,
                    labels=class_labels,
                ).round(3),
            )
        ),
    )
    print("confusion (concurrency, memory, semantic):")
    print(confusion_matrix(target, predictions, labels=class_labels))

    classifier = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
    ).fit(features, target)
    importance = pd.Series(
        classifier.feature_importances_,
        index=features.columns,
    ).sort_values(ascending=False)
    print("\ntop features by importance (descriptive only):")
    print(importance.head(8).round(3).to_string())


if __name__ == "__main__":
    main()
