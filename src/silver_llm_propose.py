"""Generate fix-only LLM proposals for the silver validation sample."""

import pandas as pd


PROMPT = """You are classifying the ROOT CAUSE of a fixed software bug, judging only from the fix below.
Choose exactly one: concurrency, memory, or semantic.
- concurrency: races, deadlocks, synchronization, atomicity, thread-safety.
- memory: leaks, null-pointer/NPE, resource not closed, buffer over/underflow, double-free.
- semantic: any other logic or functionality error (the default; most bugs are semantic).
Answer with one word (concurrency/memory/semantic), then a dash, then a 10-word reason.

COMMIT MESSAGE: {msg}
CHANGED FILES: {paths}
CHANGED METHODS: {methods}
ANSWER:"""


def classify_fix(llm, message, paths, methods):
    """Call an injected temperature-zero model and parse its proposal."""
    output = llm(
        PROMPT.format(
            msg=message[:1500],
            paths=paths[:600],
            methods=methods[:600],
        )
    ).strip().lower()
    label = next(
        (
            word
            for word in ("concurrency", "memory", "semantic")
            if output.startswith(word)
        ),
        "semantic",
    )
    reason = output.split("-", 1)[1].strip() if "-" in output else ""
    return label, reason


def main(llm):
    review = pd.read_csv("data/interim/silver_review.csv")
    labels, reasons = [], []
    for _, row in review.iterrows():
        label, reason = classify_fix(
            llm,
            str(row["commit_message"]),
            str(row["changed_paths"]),
            str(row["changed_methods"]),
        )
        labels.append(label)
        reasons.append(reason)
    review["llm_label"] = labels
    review["llm_reason"] = reasons
    review["final_label"] = ""
    review.to_csv("data/interim/silver_review_llm.csv", index=False)
    print(
        "wrote silver_review_llm.csv; set final_label for each row "
        "after author verification"
    )
