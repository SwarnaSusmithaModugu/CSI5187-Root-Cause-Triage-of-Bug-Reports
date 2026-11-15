"""Build capped concurrency+memory silver from trusted fix-grounded signals."""

import json
import re
from pathlib import Path

import pandas as pd

from . import labeling_functions as LF


RAW = Path("data/raw")
LABELS = ["concurrency", "memory", "semantic"]
MIN_LF_ACC = 0.70


def norm_url(url):
    return str(url).strip().lower().replace("http://", "https://").rstrip("/")


def load_report_regexes():
    conc = re.compile(
        r"\b(thread|concurren|lock|deadlock|race|synchroniz|volatile|atomic)\b",
        re.I,
    )
    mem = re.compile(
        r"\b(memory|leak|heap|oom|null|npe|buffer|gc)\b",
        re.I,
    )
    return conc, mem


def iter_complete():
    for path in RAW.rglob("issuesDataWStats.json"):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for issue in data.get("issues", []):
            if issue.get("commitsDetails"):
                yield data["projectName"], issue


def run_lfs(issue, report_conc, report_mem):
    votes = {
        function.__name__: function(issue)
        for function in LF.FIX_LFS
    }
    votes["lf_report_keywords"] = LF.lf_report_keywords(
        issue, report_conc, report_mem
    )
    return votes


def validate_on_gold(gold, report_conc, report_mem):
    url_to_label = dict(
        zip(gold["url"].map(norm_url), gold["root_cause"])
    )
    gold_issues = {}
    for _, issue in iter_complete():
        url = norm_url(issue["url"])
        if url in url_to_label:
            gold_issues[url] = issue
    print(
        f"gold issues with commit data: {len(gold_issues)} "
        f"of {len(url_to_label)}"
    )
    weights = {}
    report = []
    for function in LF.FIX_LFS + [LF.lf_report_keywords]:
        name = function.__name__
        hits = correct = 0
        for url, issue in gold_issues.items():
            prediction = (
                function(issue, report_conc, report_mem)
                if name == "lf_report_keywords"
                else function(issue)
            )
            if prediction is not None:
                hits += 1
                correct += int(prediction == url_to_label[url])
        accuracy = correct / hits if hits else 0.0
        report.append(
            {
                "lf": name,
                "coverage": round(
                    hits / max(len(gold_issues), 1), 3
                ),
                "accuracy_where_fires": round(accuracy, 3),
                "fires": hits,
            }
        )
        if name != "lf_report_keywords":
            weights[name] = accuracy
    print(pd.DataFrame(report).to_string(index=False))
    return weights


def label_model(votes, weights, min_conf=0.66):
    scores = {label: 0.0 for label in LABELS}
    for name, weight in weights.items():
        vote = votes.get(name)
        if vote in LABELS:
            scores[vote] += weight
    if sum(scores.values()) == 0:
        return None, 0.0
    best = max(scores, key=scores.get)
    confidence = scores[best] / sum(weights.values())
    return (
        (best, confidence)
        if confidence >= min_conf
        else (None, confidence)
    )


def main():
    gold = pd.read_csv("data/interim/gold_joined.csv")
    gold_urls = set(gold["url"].map(norm_url))
    report_conc, report_mem = load_report_regexes()
    all_weights = validate_on_gold(gold, report_conc, report_mem)
    weights = {
        name: weight
        for name, weight in all_weights.items()
        if weight >= MIN_LF_ACC
    }
    print(
        "trusted fix LFs (acc >= 0.70):",
        {name: round(weight, 3) for name, weight in weights.items()},
    )
    if not weights:
        raise SystemExit(
            "no fix LF reaches 0.70 on gold; tune lexicons before building silver"
        )

    rows = []
    wild_complete = 0
    focus_filter_removed = 0
    for project, issue in iter_complete():
        if norm_url(issue["url"]) in gold_urls:
            continue
        wild_complete += 1
        if not LF.is_focused_fix(issue):
            focus_filter_removed += 1
            continue
        votes = run_lfs(issue, report_conc, report_mem)
        label, confidence = label_model(votes, weights)
        if label in ("concurrency", "memory"):
            rows.append(
                {
                    "url": issue["url"],
                    "project": project,
                    "title": issue.get("title") or "",
                    "description": issue.get("body") or "",
                    "root_cause": label,
                    "silver_conf": round(confidence, 3),
                    "votes": "|".join(
                        f"{name}={vote}"
                        for name, vote in votes.items()
                        if vote
                    ),
                }
            )

    silver = pd.DataFrame(rows).drop_duplicates("url")
    gold_counts = gold["root_cause"].value_counts().to_dict()
    capped = []
    for label in ("concurrency", "memory"):
        cap = 2 * gold_counts.get(label, 0)
        capped.append(
            silver[silver["root_cause"] == label]
            .sort_values("silver_conf", ascending=False)
            .head(cap)
        )
    silver = pd.concat(capped, ignore_index=True)
    Path("data/interim").mkdir(exist_ok=True, parents=True)
    silver.to_csv("data/interim/silver.csv", index=False)
    print(
        f"wild complete reports: {wild_complete}; "
        f"focus filter removed: {focus_filter_removed}"
    )
    print(
        f"silver: {len(silver)} rows  "
        f"classes={silver['root_cause'].value_counts().to_dict()}"
    )
    print(
        "confidence quartiles:",
        silver["silver_conf"].quantile([0.25, 0.5, 0.75]).round(3).to_dict(),
    )


if __name__ == "__main__":
    main()
