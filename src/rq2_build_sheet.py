from pathlib import Path

import pandas as pd


SEED = 42
LAB = ["concurrency", "memory", "semantic"]


def main():
    outdir = Path("data/interim")
    outdir.mkdir(parents=True, exist_ok=True)
    gold = pd.read_csv("data/processed/gold_v1.csv")
    needed = {"url", "project", "root_cause", "title", "description_clean"}
    if not needed.issubset(gold.columns):
        raise ValueError(f"Gold missing: {needed - set(gold.columns)}")
    if gold["url"].isna().any() or not gold["url"].is_unique:
        raise ValueError("Gold has missing or duplicate URLs")
    if gold["project"].isna().any():
        raise ValueError("Gold has missing projects")
    if set(gold["root_cause"]) != set(LAB):
        raise ValueError("Gold root-cause labels do not match the RQ2 labels")

    sampled = pd.concat(
        [gold.loc[gold["root_cause"] == lab].sample(
            n=min(67, (gold["root_cause"] == lab).sum()),
            random_state=SEED,
        ) for lab in LAB],
        ignore_index=True,
    )
    sheet = sampled[["url", "project", "title", "description_clean"]].copy()
    for col in ["sufficient", "inferred_category", "evidence_span", "missing_info"]:
        sheet[col] = ""
    sheet = sheet.sample(frac=1, random_state=SEED + 1).reset_index(drop=True)
    sheet.to_csv(outdir / "sufficiency_sheet.csv", index=False)

    overlap = sheet.sample(n=min(50, len(sheet)), random_state=SEED + 2)
    overlap.to_csv(outdir / "pilot_overlap_template.csv", index=False)
    print(f"Created {len(sheet)} annotation rows across "
          f"{sheet['project'].nunique()} projects; {len(overlap)} overlap rows.")
    print("Complete sufficiency_sheet.csv -> sufficiency_labels.csv; "
          "keep all annotation fields. Annotate overlap independently "
          "in pilot_A.csv and pilot_B.csv before discussion.")


if __name__ == "__main__":
    main()