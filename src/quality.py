"""Quality flags for the gold table; no rows are removed."""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def add_flags(df):
    text = (
        df["title"].fillna("").astype(str)
        + " "
        + df["description_clean"].fillna("").astype(str)
    ).str.strip()
    df["flag_empty"] = df["description_clean"].fillna("").str.len() < 20
    heading_count = df["description_clean"].fillna("").str.count(
        r"(?i)steps to reproduce|expected|actual|environment"
    )
    df["flag_template_only"] = (
        (heading_count >= 2)
        & (df["description_len_tokens"] < 25)
    )

    def nonlatin_fraction(value):
        alphabetic = [char for char in str(value) if char.isalpha()]
        if not alphabetic:
            return 0.0
        return sum(ord(char) > 127 for char in alphabetic) / len(alphabetic)

    df["flag_non_english"] = text.apply(nonlatin_fraction) > 0.30
    df["flag_is_pr"] = df["url"].str.contains("/pull/", na=False)
    df["flag_bot_author"] = (
        df["user"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(r"bot|\[bot\]|ci|jenkins", na=False)
    )
    normalized = text.str.lower().str.replace(r"\s+", " ", regex=True)
    df["flag_exact_dup"] = normalized.duplicated(keep=False) & normalized.ne("")

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(text)
    similarity = cosine_similarity(matrix)
    np.fill_diagonal(similarity, 0)
    near_duplicate = similarity > 0.90
    df["flag_near_dup"] = near_duplicate.any(axis=1)

    pairs = []
    cross_label_pairs = []
    labels = df["root_cause"].to_numpy()
    for i, j in zip(*np.where(np.triu(near_duplicate, k=1))):
        pair = (
            df.iloc[i]["url"],
            df.iloc[j]["url"],
            round(float(similarity[i, j]), 3),
            labels[i],
            labels[j],
        )
        pairs.append(pair)
        if labels[i] != labels[j]:
            cross_label_pairs.append(pair)

    df["flag_cross_label_dup"] = False
    cross_urls = {
        url for pair in cross_label_pairs for url in pair[:2]
    }
    df.loc[df["url"].isin(cross_urls), "flag_cross_label_dup"] = True

    print("flag counts:")
    for column in df.columns:
        if column.startswith("flag_"):
            print(f"  {column}: {int(df[column].sum())}")
    print(
        f"near-dup pairs: {len(pairs)}  "
        f"cross-label pairs: {len(cross_label_pairs)}"
    )
    for pair in cross_label_pairs:
        print("  CROSS-LABEL:", pair)
    return df, pairs, cross_label_pairs
