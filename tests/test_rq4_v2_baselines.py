import pandas as pd


def test_phase2_predictions_and_matching_are_complete():
    predictions = pd.read_csv("results/rq4/v2/reveal_predictions.csv")
    assert predictions["url"].nunique() == 295
    assert set(predictions["condition"].unique()) >= {
        "B0_no_reveal",
        "B1_seed_0",
        "B2_length_control",
        "B3_same_type_control",
        "B4_type_preference",
        "B5_v1_target_reference",
        "REF_all_units",
    }
    assert not predictions.isna().any().any()
