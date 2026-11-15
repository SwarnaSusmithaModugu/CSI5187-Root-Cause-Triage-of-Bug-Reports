"""Measure class separation from the keyword-selection features alone."""

import re
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold


CONSTANTS = Path("data/raw/keywordSearch/constants.py")


def load_keywords():
    values = runpy.run_path(str(CONSTANTS))
    return (
        values["KEYWORDS_CONCURRENCY_RE"],
        values["KEYWORDS_MEMORY_RE"],
    )


def has_any(text, keywords):
    return int(any(re.search(keyword, text, flags=re.IGNORECASE) for keyword in keywords))


def main():
    gold = pd.read_csv("data/processed/gold_369.csv")
    concurrency, memory = load_keywords()
    text = (
        gold["title"].fillna("").astype(str)
        + " "
        + gold["description"].fillna("").astype(str)
    ).str.lower()
    features = np.array(
        [[has_any(value, concurrency), has_any(value, memory)] for value in text]
    )
    target = gold["root_cause"].to_numpy()
    groups = gold["project"].to_numpy()
    print("fraction with a concurrency keyword, by class:")
    print(
        pd.Series(features[:, 0], index=target)
        .groupby(level=0)
        .mean()
        .to_dict()
    )
    print("fraction with a memory keyword, by class:")
    print(
        pd.Series(features[:, 1], index=target)
        .groupby(level=0)
        .mean()
        .to_dict()
    )

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    predictions = np.empty(len(target), dtype=object)
    for train, test in cv.split(features, target, groups):
        classifier = LogisticRegression(max_iter=1000).fit(
            features[train], target[train]
        )
        predictions[test] = classifier.predict(features[test])
    score = f1_score(target, predictions, average="macro")
    print("shortcut macro-F1:", round(score, 3))
    print("confusion matrix (concurrency, memory, semantic):")
    print(
        confusion_matrix(
            target,
            predictions,
            labels=["concurrency", "memory", "semantic"],
        )
    )


if __name__ == "__main__":
    main()
