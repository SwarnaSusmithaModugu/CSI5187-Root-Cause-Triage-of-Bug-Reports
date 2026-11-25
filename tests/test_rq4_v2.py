import pandas as pd
import pytest

from src.rq4_v2.audit import unit_entries


def test_hidden_comment_excluded_from_robust_units():
    row = pd.Series({
        "description": "A sufficiently long description paragraph for this test.",
        "code_text": "x" * 40,
        "stack_text": "at example.Method.run(Method.java:1)" + "x" * 20,
        "comments_model": "a" * 50,
    })
    units = unit_entries(row, include_comments=False)
    assert "comments_model" not in units


def test_duplicate_unit_rejected_as_missing_source_text():
    row = pd.Series({
        "description": "",
        "code_text": "",
        "stack_text": "",
        "comments_model": "",
    })
    assert unit_entries(row, include_comments=True) == {}
