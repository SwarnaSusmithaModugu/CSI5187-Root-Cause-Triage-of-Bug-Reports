"""Nested grouped-CV hybrid text, keyword, and structure model."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from src.masking import load_selection_keywords, mask
from src.stats import mcnemar_test


SEED = 42
LABELS = ["concurrency", "memory", "semantic"]
RESULTS_DIR = Path("results/rq3/tables")
CONC_KW = re.compile(
    r"(race|deadlock|synchroniz|concurren|lock|atomic|thread|volatile)",
    re.I,
)
MEM_KW = re.compile(
    r"(leak|null|npe|memory|heap|buffer|oom|gc|allocate|dereference)",
    re.I,
)
EXC = re.compile(r"\b([A-Z][A-Za-z]+(Exception|Error))\b")


def assemble(data, regex, masked):
    """Build text and numeric features, removing shortcut features when masked."""
    base = (
        data["title"].fillna("")
        + " "
        + data["description_clean"].fillna("")
        + " "
        + data["comments_model"].fillna("")
    )
    text = base.apply(lambda value: mask(value, regex)) if masked else base
    output = pd.DataFrame({"text": text.values})
    output["has_stack"] = data["description_has_stack"].astype(float).values
    output["has_code"] = data["description_has_code"].astype(float).values
    output["loglen"] = np.log1p(
        data["description_clean"].fillna("").str.len().values
    )
    output["n_comments"] = np.log1p(
        data["n_comments_prefix"].fillna(0).values
    )
    numeric = ["has_stack", "has_code", "loglen", "n_comments"]
    if not masked:
        output["kw_conc"] = base.apply(
            lambda value: int(bool(CONC_KW.search(value)))
        ).values
        output["kw_mem"] = base.apply(
            lambda value: int(bool(MEM_KW.search(value)))
        ).values
        output["has_exc"] = base.apply(
            lambda value: int(bool(EXC.search(value)))
        ).values
        numeric += ["kw_conc", "kw_mem", "has_exc"]
    return output, numeric


def make_pipe(numeric_columns):
    transformer = ColumnTransformer(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=3,
                    sublinear_tf=True,
                    stop_words="english",
                ),
                "text",
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=3,
                    sublinear_tf=True,
                ),
                "text",
            ),
            ("num", StandardScaler(with_mean=False), numeric_columns),
        ]
    )
    return Pipeline(
        [
            ("feats", transformer),
            ("clf", LinearSVC(random_state=SEED)),
        ]
    )


def run(data, regex, masked, tag):
    features, numeric = assemble(data, regex, masked)
    labels, groups = data["root_cause"].values, data["project"].values
    outer = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
    predictions = np.empty(len(labels), dtype=object)
    for train, test in outer.split(features, labels, groups):
        inner = StratifiedGroupKFold(4, shuffle=True, random_state=SEED)
        search = GridSearchCV(
            make_pipe(numeric),
            {"clf__C": [0.25, 0.5, 1, 2]},
            cv=inner,
            scoring="f1_macro",
            n_jobs=-1,
        )
        search.fit(features.iloc[train], labels[train], groups=groups[train])
        predictions[test] = search.predict(features.iloc[test])
    macro = f1_score(labels, predictions, average="macro")
    per_class = dict(
        zip(
            LABELS,
            f1_score(
                labels, predictions, average=None, labels=LABELS
            ).round(3),
        )
    )
    print(f"[{tag}] hybrid macro-F1={macro:.3f} per-class={per_class}")
    print(confusion_matrix(labels, predictions, labels=LABELS))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"hybrid": predictions, "y": labels}).to_csv(
        RESULTS_DIR / f"rq3_oof_hybrid_{tag}.csv", index=False
    )
    return predictions


def main():
    data = pd.read_csv("data/processed/gold_v1.csv")
    for column in [
        "description_clean",
        "comments_model",
        "description_has_stack",
        "description_has_code",
    ]:
        if column not in data:
            data[column] = 0 if "has_" in column else ""
    if "n_comments_prefix" not in data:
        data["n_comments_prefix"] = 0
    _, regex = load_selection_keywords()
    normal = run(data, None, False, "normal")
    run(data, regex, True, "masked")

    plain = pd.read_csv(RESULTS_DIR / "rq3_oof_normal.csv")
    result = mcnemar_test(
        normal == plain["y"].values,
        plain["svm"].values == plain["y"].values,
    )
    print(
        f"[normal] hybrid vs plain SVM McNemar exact p={result.pvalue:.4f}"
    )
    print(
        "reference: artifact keyword baseline 0.773 (not a target), "
        "plain SVM 0.689"
    )


if __name__ == "__main__":
    main()
