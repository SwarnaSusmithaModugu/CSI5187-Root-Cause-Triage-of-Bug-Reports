"""RQ2 annotation agreement: two independent humans and two LLMs.

Human A vs Human B measures inter-human reliability. Comparisons involving an
LLM describe model agreement, not inter-human annotation reliability.
"""

from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
)


INPUT_DIR = Path("data/interim")
OUTPUT_DIR = Path("results/rq2_annotation_comparison")
PILOT_SIZE = 50
REQUIRED = {"url", "sufficient", "inferred_category"}
CATEGORIES = ("none", "concurrency", "memory", "semantic")


def read_annotations(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing annotation file: {path}")
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"{path}: missing required columns {sorted(missing)}")

    data = data.copy()
    for column in REQUIRED:
        data[column] = data[column].str.strip()
    data["inferred_category"] = data["inferred_category"].str.lower()
    if (data["url"] == "").any():
        raise ValueError(f"{path}: blank URL(s)")
    if data["url"].duplicated().any():
        duplicates = data.loc[data["url"].duplicated(), "url"].tolist()
        raise ValueError(f"{path}: duplicate URL(s): {duplicates[:5]}")
    if not data["sufficient"].isin(["0", "1"]).all():
        raise ValueError(f"{path}: sufficient must be 0 or 1 for every row")
    if not data["inferred_category"].isin(CATEGORIES).all():
        raise ValueError(f"{path}: invalid or blank inferred_category")

    sufficient = data["sufficient"].eq("1")
    if (sufficient & data["inferred_category"].eq("none")).any():
        raise ValueError(f"{path}: sufficient=1 requires a root-cause category")
    if ((~sufficient) & data["inferred_category"].ne("none")).any():
        raise ValueError(f"{path}: sufficient=0 requires inferred_category=none")

    data["sufficient"] = data["sufficient"].astype(int)
    data = data.set_index("url")
    if not data.index.is_unique:
        raise ValueError(f"{path}: duplicate URL(s)")
    return data


def check_pilot_urls(
    pilots: dict[str, pd.DataFrame], master: pd.DataFrame
) -> pd.Index:
    reference = set(pilots["human_b"].index)
    for name, frame in pilots.items():
        urls = set(frame.index)
        if len(urls) != PILOT_SIZE:
            raise ValueError(f"{name}: expected {PILOT_SIZE} URLs, got {len(urls)}")
        if urls != reference:
            raise ValueError(
                f"{name}: URLs differ from Human B pilot; "
                f"missing={sorted(reference - urls)[:5]}, "
                f"extra={sorted(urls - reference)[:5]}"
            )

    missing_master = reference - set(master.index)
    if missing_master:
        raise ValueError(
            "Pilot URLs absent from primary human master: "
            f"{sorted(missing_master)[:5]}"
        )
    return pd.Index(sorted(reference), name="url")


def safe_kappa(first, second, labels=None) -> float:
    if len(set(first).union(set(second))) < 2:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return float(cohen_kappa_score(first, second, labels=labels))


def compare(name_a, first, name_b, second):
    first_sufficient = first["sufficient"].to_numpy()
    second_sufficient = second["sufficient"].to_numpy()
    first_category = first["inferred_category"].to_numpy()
    second_category = second["inferred_category"].to_numpy()
    agreement = float(np.mean(first_sufficient == second_sufficient))
    kappa = safe_kappa(first_sufficient, second_sufficient, labels=[0, 1])
    category_agreement = float(np.mean(first_category == second_category))
    category_kappa = safe_kappa(
        first_category, second_category, labels=list(CATEGORIES)
    )
    confusion = confusion_matrix(first_sufficient, second_sufficient, labels=[0, 1])
    class_report = classification_report(
        first_sufficient, second_sufficient, labels=[0, 1],
        target_names=["insufficient", "sufficient"],
        output_dict=True, zero_division=0,
    )

    print(f"\n=== {name_a} vs {name_b} (n={len(first)}) ===")
    print(f"Sufficiency agreement: {agreement:.3f}; "
          f"Cohen's kappa: {'undefined' if pd.isna(kappa) else f'{kappa:.3f}'}")
    print(f"Sufficient rates: {name_a}={first_sufficient.mean():.3f}, "
          f"{name_b}={second_sufficient.mean():.3f}")
    print(f"Category agreement including none: {category_agreement:.3f}; "
          f"category kappa: {'undefined' if pd.isna(category_kappa) else f'{category_kappa:.3f}'}")
    print(f"Confusion matrix (rows={name_a}, columns={name_b}; order 0,1):\n{confusion}")
    print(classification_report(
        first_sufficient, second_sufficient, labels=[0, 1],
        target_names=["insufficient", "sufficient"],
        digits=3, zero_division=0,
    ))

    metrics = {
        "comparison": f"{name_a}_vs_{name_b}",
        "n": len(first),
        "sufficient_agreement": agreement,
        "sufficient_kappa": kappa,
        "sufficient_rate_first": float(first_sufficient.mean()),
        "sufficient_rate_second": float(second_sufficient.mean()),
        "category_agreement_including_none": category_agreement,
        "category_kappa_including_none": category_kappa,
    }
    for label in ("insufficient", "sufficient"):
        metrics[f"{label}_precision"] = class_report[label]["precision"]
        metrics[f"{label}_recall"] = class_report[label]["recall"]
        metrics[f"{label}_f1"] = class_report[label]["f1-score"]

    confusion_rows = [
        {"comparison": metrics["comparison"], "reference_sufficient": row,
         "compared_sufficient": column, "count": int(confusion[row, column])}
        for row in (0, 1) for column in (0, 1)
    ]
    return metrics, confusion_rows


def main() -> None:
    master = read_annotations(INPUT_DIR / "sufficiency_labels.csv")
    pilots = {
        "human_b": read_annotations(INPUT_DIR / "pilot_A.csv"),
        "gpt6": read_annotations(INPUT_DIR / "pilot_B.csv"),
        "claude_haiku_5_5": read_annotations(INPUT_DIR / "pilot_C.csv"),
    }
    urls = check_pilot_urls(pilots, master)
    data = {"human_a": master.loc[urls]}
    data.update({name: frame.loc[urls] for name, frame in pilots.items()})

    print(f"Human A master: {len(master)} reports; pilot: {len(urls)} matched URLs")
    pairs = [
        ("human_a", "human_b"),
        ("human_a", "gpt6"),
        ("human_a", "claude_haiku_5_5"),
        ("gpt6", "claude_haiku_5_5"),
    ]
    summary, confusion_rows = [], []
    for first, second in pairs:
        metrics, rows = compare(first, data[first], second, data[second])
        summary.append(metrics)
        confusion_rows.extend(rows)

    disagreements = pd.DataFrame(index=urls)
    for name, frame in data.items():
        disagreements[f"{name}_sufficient"] = frame["sufficient"]
        disagreements[f"{name}_category"] = frame["inferred_category"]
    for first, second in pairs:
        disagreements[f"{first}_vs_{second}_suff_diff"] = (
            disagreements[f"{first}_sufficient"] != disagreements[f"{second}_sufficient"]
        )
        disagreements[f"{first}_vs_{second}_category_diff"] = (
            disagreements[f"{first}_category"] != disagreements[f"{second}_category"]
        )
    diff_columns = [column for column in disagreements if column.endswith("_diff")]
    disagreements = disagreements.loc[disagreements[diff_columns].any(axis=1)]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary).to_csv(OUTPUT_DIR / "agreement_summary.csv", index=False)
    pd.DataFrame(confusion_rows).to_csv(OUTPUT_DIR / "confusion_matrices.csv", index=False)
    disagreements.to_csv(OUTPUT_DIR / "disagreements.csv", index_label="url")
    print(f"\nSaved comparisons to {OUTPUT_DIR}/")
    print(f"Reports with at least one disagreement: {len(disagreements)} of {len(urls)}")
    print("Human A vs Human B measures inter-human reliability.")
    print("Human-LLM and LLM-LLM comparisons describe model agreement.")


if __name__ == "__main__":
    main()