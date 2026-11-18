from pathlib import Path
import re

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

SEED = 42
LAB = ["concurrency", "memory", "semantic"]
ALLOWED = set(LAB) | {"none"}
N_SPLITS = 5
EMBEDDER = "all-MiniLM-L6-v2"


def normalized(text):
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


def load():
    gold = pd.read_csv("data/processed/gold_v1.csv").reset_index(drop=True)
    hum = pd.read_csv("data/interim/sufficiency_labels.csv")
    gold_fields = {"url", "project", "root_cause", "title", "description_clean"}
    hum_fields = {"url", "sufficient", "inferred_category", "evidence_span", "missing_info"}
    if not gold_fields.issubset(gold.columns):
        raise ValueError(f"Gold missing: {gold_fields - set(gold.columns)}")
    if not hum_fields.issubset(hum.columns):
        raise ValueError(f"Annotations missing: {hum_fields - set(hum.columns)}")

    for label, d in [("gold", gold), ("human", hum)]:
        if d["url"].isna().any() or not d["url"].is_unique:
            raise ValueError(f"{label}: missing/duplicate URLs")
    if gold["project"].isna().any():
        raise ValueError("Gold has missing projects")
    if not gold["root_cause"].isin(LAB).all():
        raise ValueError("Gold contains unknown root-cause labels")
    if not set(hum["url"]).issubset(set(gold["url"])):
        raise ValueError("Annotations contain URLs absent from gold_v1.csv")

    vals = pd.to_numeric(hum["sufficient"], errors="coerce")
    if not vals.isin([0, 1]).all():
        raise ValueError("Missing/invalid human sufficiency labels; do not silently drop")
    hum["sufficient"] = vals.astype(int)
    for col in ["inferred_category", "evidence_span", "missing_info"]:
        hum[col] = hum[col].fillna("").astype(str).str.strip()
    hum["inferred_category"] = hum["inferred_category"].str.lower()
    if not hum["inferred_category"].isin(ALLOWED).all():
        raise ValueError("Invalid inferred_category values")
    if ((hum["sufficient"] == 1) &
            ((hum["inferred_category"] == "none") |
             (hum["evidence_span"] == ""))).any():
        raise ValueError("Sufficient reports require an inferred category and cited span")
    if ((hum["sufficient"] == 0) & (hum["missing_info"] == "")).any():
        raise ValueError("Insufficient reports require missing_info")

    joined = gold.set_index("url")
    for row in hum.itertuples(index=False):
        if row.evidence_span:
            report = (str(joined.loc[row.url, "title"]) + " " +
                      str(joined.loc[row.url, "description_clean"]))
            if normalized(row.evidence_span) not in normalized(report):
                raise ValueError(f"Evidence span not found in title/description: {row.url}")
    if "title" in hum.columns and "description_clean" in hum.columns:
        for row in hum.itertuples(index=False):
            if (normalized(row.title) != normalized(joined.loc[row.url, "title"]) or
                normalized(row.description_clean) !=
                normalized(joined.loc[row.url, "description_clean"])):
                raise ValueError(f"Annotated text does not match frozen gold: {row.url}")
    return gold, hum


def oof(gold, hum):
    encoder = SentenceTransformer(EMBEDDER)
    texts = (gold["title"].fillna("") + ". " +
             gold["description_clean"].fillna("")).tolist()
    X = encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    y = gold["root_cause"].to_numpy()
    groups = gold["project"].to_numpy()
    urls = gold["url"].to_numpy()
    hum_by_url = hum.set_index("url")["sufficient"].to_dict()
    annotated = np.array([u in hum_by_url for u in urls], dtype=bool)
    s = np.array([hum_by_url.get(u, -1) for u in urls], dtype=int)

    n = len(gold)
    pred = np.full(n, "", dtype=object)
    confidence = np.full(n, np.nan)
    p_sufficient = np.full(n, np.nan)
    fold_id = np.full(n, -1, dtype=int)
    splitter = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True,
                                    random_state=SEED)

    for fold, (tr, te) in enumerate(splitter.split(X, y, groups)):
        train_projects = set(groups[tr])
        test_projects = set(groups[te])
        if train_projects & test_projects:
            raise AssertionError(f"Fold {fold}: project leakage")
        if set(y[tr]) != set(LAB):
            raise ValueError(f"Fold {fold}: root-cause train split lacks a class")

        rc = LogisticRegression(max_iter=1000, class_weight="balanced")
        rc.fit(X[tr], y[tr])
        probs = rc.predict_proba(X[te])
        order = [list(rc.classes_).index(c) for c in LAB]
        probs = probs[:, order]
        pred[te] = np.asarray(LAB)[probs.argmax(axis=1)]
        confidence[te] = probs.max(axis=1)
        fold_id[te] = fold

        train_annotated = tr[annotated[tr]]
        test_annotated = te[annotated[te]]
        counts = np.bincount(s[train_annotated], minlength=2)
        print(f"Fold {fold}: RC train={len(tr)}, RC test={len(te)}, "
              f"sufficiency train={len(train_annotated)} "
              f"(insufficient={counts[0]}, sufficient={counts[1]}), "
              f"sufficiency test={len(test_annotated)}")
        if counts.min() < 2:
            raise ValueError(f"Fold {fold}: too few examples of one sufficiency "
                             "class in training projects; revise sampling/folds "
                             "before evaluating, not by dropping the fold")
        if len(test_annotated) == 0:
            raise ValueError(f"Fold {fold}: no annotated held-out reports")
        suff_clf = LogisticRegression(max_iter=1000, class_weight="balanced")
        suff_clf.fit(X[train_annotated], s[train_annotated])
        index_1 = list(suff_clf.classes_).index(1)
        p_sufficient[test_annotated] = suff_clf.predict_proba(
            X[test_annotated])[:, index_1]

    if (fold_id < 0).any() or (pred == "").any() or np.isnan(confidence).any():
        raise AssertionError("Missing root-cause OOF predictions")
    if np.isnan(p_sufficient[annotated]).any():
        raise AssertionError("Missing sufficiency OOF predictions on annotated reports")
    if not np.isnan(p_sufficient[~annotated]).all():
        raise AssertionError("Unexpected sufficiency scores on unannotated reports")
    if not np.isfinite(p_sufficient[annotated]).all():
        raise AssertionError("Nonfinite sufficiency scores")

    return pd.DataFrame({
        "url": urls, "project": groups, "fold": fold_id,
        "y": y, "pred": pred, "correct": (pred == y).astype(int),
        "confidence": confidence, "p_sufficient": p_sufficient,
        "annotated": annotated,
    })


def ranked_correct(score, correct):
    score = np.asarray(score, dtype=float)
    correct = np.asarray(correct, dtype=int)
    if len(score) == 0 or len(score) != len(correct):
        raise ValueError("Empty or mismatched score/correct vectors")
    if not np.isfinite(score).all() or not np.isin(correct, [0, 1]).all():
        raise ValueError("Invalid score/correct values")
    return correct[np.argsort(-score, kind="mergesort")]


def aurc(score, correct):
    c = ranked_correct(score, correct)
    return float(np.mean(1 - np.cumsum(c) / np.arange(1, len(c) + 1)))


def err_at(score, correct, coverage):
    if not 0 < coverage <= 1:
        raise ValueError("coverage must be in (0, 1]")
    c = ranked_correct(score, correct)
    k = max(1, int(np.ceil(coverage * len(c))))
    return float(1 - c[:k].mean())


def paired_project_delta(base, method, correct, groups,
                         metric="aurc", n_boot=2000, seed=SEED):
    base = np.asarray(base, dtype=float)
    method = np.asarray(method, dtype=float)
    correct = np.asarray(correct, dtype=int)
    groups = np.asarray(groups)
    if not (len(base) == len(method) == len(correct) == len(groups)):
        raise ValueError("Paired vectors have different lengths")
    measure = aurc if metric == "aurc" else (
        (lambda sc, co: err_at(sc, co, 0.80)) if metric == "err80" else None
    )
    if measure is None:
        raise ValueError("metric must be 'aurc' or 'err80'")
    observed = measure(base, correct) - measure(method, correct)
    projects = pd.unique(groups)
    by_project = {p: np.flatnonzero(groups == p) for p in projects}
    if len(projects) < 2:
        raise ValueError("Project-cluster bootstrap requires multiple projects")
    rng = np.random.default_rng(seed)
    replicates = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        sampled = rng.choice(projects, size=len(projects), replace=True)
        idx = np.concatenate([by_project[p] for p in sampled])
        replicates[b] = (measure(base[idx], correct[idx]) -
                         measure(method[idx], correct[idx]))
    lo, hi = np.percentile(replicates, [2.5, 97.5])
    return float(observed), float(lo), float(hi)


def report_rq2_diagnostics(subset: pd.DataFrame, hum: pd.DataFrame) -> None:
    """Report diagnostics on the same annotated OOF cases as selection."""
    required_oof = {"url", "project", "correct", "confidence", "p_sufficient"}
    required_human = {"url", "sufficient"}
    if not required_oof.issubset(subset.columns):
        raise ValueError(f"OOF subset missing {required_oof - set(subset.columns)}")
    if not required_human.issubset(hum.columns):
        raise ValueError(f"Human labels missing {required_human - set(hum.columns)}")
    if subset["url"].duplicated().any() or hum["url"].duplicated().any():
        raise ValueError("Duplicate URL in annotated subset or human labels")

    data = subset.drop(columns=["sufficient"], errors="ignore").merge(
        hum[["url", "sufficient"]],
        how="left", on="url", validate="one_to_one", indicator=True,
    )
    if len(data) != len(subset) or not data["_merge"].eq("both").all():
        raise AssertionError("OOF and human annotations are not aligned 1:1")
    data = data.drop(columns="_merge")

    label = data["sufficient"].astype(int).to_numpy()
    probability = data["p_sufficient"].to_numpy(dtype=float)
    confidence = data["confidence"].to_numpy(dtype=float)
    correct = data["correct"].to_numpy(dtype=int)
    if (not np.isin(label, [0, 1]).all()
            or not np.isin(correct, [0, 1]).all()
            or not np.isfinite(probability).all()
            or not np.isfinite(confidence).all()
            or not np.logical_and(probability >= 0, probability <= 1).all()
            or not np.logical_and(confidence >= 0, confidence <= 1).all()):
        raise ValueError("Invalid labels, correctness flags, or finite score ranges")

    hard = (probability >= 0.5).astype(int)
    print("\n=== RQ2 sufficiency-model diagnostics (annotated OOF subset) ===")
    print(f"N={len(data)}; sufficient={int(label.sum())}; "
          f"insufficient={int((label == 0).sum())}; "
          f"projects={data['project'].nunique()}")
    print("Confusion matrix (rows=human; cols=model; labels 0=insufficient, 1=sufficient):")
    print(confusion_matrix(label, hard, labels=[0, 1]))
    print(classification_report(
        label, hard, labels=[0, 1],
        target_names=["insufficient", "sufficient"],
        digits=3, zero_division=0,
    ))

    baseline_f1_sufficient = (
        2 * label.sum() / (len(label) + label.sum()) if label.sum() else 0.0
    )
    print(f"Always-sufficient baseline positive-class F1: "
          f"{baseline_f1_sufficient:.3f}")
    if np.unique(label).size == 2:
        print(f"Sufficiency ROC-AUC: {roc_auc_score(label, probability):.3f}")
        print(f"Insufficient-class AP (positive = insufficient): "
              f"{average_precision_score(1 - label, 1 - probability):.3f}")
        print(f"Insufficient prevalence: {(label == 0).mean():.3f}")
    else:
        print("Sufficiency ROC-AUC and insufficient AP undefined: one label class")

    print("\n=== Root-cause correctness by HUMAN sufficiency ===")
    group_summary = (
        data.groupby("sufficient", sort=True)["correct"]
        .agg(n="size", correct_rate="mean")
        .reset_index()
    )
    group_summary["error_rate"] = 1 - group_summary["correct_rate"]
    print(group_summary.to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    print("\n=== Ability to rank CORRECT root-cause predictions ===")
    if np.unique(correct).size == 2:
        print(f"Correctness ROC-AUC, confidence: {roc_auc_score(correct, confidence):.3f}")
        print(f"Correctness ROC-AUC, sufficiency: {roc_auc_score(correct, probability):.3f}")
    else:
        print("Correctness ROC-AUC undefined: every prediction has same outcome")
    if np.unique(confidence).size > 1 and np.unique(probability).size > 1:
        rho = spearmanr(confidence, probability).statistic
        print(f"Spearman correlation, confidence vs sufficiency: {rho:.3f}")
    else:
        print("Spearman correlation undefined: a score is constant")

    Path("results").mkdir(parents=True, exist_ok=True)
    group_summary.to_csv("results/rq2_correctness_by_human_sufficiency.csv", index=False)
    data[["url", "project", "sufficient", "correct", "confidence",
          "p_sufficient"]].to_csv("results/rq2_diagnostic_subset.csv", index=False)


def audit_mini_lm_truncation(gold: pd.DataFrame, hum: pd.DataFrame) -> None:
    """Audit encoder-window visibility without changing model inputs or labels."""
    if not {"url", "title", "description_clean"}.issubset(gold.columns):
        raise ValueError("Missing gold title/description fields")
    if not {"url", "evidence_span", "sufficient"}.issubset(hum.columns):
        raise ValueError("Missing annotation evidence_span/sufficient fields")

    encoder = SentenceTransformer(EMBEDDER)
    tokenizer = encoder.tokenizer
    limit = int(encoder.max_seq_length)
    if limit <= 0:
        raise ValueError("Could not read encoder max_seq_length")
    reports = gold[["url", "title", "description_clean"]].copy()
    reports["input_text"] = (
        reports["title"].fillna("") + ". " +
        reports["description_clean"].fillna("")
    )
    annotated = reports.merge(
        hum[["url", "evidence_span", "sufficient"]],
        on="url", how="left", validate="one_to_one"
    )
    results = []
    for row in annotated.itertuples(index=False):
        original = tokenizer(row.input_text, add_special_tokens=True, truncation=False)
        full_n = len(original["input_ids"])
        encoded = tokenizer(
            row.input_text, add_special_tokens=True, max_length=limit,
            truncation=True, return_offsets_mapping=True,
        )
        offsets = encoded["offset_mapping"]
        visible_end = max((end for start, end in offsets if end > start), default=0)
        is_annotated = pd.notna(row.sufficient)
        span = "" if pd.isna(row.evidence_span) else str(row.evidence_span).strip()
        status = "not_annotated"
        if is_annotated:
            if not span:
                status = "no_span_provided"
            else:
                start = row.input_text.casefold().find(span.casefold())
                if start == -1:
                    status = "span_not_exactly_located"
                elif start >= visible_end:
                    status = "span_entirely_after_window"
                elif start + len(span) > visible_end:
                    status = "span_partly_truncated"
                else:
                    status = "span_inside_window"
        results.append({
            "url": row.url,
            "annotated": bool(is_annotated),
            "sufficient": row.sufficient if is_annotated else np.nan,
            "wordpiece_count_with_special_tokens": full_n,
            "encoder_limit": limit,
            "truncated": bool(full_n > limit),
            "visible_character_end_approx": visible_end,
            "evidence_span_status": status,
        })

    audit = pd.DataFrame(results)
    audit.to_csv("results/rq2_embedding_truncation_audit.csv", index=False)
    print("\n=== MiniLM truncation audit ===")
    print(f"Max sequence length used by encoder: {limit} wordpieces")
    print(f"All reports truncated: {int(audit['truncated'].sum())}/{len(audit)} "
          f"({audit['truncated'].mean():.1%})")
    annotated_audit = audit[audit["annotated"]]
    print(f"Annotated reports truncated: {int(annotated_audit['truncated'].sum())}/"
          f"{len(annotated_audit)} ({annotated_audit['truncated'].mean():.1%})")
    print("Human evidence-span placement:")
    print(annotated_audit["evidence_span_status"].value_counts(dropna=False).to_string())
    print("Saved: results/rq2_embedding_truncation_audit.csv")


def main():
    gold, hum = load()
    out = oof(gold, hum)
    subset = out.loc[out["annotated"]].copy()
    if len(subset) != len(hum):
        raise AssertionError("Not every human annotation reached final evaluation")
    if subset["p_sufficient"].isna().any():
        raise AssertionError("An annotated report is missing a sufficiency score")

    # Diagnostics only; no model, fold, or policy changes.
    report_rq2_diagnostics(subset, hum)
    audit_mini_lm_truncation(gold, hum)

    print(f"\nGold reports: {len(gold)}; annotated/evaluated: {len(subset)}; "
          f"evaluation projects: {subset['project'].nunique()}; "
          f"human sufficient-rate: {hum['sufficient'].mean():.3f}")
    print(f"RC macro-F1 on ALL gold OOF reports: "
          f"{f1_score(out['y'], out['pred'], average='macro'):.3f}")
    print(f"RC macro-F1 on ANNOTATED OOF subset: "
          f"{f1_score(subset['y'], subset['pred'], average='macro'):.3f}")

    correct = subset["correct"].to_numpy()
    projects = subset["project"].to_numpy()
    sig = {
        "confidence": subset["confidence"].to_numpy(),
        "sufficiency": subset["p_sufficient"].to_numpy(),
        "combined": (subset["confidence"] * subset["p_sufficient"]).to_numpy(),
    }
    print("\nSelective prediction on the SAME annotated held-out examples:")
    for name, score in sig.items():
        risks = {f"err@{int(k * 100)}%": round(err_at(score, correct, k), 3)
                 for k in [0.90, 0.80, 0.70]}
        print(f"{name:12s} AURC={aurc(score, correct):.4f}  {risks}")

    print("\nPaired project-clustered differences (baseline minus combined):")
    for baseline in ["confidence", "sufficiency"]:
        for metric in ["aurc", "err80"]:
            obs, lo, hi = paired_project_delta(
                sig[baseline], sig["combined"], correct, projects, metric=metric)
            print(f"vs {baseline:11s} {metric:5s}: observed Delta={obs:+.4f}, "
                  f"95% bootstrap CI=[{lo:+.4f}, {hi:+.4f}]")

    check = gold[["url", "root_cause"]].merge(
        hum[["url", "sufficient", "inferred_category"]],
        on="url", validate="one_to_one")
    sufficient = check[check["sufficient"] == 1]
    n_sufficient = len(sufficient)
    if n_sufficient:
        match = (sufficient["inferred_category"] ==
                 sufficient["root_cause"].str.lower())
        print(f"\nConstruct cross-check: annotator's inferred category "
              f"matches gold for {match.sum()}/{n_sufficient} "
              f"({match.mean():.3f}) reports judged sufficient")
        print("Sufficient reports by gold class:",
              sufficient["root_cause"].value_counts().to_dict())
    else:
        print("\nConstruct cross-check unavailable: no sufficient reports")

    Path("results").mkdir(parents=True, exist_ok=True)
    out.to_csv("results/rq2_oof.csv", index=False)
    subset.to_csv("results/rq2_evaluation_subset.csv", index=False)
    print("Wrote results/rq2_oof.csv and results/rq2_evaluation_subset.csv")


if __name__ == "__main__":
    main()