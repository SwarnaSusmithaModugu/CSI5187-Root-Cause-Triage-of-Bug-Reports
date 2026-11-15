import pandas as pd


def test_frozen():
    gold = pd.read_csv("data/processed/gold_v1.csv")
    assert len(gold) == 369
    assert gold["root_cause"].value_counts().to_dict() == {
        "semantic": 126,
        "concurrency": 122,
        "memory": 121,
    }
    assert gold["url"].nunique() == 369
    assert "comments_model" in gold.columns
