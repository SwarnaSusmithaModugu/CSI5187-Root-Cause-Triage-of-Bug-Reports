"""Clean silver text and remove near-duplicates of gold."""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .clean import add_clean_columns


def main():
    silver = pd.read_csv("data/interim/silver.csv")
    gold = pd.read_csv("data/processed/gold_v1.csv")
    silver = add_clean_columns(silver, "description", "description")
    gold_text = (
        gold["title"].fillna("")
        + " "
        + gold["description_clean"].fillna("")
    ).tolist()
    silver_text = (
        silver["title"].fillna("")
        + " "
        + silver["description_clean"].fillna("")
    ).tolist()
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
    vectorizer.fit(gold_text + silver_text)
    similarities = cosine_similarity(
        vectorizer.transform(silver_text),
        vectorizer.transform(gold_text),
    ).max(axis=1)
    before = len(silver)
    silver = silver[similarities < 0.9].copy()
    print(
        f"dropped {before - len(silver)} silver rows "
        "near-duplicate to gold"
    )
    silver.to_csv("data/processed/silver.csv", index=False)
    print(
        f"final silver: {len(silver)} rows  "
        f"{silver['root_cause'].value_counts().to_dict()}"
    )


if __name__ == "__main__":
    main()
