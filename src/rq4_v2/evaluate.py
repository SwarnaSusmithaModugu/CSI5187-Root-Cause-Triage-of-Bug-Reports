"""Evaluate saved RQ4 v2 baseline predictions and bootstrap uncertainty."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score


OUTPUT = Path("results/rq4/v2")
LABELS = ["concurrency", "memory", "semantic"]
SEED = 42


def macro_and_accuracy(part):
    y_true = part["y_true"].values
    y_pred = part["prediction"].values
    return (
        f1_score(y_true, y_pred, average="macro", labels=LABELS),
        float(np.mean(y_true == y_pred)),
        confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
    )


def project_bootstrap(paired, first, second, resamples=5000):
    rng = np.random.default_rng(SEED)
    first_part = paired[paired["condition"] == first].set_index("url")
    second_part = paired[paired["condition"] == second].set_index("url")
    merged = first_part.join(
        second_part,
        how="inner",
        lsuffix="_first",
        rsuffix="_second",
    )
    projects = sorted(merged["project_first"].drop_duplicates())

    matrices_first = {}
    matrices_second = {}
    for project in projects:
        part = merged[merged["project_first"] == project]
        matrices_first[project] = confusion_matrix(
            part["y_true_first"], part["prediction_first"], labels=LABELS
        )
        matrices_second[project] = confusion_matrix(
            part["y_true_second"], part["prediction_second"], labels=LABELS
        )

    def from_matrices(matrices, counts):
        confusions = [matrices[project] for project in projects]
        total = sum((counts[index] * confusions[index] for index in range(len(projects))), np.zeros((3, 3), dtype=int))
        return macro_from_confusion(total), float(np.trace(total) / total.sum())

    def macro_from_confusion(total):
        scores = []
        for index in range(len(LABELS)):
            tp = total[index, index]
            fp = total[:, index].sum() - tp
            fn = total[index, :].sum() - tp
            denominator = 2 * tp + fp + fn
            scores.append(0.0 if denominator == 0 else (2 * tp) / denominator)
        return float(np.mean(scores))

    deltas_f1 = []
    deltas_acc = []
    for _ in range(resamples):
        counts_array = rng.choice(
            len(projects), size=len(projects), replace=True
        )
        counts = np.bincount(counts_array, minlength=len(projects))
        f1_first, acc_first = from_matrices(matrices_first, counts)
        f1_second, acc_second = from_matrices(matrices_second, counts)
        deltas_f1.append(f1_second - f1_first)
        deltas_acc.append(acc_second - acc_first)
    return (
        float(np.quantile(deltas_f1, 0.025)),
        float(np.quantile(deltas_f1, 0.975)),
        float(np.quantile(deltas_acc, 0.025)),
        float(np.quantile(deltas_acc, 0.975)),
    )


def main():
    predictions = pd.read_csv(OUTPUT / "reveal_predictions.csv")
    metrics = []
    for condition in sorted(predictions["condition"].unique()):
        part = predictions[predictions["condition"] == condition]
        macro_f1, accuracy, confusion = macro_and_accuracy(part)
        metrics.append({
            "condition": condition,
            "n": len(part),
            "projects": part["project"].nunique(),
            "macro_f1": macro_f1,
            "accuracy": accuracy,
            "confusion_matrix": json.dumps(confusion),
        })
    pd.DataFrame(metrics).to_csv(OUTPUT / "metrics.csv", index=False)

    b0 = predictions[predictions["condition"] == "B0_no_reveal"]
    b3 = predictions[predictions["condition"] == "B3_same_type_control"]
    paired = pd.concat([
        b0.assign(condition="B0_no_reveal"),
        b3.assign(condition="B3_same_type_control"),
    ])
    ci = project_bootstrap(paired, "B0_no_reveal", "B3_same_type_control")
    pd.DataFrame([{
        "comparison": "B3_same_type_control_minus_B0",
        "macro_f1_ci_low": ci[0],
        "macro_f1_ci_high": ci[1],
        "accuracy_ci_low": ci[2],
        "accuracy_ci_high": ci[3],
        "resamples": 5000,
        "method": "paired project-cluster bootstrap",
    }]).to_csv(OUTPUT / "bootstrap_ci.csv", index=False)

    b0 = predictions[predictions["condition"] == "B0_no_reveal"][
        ["url", "project", "fold_id", "y_true", "prediction"]
    ].rename(columns={"prediction": "prediction_b0"})
    b3 = predictions[predictions["condition"] == "B3_same_type_control"][
        ["url", "prediction"]
    ].rename(columns={"prediction": "prediction_b3"})
    paired_changes = b0.merge(b3, on="url", how="inner")
    paired_changes["b0_correct"] = (
        paired_changes["prediction_b0"] == paired_changes["y_true"]
    )
    paired_changes["b3_correct"] = (
        paired_changes["prediction_b3"] == paired_changes["y_true"]
    )
    paired_changes["change"] = np.select(
        [
            paired_changes["b3_correct"] & ~paired_changes["b0_correct"],
            ~paired_changes["b3_correct"] & paired_changes["b0_correct"],
        ],
        ["beneficial", "harmful"],
        default="unchanged",
    )
    paired_changes.to_csv(OUTPUT / "paired_differences.csv", index=False)

    subgroup_rows = []
    for condition in sorted(predictions["condition"].unique()):
        part = predictions[predictions["condition"] == condition]
        for class_name in LABELS:
            subgroup = part[part["y_true"] == class_name]
            if len(subgroup):
                macro_f1, accuracy, _ = macro_and_accuracy(subgroup)
                subgroup_rows.append({
                    "condition": condition,
                    "subgroup": "root_cause",
                    "value": class_name,
                    "n": len(subgroup),
                    "projects": subgroup["project"].nunique(),
                    "macro_f1": macro_f1,
                    "accuracy": accuracy,
                })
    pd.DataFrame(subgroup_rows).to_csv(
        OUTPUT / "subgroup_metrics.csv", index=False
    )


if __name__ == "__main__":
    main()
