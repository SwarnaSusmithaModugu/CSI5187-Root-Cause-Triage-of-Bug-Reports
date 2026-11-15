"""RQ1 field importance with normal and keyword-masked inputs."""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.masking import load_selection_keywords, mask


SEED = 42
FIELDS = ["title", "description_clean", "comments_model"]
FILL = "zzfill"


def build(data, keep, mode, regex=None):
    parts = []
    for field in FIELDS:
        column = data[field].fillna("")
        if field in keep:
            parts.append(
                column.apply(lambda value: mask(value, regex))
                if regex is not None
                else column
            )
        elif mode == "length":
            parts.append(
                column.apply(lambda value: " ".join(
                    [FILL] * len(str(value).split())
                ))
            )
    if not parts:
        return [""] * len(data)
    output = parts[0]
    for part in parts[1:]:
        output = output + " " + part
    return output.tolist()


def oof(texts, labels, groups, n=5):
    texts = np.array(texts, dtype=object)
    predictions = np.empty(len(labels), dtype=object)
    for train, test in StratifiedGroupKFold(
        n, shuffle=True, random_state=SEED
    ).split(texts, labels, groups):
        pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2), min_df=2, sublinear_tf=True
                    ),
                ),
                ("clf", LinearSVC(random_state=SEED)),
            ]
        )
        pipeline.fit(texts[train].tolist(), labels[train])
        predictions[test] = pipeline.predict(texts[test].tolist())
    return predictions


def main():
    data = pd.read_csv("data/processed/gold_v1.csv")
    for field in FIELDS:
        if field not in data:
            data[field] = ""
    labels, groups = data["root_cause"].values, data["project"].values
    _, regex = load_selection_keywords()

    rows = []
    full = oof(build(data, FIELDS, "hard"), labels, groups)
    rows.append(("full", "-", f1_score(labels, full, average="macro")))
    for mode in ("hard", "length"):
        for field in FIELDS:
            for kind, keep in (
                ("loo", [value for value in FIELDS if value != field]),
                ("loi", [field]),
            ):
                prediction = oof(build(data, keep, mode), labels, groups)
                rows.append(
                    (
                        f"{kind}_{field}",
                        mode,
                        f1_score(labels, prediction, average="macro"),
                    )
                )
    masked_full = oof(build(data, FIELDS, "hard", regex=regex), labels, groups)
    rows.append(
        ("full_keyword_masked", "mask", f1_score(
            labels, masked_full, average="macro"
        ))
    )
    output = pd.DataFrame(rows, columns=["setting", "mode", "macro_f1"])
    output.to_csv("results/rq1_final.csv", index=False)
    print(output.round(3).to_string(index=False))

    text = build(data, FIELDS, "hard")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), min_df=3, stop_words="english"
    )
    features = vectorizer.fit_transform(text)
    information_gain = mutual_info_classif(
        features, labels, random_state=SEED
    )
    terms = np.array(vectorizer.get_feature_names_out())
    top = pd.DataFrame(
        {
            "term": terms[np.argsort(information_gain)[::-1][:25]],
            "info_gain": np.sort(information_gain)[::-1][:25],
        }
    )
    top.to_csv("results/rq1_infogain_terms.csv", index=False)
    print("\ntop InfoGain terms:", list(top["term"].head(12)))
    print(
        "note: if the top InfoGain terms are the selection keywords, "
        "that is the shortcut showing again"
    )


if __name__ == "__main__":
    main()
