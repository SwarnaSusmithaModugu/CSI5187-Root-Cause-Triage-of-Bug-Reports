"""Recover issue comment threads for the gold reports through the GitHub REST API.

Usage (run on your machine or Colab, not in a locked-down sandbox):
    export GITHUB_TOKEN=...            # personal access token, read-only public access is enough
    python fetch_comments.py --gold data/gold_urls.csv --out data/comments

gold_urls.csv needs a 'url' column. If it also has fix_date and closed columns, a coverage
report is written using the same pre-fix cut that load_projects.attach_comments applies.

Raw API responses are saved untouched, one json file per issue, so the pull can be audited.
"""
import argparse, json, os, re, sys, time
from pathlib import Path
import pandas as pd
import requests

API = "https://api.github.com"
URL_RE = re.compile(r"github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)")
# accounts that post automated text. extend after looking at the raw data
BOT_LOGINS = {"codecov-io", "codecov", "spring-projects-issues", "stale", "dependabot"}

def parse_url(url):
    m = URL_RE.search(url)
    if not m:
        raise ValueError(f"not an issue url: {url}")
    return m.group(1), m.group(2), int(m.group(3))

def is_bot(user):
    if not user:
        return True  # deleted account, no usable authorship
    login = (user.get("login") or "").lower()
    return user.get("type") == "Bot" or login.endswith("[bot]") or login in BOT_LOGINS

def get_page(session, url, params=None, tries=5):
    for attempt in range(tries):
        r = session.get(url, params=params, timeout=30)
        remaining = r.headers.get("X-RateLimit-Remaining")
        if r.status_code in (403, 429) and remaining == "0":
            wait = max(int(r.headers.get("X-RateLimit-Reset", 0)) - int(time.time()), 1) + 2
            print(f"rate limited, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code in (500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        return r
    return r

def fetch_issue_comments(session, owner, repo, number):
    """Returns (status, list_of_raw_comments). status: ok, missing (404/410), error."""
    url = f"{API}/repos/{owner}/{repo}/issues/{number}/comments"
    out, params = [], {"per_page": 100}
    while url:
        r = get_page(session, url, params)
        if r.status_code in (404, 410):
            return "missing", []
        if r.status_code != 200:
            return f"error_{r.status_code}", out
        out.extend(r.json())
        url = r.links.get("next", {}).get("url")
        params = None  # the next link already carries the query
    return "ok", out

def run(gold_path, out_dir):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("set GITHUB_TOKEN first")
    out_dir = Path(out_dir); (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    gold = pd.read_csv(gold_path)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                      "X-GitHub-Api-Version": "2022-11-28"})
    rows, status = [], {}
    for k, url in enumerate(gold["url"], 1):
        owner, repo, n = parse_url(url)
        raw_path = out_dir / "raw" / f"{owner}__{repo}__{n}.json"
        if raw_path.exists():                       # resume support
            st, comments = "ok", json.load(open(raw_path, encoding="utf-8"))
        else:
            st, comments = fetch_issue_comments(s, owner, repo, n)
            if st == "ok":
                json.dump(comments, open(raw_path, "w", encoding="utf-8"))
        status[url] = st
        for c in comments:
            rows.append({"url": url, "comment_text": c.get("body") or "",
                         "comment_created": c.get("created_at"),
                         "author": (c.get("user") or {}).get("login"),
                         "is_bot": is_bot(c.get("user"))})
        if k % 25 == 0:
            print(f"{k}/{len(gold)} fetched", file=sys.stderr)
    com = pd.DataFrame(rows, columns=["url", "comment_text", "comment_created", "author", "is_bot"])
    com.to_csv(out_dir / "comments_all.csv", index=False)
    pd.Series(status, name="status").rename_axis("url").to_csv(out_dir / "fetch_status.csv")
    coverage(gold, com, status, out_dir)

def coverage(gold, com, status, out_dir):
    st = pd.Series(status)
    lines = [f"issues requested: {len(gold)}",
             f"fetch ok: {(st == 'ok').sum()}  missing (404/410): {(st == 'missing').sum()}  "
             f"other errors: {(~st.isin(['ok', 'missing'])).sum()}",
             f"issues with any comment: {com['url'].nunique()}",
             f"comments total: {len(com)}  from bots: {int(com['is_bot'].sum())}"]
    if {"fix_date", "closed"} <= set(gold.columns):
        sys.path.insert(0, str(Path(__file__).parent))
        from load_projects import attach_comments
        human = com[~com["is_bot"]]
        merged = attach_comments(gold, human)
        n_pre = int((merged["comments"] != "").sum())
        lines.append(f"issues with >=1 human comment before the fix: {n_pre} of {len(gold)} "
                     f"({100 * n_pre / len(gold):.0f}%)")
        merged[["url", "comments"]].to_csv(Path(out_dir) / "comments_prefix.csv", index=False)
    text = "\n".join(lines)
    (Path(out_dir) / "coverage.txt").write_text(text + "\n", encoding="utf-8")
    print(text)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--out", default="data/comments")
    a = ap.parse_args()
    run(a.gold, a.out)
