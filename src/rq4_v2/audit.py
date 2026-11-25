"""Build RQ4 v2 source, unit, and project-fold audits."""

import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from src.rq4_feasibility import description_units


SEED = 42
OUTPUT = Path("results/rq4/v2")
MIN_UNIT_CHARS = 30
MAX_UNIT_CHARS = 2000


def unit_entries(row, include_comments=False):
    entries = {}
    for index, paragraph in enumerate(description_units(row["description"])):
        start = str(row["description"]).find(paragraph)
        entries[f"description_p{index}"] = (
            "description", paragraph, max(start, 0),
        )
    for name in ["code_text", "stack_text"]:
        value = row.get(name, "")
        if isinstance(value, str):
            value = value.strip()
            if MIN_UNIT_CHARS <= len(value) <= MAX_UNIT_CHARS:
                start = str(row["description"]).find(value)
                entries[name] = (name, value, max(start, 0))
    if include_comments:
        value = row.get("comments_model", "")
        if isinstance(value, str):
            value = value.strip()
            if MIN_UNIT_CHARS <= len(value) <= MAX_UNIT_CHARS:
                entries["comments_model"] = ("comments_model", value, 0)
    return entries


def clean_overlap_flags(entries):
    item_ids = list(entries)
    for unit_id, (source, text, offset) in entries.items():
        yield unit_id, source, text, offset, any(
            unit_id != other and text in other_text
            for other in item_ids
            for other_source, other_text, other_offset in [entries[other]]
        )


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv("data/processed/gold_v1.csv")
    unit_rows = []
    manifest_rows = []

    for _, row in data.iterrows():
        entries = unit_entries(row, include_comments=True)
        for unit_id, source, text, offset, overlap in clean_overlap_flags(entries):
            unit_rows.append({
                "url": row["url"],
                "unit_id": unit_id,
                "unit_type": source,
                "source_field": source,
                "offset_start": offset,
                "offset_end": offset + len(text),
                "char_len": len(text),
                "token_len": len(text.split()),
                "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "overlap_flag": bool(overlap),
                "temporal_status": (
                    "pre-fix cutoff" if source == "comments_model"
                    else "retrospective archived report text"
                ),
                "eligible": MIN_UNIT_CHARS <= len(text) <= MAX_UNIT_CHARS,
            })

        robust_entries = unit_entries(row, include_comments=False)
        manifest_rows.append({
            "url": row["url"],
            "project": row["project"],
            "label_for_audit_only": row["root_cause"],
            "n_units_original_v1": len(entries),
            "n_units_robust_no_comments": len(robust_entries),
            "unit_ids_original_v1": "|".join(entries),
            "unit_ids_robust_no_comments": "|".join(robust_entries),
            "eligible_original_v1": len(entries) >= 2,
            "eligible_robust_no_comments": len(robust_entries) >= 2,
            "leakage_flags": "no_fix_commit_or_gold_label_used",
            "temporal_status": "mixed; comments excluded from primary robust cohort",
        })

    pd.DataFrame(unit_rows).to_csv(OUTPUT / "unit_audit.csv", index=False)
    pd.DataFrame(manifest_rows).to_csv(OUTPUT / "unit_manifest_v2.csv", index=False)

    eligible = data[data.apply(
        lambda row: len(unit_entries(row, include_comments=False)) >= 2, axis=1
    )].reset_index(drop=True)
    fold_ids = [-1] * len(data)
    robust_index = {row["url"]: index for index, row in eligible.iterrows()}
    fold = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
    fold_rows = []
    for fold_id, (_, test) in enumerate(
        fold.split(eligible, eligible["root_cause"], eligible["project"])
    ):
        for index in test:
            url = eligible.iloc[index]["url"]
            fold_rows.append({
                "url": url,
                "project": eligible.iloc[index]["project"],
                "fold_id": fold_id,
            })
    fold_rows.sort(key=lambda item: item["url"])
    fold_map = pd.DataFrame(fold_rows)
    fold_map.to_csv(OUTPUT / "fold_map.csv", index=False)
    fold_payload = json.dumps(
        fold_map.sort_values(["url"]).to_dict("records"),
        sort_keys=True,
    )

    audit = f"""# RQ4 v2 Audit

## Implementation audit

| Check | Status | Evidence |
|---|---|---|
| Hidden-content selector | FAIL | `src/rq4_reveal.py` calls `decision_function` on test candidate unit text and contains the hidden unit text in v1 target selection. |
| V1 unit label use | FAIL | `src/rq4_reveal.py` fits a training text classifier using report root-cause labels and candidate unit text. It is not a predeclared utility policy and unit labels do not establish value. |
| Same-report model | PASS | B0/B1/B2/B3/B4/B5 use one withheld-fitted model per outer test report in v1 construction, except selector-specific invalid v1 actions. |
| Comments time boundary | UNKNOWN | `src/build_processed.py:35-54` applies fix/closed comment cutoffs, but filing-time timestamps are unavailable. Comments are excluded from the primary robust v2 cohort. |
| Code/stack provenance | MIXED | `src/clean.py:25-63` extracts code and stack text from the archived description. `src/build_processed.py:86-100` renames extracted fields. These units can duplicate description content. |
| Unit offsets | PARTIAL | Unit audit stores offsets for exact description extracts; code/stack offsets are source-linked to description where found. |
| Project boundaries | PASS | Reuse one 5-fold `StratifiedGroupKFold(seed=42)` mapping for the robust v2 cohort. |
| V1 archive | PASS | v1 CSV files were not overwritten. New artifacts are under `results/rq4/v2/`. |

## Remediation

The v1 targeted selector is invalid as a learnable acquisition policy because it
reads withheld candidate text. It is retained only as a historical reference
and is not used as a valid v2 method. Phase 3 C-VOI is blocked until the
Phase 2 baselines pass leakage and matching gates.

## Cohorts

- Robust no-comments eligible reports: {len(eligible)}
- Robust projects: {eligible['project'].nunique()}
- Fold mapping SHA-256: {hashlib.sha256(fold_payload.encode()).hexdigest()}
"""
    (OUTPUT / "audit.md").write_text(audit, encoding="utf-8")

    protocol = """# RQ4 v2 Experiment Protocol

Primary robust cohort excludes `comments_model`. Candidate units are coherent
description paragraphs and source-linked code/stack extracts. The visible state
is title plus remaining description text, unit type, unit index, unit count,
and length metadata. Hidden candidate text, embeddings, labels, correctness,
restored margins, and outcomes are never selector features.

B0 is withheld. B1 is one reveal chosen uniformly by predeclared seeds.
B2 is closest length. B3 is same-type plus closest length. B4 is a training-derived
field-type preference with deterministic fallback. B5 is the historical v1
method and is marked invalid for test-time selection. REF restores all allowed
source units.

All conditions share each report's one outer-fold fitted withheld LinearSVC.
"""
    (OUTPUT / "experiment_protocol.md").write_text(protocol, encoding="utf-8")

    manifest = {
        "experiment_id": "rq4_v2_audit_baselines",
        "seed": SEED,
        "dataset_sha256": hashlib.sha256(
            Path("data/processed/gold_v1.csv").read_bytes()
        ).hexdigest(),
        "fold_map_sha256": hashlib.sha256(fold_payload.encode()).hexdigest(),
        "cohort": "eligible description/code/stack units; comments excluded",
        "eligible_reports": int(len(eligible)),
        "eligible_projects": int(eligible["project"].nunique()),
    }
    (OUTPUT / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
