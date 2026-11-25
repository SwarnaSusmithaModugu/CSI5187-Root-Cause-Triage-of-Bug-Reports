"""Controlled retrospective restoration of existing RQ4 eligible text units."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.rq4_feasibility import description_units


SEED = 42
LABELS = ["concurrency", "memory", "semantic"]
RESULTS_DIR = Path("results/rq4")


def units(row):
    found = {}
    for index, paragraph in enumerate(description_units(row["description"])):
        found[f"description_p{index}"] = paragraph
    for name in ["code_text", "stack_text", "comments_model"]:
        value = row.get(name, "")
        if isinstance(value, str) and 30 <= len(value.strip()) <= 2000:
            found[name] = value.strip()
    return found


def remove_units(row):
    text = (
        str(row["title"] if pd.notna(row["title"]) else "")
        + "\n"
        + str(row["description"] if pd.notna(row["description"]) else "")
        + "\n"
    )
    text = text.replace(str(row["comments_model"] if pd.notna(row["comments_model"]) else ""), "")
    for value in units(row).values():
        text = text.replace(value, " ")
    return " ".join(text.split())


def restore(text, unit_text):
    return " ".join([text, unit_text])


def targeted_unit(unit_map, train_indices, row):
    candidate_units = []
    candidate_labels = []
    for index in train_indices:
        for _unit_id, unit_text in units_map[index].items():
            candidate_units.append(unit_text)
            candidate_labels.append(eligible_labels[index])
    if not candidate_units:
        return next(iter(units(row)))
    policy = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", LinearSVC(random_state=SEED)),
    ])
    policy.fit(candidate_units, candidate_labels)
    test_units = list(units(row).items())
    scores = policy.decision_function([value for _, value in test_units])
    if scores.ndim == 1:
        score_by_unit = list(scores)
    else:
        score_by_unit = scores.max(axis=1)
    return test_units[int(np.argmax(score_by_unit))][0]


def main():
    global units_map, eligible_labels
    data = pd.read_csv("data/processed/gold_v1.csv")
    eligible = data[data.apply(lambda row: len(units(row)) >= 2, axis=1)].copy()
    eligible = eligible.reset_index(drop=True)
    units_map = [units(row) for _, row in eligible.iterrows()]
    eligible_labels = eligible["root_cause"].values

    labels = eligible["root_cause"].values
    groups = eligible["project"].values
    records = []
    folds = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)

    for fold_id, (train, test) in enumerate(
        folds.split(eligible, labels, groups)
    ):
        held_out_model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("clf", LinearSVC(random_state=SEED)),
        ])
        withheld_text = [remove_units(row) for _, row in eligible.iloc[train].iterrows()]
        held_out_model.fit(withheld_text, labels[train])

        for test_index in test:
            row = eligible.iloc[test_index]
            available = units(row)
            withheld = remove_units(row)
            target_id = targeted_unit(
                units_map, train, row
            )
            target_text = available[target_id]
            target_len = len(target_text)
            control_candidates = [key for key in available if key != target_id]
            control_id = (
                min(control_candidates, key=lambda key: abs(len(available[key]) - target_len))
                if control_candidates else target_id
            )

            conditions = {
                "withheld": withheld,
                "control": restore(withheld, available[control_id]),
                "targeted": restore(withheld, target_text),
            }
            for condition, text in conditions.items():
                records.append({
                    "url": row["url"],
                    "project": row["project"],
                    "fold_id": fold_id,
                    "y_true": row["root_cause"],
                    "prediction": held_out_model.predict([text])[0],
                    "condition": condition,
                    "target_unit_id": target_id,
                    "control_unit_id": control_id,
                    "experiment_id": "rq4_reveal_v1",
                })

    predictions = pd.DataFrame(records)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(RESULTS_DIR / "rq4_reveal_predictions.csv", index=False)

    metrics = []
    for condition in ["withheld", "control", "targeted"]:
        part = predictions[predictions["condition"] == condition]
        y_true = part["y_true"].values
        y_pred = part["prediction"].values
        metrics.append({
            "condition": condition,
            "n": len(part),
            "projects": part["project"].nunique(),
            "macro_f1": f1_score(y_true, y_pred, average="macro", labels=LABELS),
            "accuracy": float(np.mean(y_true == y_pred)),
            "confusion_matrix": confusion_matrix(
                y_true, y_pred, labels=LABELS
            ).tolist(),
        })
    pd.DataFrame(metrics).to_csv(RESULTS_DIR / "rq4_results.csv", index=False)
    print(pd.DataFrame(metrics).drop(columns=["confusion_matrix"]))


if __name__ == "__main__":
    main()
