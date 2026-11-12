"""RQ1 field importance: leave-one-out and leave-one-in with hard and length-matched masking.

Protocol: project-grouped CV, out-of-fold predictions pooled per setting, paired bootstrap over
reports for the macro-F1 change versus the full input. Fields with no text anywhere (e.g. comments
before they are recovered) are skipped automatically.
"""
import numpy as np, pandas as pd
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold

SEED = 42
FILL = "zzfill"

def available_fields(df, candidates=("title", "description", "comments")):
    return [f for f in candidates if f in df.columns and df[f].fillna("").str.strip().ne("").any()]

def build_text(df, keep, all_fields, mode):
    """mode 'hard': dropped fields vanish. mode 'length': dropped fields become a filler of equal token count."""
    parts = []
    for f in all_fields:
        col = df[f].fillna("")
        if f in keep:
            parts.append(col)
        elif mode == "length":
            parts.append(col.apply(lambda t: " ".join([FILL] * len(t.split()))))
    if not parts:
        return [""] * len(df)
    out = parts[0]
    for p in parts[1:]:
        out = out + " " + p
    return out.tolist()

def oof_predictions(texts, y, groups, n_splits=5):
    texts = np.array(texts, dtype=object)
    pred = np.empty(len(y), dtype=object)
    # stratified + grouped: no project on both sides, and classes stay roughly balanced per fold
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    for tr, te in cv.split(texts, y, groups):
        pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
                         ("clf", LinearSVC(random_state=SEED))])
        pipe.fit(texts[tr].tolist(), y[tr])
        pred[te] = pipe.predict(texts[te].tolist())
    return pred

def paired_bootstrap_delta(y, pred_a, pred_b, n=2000, seed=SEED):
    """Delta macro-F1 (a minus b) with a 95% CI, resampling reports."""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y))
    deltas = []
    for _ in range(n):
        s = rng.choice(idx, len(idx), replace=True)
        deltas.append(f1_score(y[s], pred_a[s], average="macro") - f1_score(y[s], pred_b[s], average="macro"))
    return float(np.mean(deltas)), *np.percentile(deltas, [2.5, 97.5])

def run_ablation(df, label_col="root_cause", group_col="project", n_splits=5):
    fields = available_fields(df)
    y = df[label_col].values
    groups = df[group_col].values
    full_pred = oof_predictions(build_text(df, fields, fields, "hard"), y, groups, n_splits)
    full_f1 = f1_score(y, full_pred, average="macro")
    rows = [{"setting": "full", "mode": "-", "macro_f1": full_f1, "delta_vs_full": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}]
    for mode in ("hard", "length"):
        for f in fields:
            for kind, keep in (("loo", [x for x in fields if x != f]), ("loi", [f])):
                if not keep:
                    continue
                pred = oof_predictions(build_text(df, keep, fields, mode), y, groups, n_splits)
                d, lo, hi = paired_bootstrap_delta(y, pred, full_pred)
                rows.append({"setting": f"{kind}_{f}", "mode": mode,
                             "macro_f1": f1_score(y, pred, average="macro"),
                             "delta_vs_full": d, "ci_lo": lo, "ci_hi": hi})
    return pd.DataFrame(rows)
