"""Nested grouped-CV hybrid with schema-checked original structural fields."""

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
from src.stats import mcnemar_test, paired_bootstrap


SEED = 42
LABELS = ["concurrency", "memory", "semantic"]
RESULTS_DIR = Path("results/rq3/tables")
EXPERIMENT_ID = "rq3_hybrid_structural_corrected_v1"


def assemble(data, regex, masked):
    required = ["title", "description_clean", "comments_model", "has_stack",
                "has_code", "n_comments_prefix"]
    missing = [column for column in required if column not in data]
    if missing:
        raise ValueError(f"Missing required corrected-hybrid columns: {missing}")

    for column in ["has_stack", "has_code"]:
        values = data[column]
        if values.isna().any():
            raise ValueError(f"Required structural feature has missing values: {column}")
        if not set(values.dropna().unique()).issubset({False, True, 0, 1}):
            raise ValueError(f"Required structural feature has invalid values: {column}")

    base = (
        data["title"].fillna("")
        + " "
        + data["description_clean"].fillna("")
        + " "
        + data["comments_model"].fillna("")
    )
    text = base.apply(lambda value: mask(value, regex)) if masked else base
    output = pd.DataFrame({"text": text.values})
    output["has_stack"] = data["has_stack"].astype(float).values
    output["has_code"] = data["has_code"].astype(float).values
    output["loglen"] = np.log1p(data["description_clean"].fillna("").str.len().values)
    output["n_comments"] = np.log1p(data["n_comments_prefix"].fillna(0).values)
    numeric = ["has_stack", "has_code", "loglen", "n_comments"]

    if not masked:
        conc = r"(race|deadlock|synchroniz|concurren|lock|atomic|thread|volatile)"
        mem = r"(leak|null|npe|memory|heap|buffer|oom|gc|allocate|dereference)"
        exc = r"\b([A-Z][A-Za-z]+(?:Exception|Error))\b"
        import re
        output["kw_conc"] = base.apply(
            lambda value: int(bool(re.search(conc, value, re.I)))
        ).values
        output["kw_mem"] = base.apply(
            lambda value: int(bool(re.search(mem, value, re.I)))
        ).values
        output["has_exc"] = base.apply(
            lambda value: int(bool(re.search(exc, value)))
        ).values
        numeric += ["kw_conc", "kw_mem", "has_exc"]
    return output, numeric


def make_pipe(numeric_columns):
    transformer = ColumnTransformer([
        ("word", TfidfVectorizer(
            ngram_range=(1, 2), min_df=3, sublinear_tf=True,
            stop_words="english",
        ), "text"),
        ("char", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=3,
            sublinear_tf=True,
        ), "text"),
        ("num", StandardScaler(with_mean=False), numeric_columns),
    ])
    return Pipeline([
        ("feats", transformer),
        ("clf", LinearSVC(random_state=SEED)),
    ])


def metrics(labels, predictions):
    return {
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "per_class": dict(zip(
            LABELS,
            f1_score(labels, predictions, average=None, labels=LABELS).round(6),
        )),
        "confusion": confusion_matrix(labels, predictions, labels=LABELS).tolist(),
    }


def run(data, regex, masked, setting):
    features, numeric = assemble(data, regex, masked)
    labels = data["root_cause"].values
    groups = data["project"].values
    predictions = np.empty(len(labels), dtype=object)
    fold_ids = np.empty(len(labels), dtype=int)
    outer = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)

    for fold_id, (train, test) in enumerate(outer.split(features, labels, groups)):
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
        fold_ids[test] = fold_id

    output = pd.DataFrame({
        "url": data["url"].values,
        "project": data["project"].values,
        "fold_id": fold_ids,
        "y_true": labels,
        "prediction": predictions,
        "setting": setting,
        "experiment_id": EXPERIMENT_ID,
    })
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"rq3_oof_hybrid_structural_corrected_{setting}.csv"
    output.to_csv(path, index=False)
    print(f"[{setting}] wrote {path} rows={len(output)}")
    print(metrics(labels, predictions))
    return output


def compare(data, normal, masked):
    legacy_files = {
        "normal": RESULTS_DIR / "rq3_oof_hybrid_normal.csv",
        "masked": RESULTS_DIR / "rq3_oof_hybrid_masked.csv",
    }
    rows = []
    for setting, legacy_path in legacy_files.items():
        legacy = pd.read_csv(legacy_path)
        if not np.array_equal(legacy["y"].values, data["root_cause"].values):
            raise ValueError(f"Legacy row-order labels do not match gold: {setting}")
        corrected = normal if setting == "normal" else masked
        labels = data["root_cause"].values
        old_pred = legacy["hybrid"].values
        new_pred = corrected["prediction"].values
        old_metrics = metrics(labels, old_pred)
        new_metrics = metrics(labels, new_pred)
        result = mcnemar_test(old_pred == labels, new_pred == labels)
        diff, low, high = paired_bootstrap(old_pred == labels, new_pred == labels)
        rows.append({
            "setting": setting,
            "legacy_macro_f1": old_metrics["macro_f1"],
            "corrected_macro_f1": new_metrics["macro_f1"],
            "macro_f1_delta": new_metrics["macro_f1"] - old_metrics["macro_f1"],
            "legacy_accuracy": float(np.mean(old_pred == labels)),
            "corrected_accuracy": float(np.mean(new_pred == labels)),
            "accuracy_delta": diff,
            "accuracy_ci_low": low,
            "accuracy_ci_high": high,
            "mcnemar_p": result.pvalue,
            "changed_predictions": int(np.sum(old_pred != new_pred)),
        })
    pd.DataFrame(rows).to_csv(
        RESULTS_DIR / "rq3_structural_feature_comparison.csv", index=False
    )


def main():
    data = pd.read_csv("data/processed/gold_v1.csv")
    if len(data) != 369 or data["url"].nunique() != 369:
        raise ValueError("Expected 369 unique gold URLs")
    if set(data["root_cause"].unique()) != set(LABELS):
        raise ValueError("Unexpected root-cause labels")
    _, regex = load_selection_keywords()
    normal = run(data, None, False, "normal")
    masked = run(data, regex, True, "masked")
    compare(data, normal, masked)


if __name__ == "__main__":
    main()
