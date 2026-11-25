import pandas as pd

from src.rq4_feasibility import audit_row


def test_audit_requires_two_units():
    row = pd.Series({
        "url": "https://example.test/1",
        "project": "example/project",
        "root_cause": "memory",
        "description": "This is a sufficiently long prose paragraph for one unit.",
        "code_text": "",
        "stack_text": "",
        "comments_model": "",
    })
    result = audit_row(row)
    assert result["eligible"] is False
    assert result["n_units"] == 1


def test_audit_accepts_distinct_authentic_units():
    row = pd.Series({
        "url": "https://example.test/2",
        "project": "example/project",
        "root_cause": "concurrency",
        "description": "This prose paragraph is long enough to qualify as an evidence unit.",
        "code_text": "",
        "stack_text": "at example.Thread.run(Thread.java:123)\n at example.Work.run(Work.java:456)",
        "comments_model": "",
    })
    result = audit_row(row)
    assert result["eligible"] is True
    assert result["n_units"] == 2
