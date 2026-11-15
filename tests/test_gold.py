import pandas as pd


def test_gold():
    gold = pd.read_csv("data/processed/gold_369.csv")
    assert len(gold) == 369
    assert gold["root_cause"].value_counts().to_dict() == {
        "semantic": 126,
        "concurrency": 122,
        "memory": 121,
    }
    assert gold["url"].nunique() == 369
    assert gold["root_cause"].notna().all()
    assert gold["project"].notna().all()
