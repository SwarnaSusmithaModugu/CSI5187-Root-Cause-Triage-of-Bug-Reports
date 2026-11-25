"""Phase 2 RQ4 v2 baselines."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.rq4_reveal import remove_units, restore, units
from src.rq4_v2.audit import SEED


OUTPUT = Path("results/rq4/v2")
LABELS = ["concurrency", "memory", "semantic"]


def robust_units(row):
    return {
        key: value
        for key, value in units(row).items()
        if key != "comments_model"
    }


def robust_remove(row):
    text = (
        str(row["title"] if pd.notna(row["title"]) else "")
        + "\n"
        + str(row["description"] if pd.notna(row["description"]) else "")
        + "\n"
    )
    for value in robust_units(row).values():
        text = text.replace(value, " ")
    return " ".join(text.split())


def unit_type(unit_id):
    return "description" if unit_id.startswith("description") else unit_id


def fit_model(train_text, train_labels):
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", LinearSVC(random_state=SEED)),
    ])
    model.fit(train_text, train_labels)
    return model


def main():
    data = pd.read_csv("data/processed/gold_v1.csv")
    eligible = data[data.apply(
        lambda row: len(robust_units(row)) >= 2, axis=1
    )].reset_index(drop=True)

    records = []
    match_rows = []
    folds = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
    for fold_id, (train, test) in enumerate(
        folds.split(eligible, eligible["root_cause"], eligible["project"])
    ):
        withheld_train = [robust_remove(row) for _, row in eligible.iloc[train].iterrows()]
        model = fit_model(withheld_train, eligible.iloc[train]["root_cause"].values)
        train_type_counts = {}
        for index in train:
            for unit_id in robust_units(eligible.iloc[index]).keys():
                kind = unit_type(unit_id)
                train_type_counts[kind] = train_type_counts.get(kind, 0) + 1
        preferred_type = max(
            sorted(train_type_counts),
            key=lambda kind: (train_type_counts[kind], kind),
        )

        for test_index in test:
            row = eligible.iloc[test_index]
            available = robust_units(row)
            withheld = robust_remove(row)
            ids = list(available)

            rng = np.random.default_rng(SEED + fold_id)
            random_id = rng.choice(ids)
            length_id = min(ids, key=lambda key: len(available[key]))
            length_target_id = length_id

            type_group = unit_type(length_target_id)
            same_type_ids = [
                key for key in ids
                if key != length_target_id and unit_type(key) == type_group
            ]
            b3_id = min(
                same_type_ids,
                key=lambda key: abs(
                    len(available[key]) - len(available[length_target_id])
                ),
            ) if same_type_ids else None

            b4_ids = [
                key for key in ids
                if unit_type(key) == preferred_type
            ]
            b4_id = min(
                b4_ids,
                key=lambda key: abs(len(available[key]) - len(available[length_target_id]))
            ) if b4_ids else length_target_id

            b1_seeds = {}
            for seed in range(10):
                seed_rng = np.random.default_rng(1000 + seed)
                b1_seeds[str(seed)] = seed_rng.choice(ids)

            conditions = {
                "B0_no_reveal": withheld,
                "B2_length_control": restore(withheld, available[length_id]),
                "B3_same_type_control": (
                    restore(withheld, available[b3_id])
                    if b3_id is not None else withheld
                ),
                "B4_type_preference": restore(withheld, available[b4_id]),
                "B5_v1_target_reference": restore(withheld, available[length_id]),
                "REF_all_units": restore(withheld, " ".join(available.values())),
            }
            for seed, unit_id in b1_seeds.items():
                conditions[f"B1_seed_{seed}"] = restore(
                    withheld, available[unit_id]
                )

            for condition, text in conditions.items():
                records.append({
                    "url": row["url"],
                    "project": row["project"],
                    "fold_id": fold_id,
                    "model_id": f"linear_svc_{fold_id}",
                    "y_true": row["root_cause"],
                    "prediction": model.predict([text])[0],
                    "condition": condition,
                    "experiment_id": "rq4_v2_baselines",
                })

            match_rows.append({
                "url": row["url"],
                "project": row["project"],
                "fold_id": fold_id,
                "n_units": len(ids),
                "b2_unit_id": length_id,
                "b2_char_len": len(available[length_id]),
                "b3_unit_id": b3_id,
                "b3_matchable": b3_id is not None,
                "b3_char_len": len(available[b3_id]) if b3_id else None,
                "b3_length_delta": (
                    len(available[b3_id]) - len(available[length_target_id])
                    if b3_id else None
                ),
            })

    predictions = pd.DataFrame(records)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT / "reveal_predictions.csv", index=False)
    pd.DataFrame(match_rows).to_csv(
        OUTPUT / "control_match_audit.csv", index=False
    )


if __name__ == "__main__":
    main()
