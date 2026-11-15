"""Mask fix-revealing comments and freeze the gold dataset."""

import hashlib
import re
from pathlib import Path

import pandas as pd


LEAK = [
    (re.compile(r"fix(ed|es)?\s+(in|by|with)\b", re.I), "<FIXREF>"),
    (re.compile(r"(closes|fixes|resolves)\s+#?\d+", re.I), "<FIXREF>"),
    (re.compile(r"\bpull request\b|\bPR\s*#?\d+\b", re.I), "<FIXREF>"),
    (re.compile(r"\bcommit\s+[0-9a-f]{7,40}\b", re.I), "<FIXREF>"),
    (re.compile(r"\bmerged\b", re.I), "<FIXREF>"),
]


def mask_leak(text):
    value = text if isinstance(text, str) else ""
    for pattern, replacement in LEAK:
        value = pattern.sub(replacement, value)
    return value


def main():
    data = pd.read_csv("data/processed/gold_369.csv")
    assert len(data) == 369, f"expected 369 rows, got {len(data)}"

    source = "comments_clean" if "comments_clean" in data else "comments"
    data["comments_model"] = data[source].apply(mask_leak)
    changed = int((data["comments_model"] != data[source]).sum())
    print(f"comments with a fix-revealing phrase masked: {changed}")

    notes = {
        "empty_descriptions_kept": int(
            data.get("flag_empty", pd.Series([False] * len(data))).sum()
        ),
        "bot_author_kept": int(
            data.get("flag_bot_author", pd.Series([False] * len(data))).sum()
        ),
        "exact_dups": int(
            data.get("flag_exact_dup", pd.Series([False] * len(data))).sum()
        ),
        "near_dups": int(
            data.get("flag_near_dup", pd.Series([False] * len(data))).sum()
        ),
        "cross_label_dups": int(
            data.get(
                "flag_cross_label_dup",
                pd.Series([False] * len(data)),
            ).sum()
        ),
        "reports_with_prefix_comments": int(
            (data.get("n_comments_prefix", 0) > 0).sum()
        ),
    }
    print("keep-and-note counts:", notes)
    assert notes["cross_label_dups"] == 0, (
        "cross-label duplicates exist, resolve by hand before freezing"
    )

    output = Path("data/processed/gold_v1.csv")
    data.to_csv(output, index=False)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()[:16]
    print(
        f"froze {output} rows={len(data)} cols={data.shape[1]} "
        f"sha256_16={digest}"
    )


if __name__ == "__main__":
    main()
