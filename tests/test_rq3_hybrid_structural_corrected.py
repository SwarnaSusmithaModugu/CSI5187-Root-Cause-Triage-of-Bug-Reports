import pandas as pd
import pytest

from src.rq3_hybrid_structural_corrected import assemble


def fixture_data():
    return pd.DataFrame({
        "title": ["Race", "Memory"],
        "description_clean": ["stack trace", "buffer"],
        "comments_model": ["thread", "heap"],
        "has_stack": [True, False],
        "has_code": [False, True],
        "n_comments_prefix": [1, 0],
    })


def test_assemble_requires_original_structural_columns():
    data = fixture_data().drop(columns=["has_stack"])
    with pytest.raises(ValueError, match="Missing required.*has_stack"):
        assemble(data, None, False)


def test_assemble_rejects_missing_structural_values():
    data = fixture_data()
    data["has_code"] = pd.Series([True, pd.NA], dtype="boolean")
    with pytest.raises(ValueError, match="missing values.*has_code"):
        assemble(data, None, False)


def test_assemble_includes_nonconstant_structural_features():
    features, numeric = assemble(fixture_data(), None, False)
    assert "has_stack" in numeric
    assert "has_code" in numeric
    assert features["has_stack"].tolist() == [1.0, 0.0]
    assert features["has_code"].tolist() == [0.0, 1.0]
