"""Feasibility audit for controlled restoration of existing gold-report text."""

import re
from pathlib import Path

import pandas as pd


MIN_UNIT_CHARS = 30
MAX_UNIT_CHARS = 2000
MIN_REPORTS = 100
MIN_PROJECTS = 40
MIN_PER_CLASS = 20


def description_units(text):
    if not isinstance(text, str):
        return []
    paragraphs = re.split(r"\n\s*\n+", text)
    return [
        paragraph.strip()
        for paragraph in paragraphs
        if MIN_UNIT_CHARS <= len(paragraph.strip()) <= MAX_UNIT_CHARS
    ]


def audit_row(row):
    units = {}
    for index, paragraph in enumerate(description_units(row["description"])):
        units[f"description_p{index}"] = paragraph
    for name in ["code_text", "stack_text", "comments_model"]:
        value = row.get(name, "")
        if isinstance(value, str):
            value = value.strip()
            if MIN_UNIT_CHARS <= len(value) <= MAX_UNIT_CHARS:
                units[name] = value

    eligible = len(units) >= 2
    reasons = []
    if len(units) < 2:
        reasons.append("fewer_than_two_eligible_units")
    if len(units) >= 2:
        reasons.append("two_or_more_authentic_nonoverlapping_units")

    return pd.Series({
        "url": row["url"],
        "project": row["project"],
        "label_for_audit_only": row["root_cause"],
        "eligible": eligible,
        "n_units": len(units),
        "unit_ids": "|".join(units),
        "eligibility_reason": ";".join(reasons),
        "text_provenance": "description_clean/code/stack/comments_model",
        "leakage_flags": "no_fix_commit_or_gold_label_used",
    })


def main():
    data = pd.read_csv("data/processed/gold_v1.csv")
    required = {
        "url", "project", "root_cause", "description", "code_text",
        "stack_text", "comments_model",
    }
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing RQ4 feasibility columns: {missing}")

    manifest = data.apply(audit_row, axis=1)
    eligible = manifest[manifest["eligible"]]
    output = Path("results/rq4")
    output.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output / "feasibility.csv", index=False)

    counts = data.assign(eligible=manifest["eligible"]).groupby(
        "root_cause"
    )["eligible"].agg(["sum", "count"])
    counts.columns = ["eligible", "total"]
    print("RQ4 feasibility manifest")
    print(manifest[manifest["eligible"]][[
        "url", "project", "label_for_audit_only", "n_units"
    ]].head())
    print("eligible reports:", len(eligible))
    print("eligible projects:", eligible["project"].nunique())
    print("per-class:")
    print(counts)

    class_ok = all(
        counts.loc[label, "eligible"] >= MIN_PER_CLASS
        for label in ["concurrency", "memory", "semantic"]
        if label in counts.index
    )
    go = (
        len(eligible) >= MIN_REPORTS
        and eligible["project"].nunique() >= MIN_PROJECTS
        and class_ok
    )
    print("go_no_go:", "GO" if go else "NO-GO")


if __name__ == "__main__":
    main()
