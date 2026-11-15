"""Score the author-verified silver review against LLM proposals."""

import pandas as pd
from sklearn.metrics import cohen_kappa_score


def main():
    review = pd.read_csv("data/interim/silver_review_final.csv")
    review = review[
        review["final_label"].isin(["concurrency", "memory", "semantic"])
    ]
    precision = (review["final_label"] == review["silver_label"]).mean()
    llm_agreement = (review["final_label"] == review["llm_label"]).mean()
    kappa = cohen_kappa_score(review["final_label"], review["llm_label"])
    print(f"reviewed {len(review)}")
    print(f"SILVER PRECISION (your verified label == silver): {precision:.3f}")
    print(
        f"you vs LLM agreement: {llm_agreement:.3f}  "
        f"kappa: {kappa:.3f}"
    )
    print(
        "per class precision:",
        review.assign(
            ok=review["final_label"] == review["silver_label"]
        )
        .groupby("silver_label")["ok"]
        .mean()
        .round(3)
        .to_dict(),
    )


if __name__ == "__main__":
    main()
