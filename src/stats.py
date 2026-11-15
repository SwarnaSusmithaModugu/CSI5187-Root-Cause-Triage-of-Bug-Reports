import numpy as np
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests


def bootstrap_ci(values, n=2000, alpha=0.05, seed=42):
    rng = np.random.default_rng(seed)
    values = np.asarray(values, float)
    means = [
        rng.choice(values, len(values), replace=True).mean()
        for _ in range(n)
    ]
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(values.mean()), float(lo), float(hi)


def paired_bootstrap(correct_a, correct_b, n=2000, seed=42):
    """Return a bootstrap confidence interval for accuracy difference a-b."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(correct_a, float), np.asarray(correct_b, float)
    indices = np.arange(len(a))
    differences = [
        a[sample].mean() - b[sample].mean()
        for sample in (
            rng.choice(indices, len(indices), replace=True) for _ in range(n)
        )
    ]
    return (
        float(a.mean() - b.mean()),
        float(np.percentile(differences, 2.5)),
        float(np.percentile(differences, 97.5)),
    )


def mcnemar_test(correct_a, correct_b):
    a, b = np.asarray(correct_a, bool), np.asarray(correct_b, bool)
    table = [
        [int((a & b).sum()), int((a & ~b).sum())],
        [int((~a & b).sum()), int((~a & ~b).sum())],
    ]
    return mcnemar(table, exact=True)


def holm(pvalues):
    reject, adjusted, _, _ = multipletests(pvalues, method="holm")
    return list(reject), list(np.round(adjusted, 4))


def cliffs_delta(x, y):
    x, y = np.asarray(x), np.asarray(y)
    greater = sum((value > y).sum() for value in x)
    less = sum((value < y).sum() for value in x)
    return (greater - less) / (len(x) * len(y))
