"""RQ3 classical methods with normal and keyword-masked inputs."""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier

from src.masking import load_selection_keywords, mask
from src.stats import holm, mcnemar_test, paired_bootstrap


SEED = 42
LABELS = ["concurrency", "memory", "semantic"]


def text(data, regex=None):
    value = (
        data["title"].fillna("")
        + " "
        + data["description_clean"].fillna("")
        + " "
        + data["comments_model"].fillna("")
    )
    return (
        value.apply(lambda item: mask(item, regex))
        if regex is not None
        else value
    ).tolist()


def model(name):
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), min_df=2, sublinear_tf=True
    )
    classifiers = {
        "majority": DummyClassifier(strategy="most_frequent"),
        "svm": LinearSVC(random_state=SEED),
        "knn": KNeighborsClassifier(n_neighbors=5),
        "tree": DecisionTreeClassifier(random_state=SEED, max_depth=12),
    }
    return Pipeline([("tfidf", vectorizer), ("clf", classifiers[name])])


def run(data, regex, tag):
    features = np.array(text(data, regex), dtype=object)
    labels, groups = data["root_cause"].values, data["project"].values
    folds = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
    out_of_fold = {}
    for name in ["majority", "svm", "knn", "tree"]:
        predictions = np.empty(len(labels), dtype=object)
        for train, test in folds.split(features, labels, groups):
            fitted = model(name).fit(
                features[train].tolist(), labels[train]
            )
            predictions[test] = fitted.predict(features[test].tolist())
        out_of_fold[name] = predictions
        macro = f1_score(labels, predictions, average="macro")
        per_class = dict(
            zip(
                LABELS,
                f1_score(
                    labels, predictions, average=None, labels=LABELS
                ).round(3),
            )
        )
        print(
            f"[{tag}] {name:9s} macro-F1={macro:.3f} "
            f"per-class={per_class}"
        )

    svm_correct = out_of_fold["svm"] == labels
    names, pvalues = [], []
    for other in ["knn", "tree", "majority"]:
        result = mcnemar_test(
            svm_correct, out_of_fold[other] == labels
        )
        names.append(f"svm_vs_{other}")
        pvalues.append(result.pvalue)
        difference, low, high = paired_bootstrap(
            svm_correct, out_of_fold[other] == labels
        )
        print(
            f"[{tag}] svm vs {other}: acc delta={difference:+.3f} "
            f"CI[{low:+.3f},{high:+.3f}] "
            f"mcnemar p={result.pvalue:.4f}"
        )
    _, adjusted = holm(pvalues)
    print(f"[{tag}] Holm-adjusted p: {dict(zip(names, adjusted))}")
    pd.DataFrame({**out_of_fold, "y": labels}).to_csv(
        f"results/rq3_oof_{tag}.csv", index=False
    )
    return out_of_fold


def main():
    data = pd.read_csv("data/processed/gold_v1.csv")
    for column in ["comments_model", "description_clean"]:
        if column not in data:
            data[column] = ""
    _, regex = load_selection_keywords()
    print("=== normal ===")
    run(data, None, "normal")
    print("\n=== keyword masked ===")
    run(data, regex, "masked")
    print(
        "\nreference lines: shortcut baseline macro-F1 0.773, "
        "preliminary RQ1 0.655"
    )


if __name__ == "__main__":
    main()
