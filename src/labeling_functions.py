"""Fix-grounded labeling functions. Report-side signals are for comparison only."""

import re


CONC = re.compile(
    r"(race condition|data ?race|\bdead ?lock(s|ed|ing)?\b|"
    r"synchroniz(e|ed|ation)|acquire[sd]? (a |the )?lock|lock contention|"
    r"concurrent modification|\bvolatile\b|atomic(ity|ally)?|"
    r"reentrant ?lock|thread[- ]?safe(ty)?|ExecutorService|thread ?pool|"
    r"happens.before|non-thread-safe)",
    re.I,
)
MEM = re.compile(
    r"(memory leak|out ?of ?memory|\bOOM\b|null ?pointer ?"
    r"(exception|dereference)|\bNPE\b|resource leak|unclosed "
    r"(stream|resource|connection|channel)|buffer (over|under)flow|"
    r"double[- ]?(free|release)|reference count|fail(ed|s|ing)? to "
    r"(close|release|dispose)|leak detector|ByteBuf)",
    re.I,
)
EXC_CONC = re.compile(
    r"\b(ConcurrentModificationException|RejectedExecutionException|"
    r"TimeoutException|InterruptedException)\b"
)
EXC_MEM = re.compile(
    r"\b(OutOfMemoryError|NullPointerException|StackOverflowError|"
    r"BufferOverflowException|BufferUnderflowException)\b"
)
_MERGE = re.compile(r"^\s*merge (pull request|branch|remote)", re.I)
_SRC = re.compile(r"\.(java|kt|scala|cc|cpp|c|h|cs|py|js|ts|go)$", re.I)
_NONCODE_DIR = re.compile(
    r"(^|/)(docs?|site|\.github|\.test-infra)/|"
    r"(^|/)(pom\.xml|license|readme)",
    re.I,
)
_ISSUE = re.compile(r"#\d+")


def _commit_msg(issue):
    return " ".join(
        (commit.get("commitMessage") or "")
        for commit in (issue.get("commitsDetails") or [])
    )


def _changed_paths(issue):
    paths = []
    for commit in issue.get("commitsDetails") or []:
        for stat in commit.get("commitGitStats") or []:
            if stat.get("filePath"):
                paths.append(stat["filePath"])
        for stat in commit.get("commitSpoonAstDiffStats") or []:
            if stat.get("spoonFilePath"):
                paths.append(stat["spoonFilePath"])
    return " ".join(paths)


def _changed_methods(issue):
    methods = []
    for commit in issue.get("commitsDetails") or []:
        for stat in commit.get("commitSpoonAstDiffStats") or []:
            for method in stat.get("spoonMethods") or []:
                if method.get("spoonMethodName"):
                    methods.append(method["spoonMethodName"])
    return " ".join(methods)


def is_real_bug_fix(issue):
    """Keep fixes changing at least one non-test source file."""
    if _MERGE.search(_commit_msg(issue) or ""):
        return False
    source_paths = [
        path
        for path in _changed_paths(issue).split()
        if _SRC.search(path)
        and "test" not in path.lower()
        and not _NONCODE_DIR.search(path)
    ]
    return len(source_paths) >= 1


def is_focused_fix(issue):
    """Keep non-merge, single-issue, bounded-size source fixes."""
    message = _commit_msg(issue)
    if re.search(r"\bmerge (pull request|branch|remote|from)\b", message, re.I):
        return False
    if len(set(_ISSUE.findall(message))) > 2:
        return False
    if len(set(_changed_paths(issue).split())) > 20:
        return False
    return is_real_bug_fix(issue)


def _decide(text):
    concurrency = bool(CONC.search(text))
    memory = bool(MEM.search(text))
    if concurrency and not memory:
        return "concurrency"
    if memory and not concurrency:
        return "memory"
    return None


def lf_commit_keywords(issue):
    return _decide(_commit_msg(issue))


def lf_changed_paths(issue):
    return _decide(_changed_paths(issue))


def lf_changed_methods(issue):
    return _decide(_changed_methods(issue))


def lf_exception_type(issue):
    text = (
        (issue.get("title") or "")
        + " "
        + (issue.get("body") or "")
        + " "
        + _commit_msg(issue)
    )
    if EXC_CONC.search(text):
        return "concurrency"
    if EXC_MEM.search(text):
        return "memory"
    return None


def lf_report_keywords(issue, report_conc, report_mem):
    text = (issue.get("title") or "") + " " + (issue.get("body") or "")
    concurrency = bool(report_conc.search(text))
    memory = bool(report_mem.search(text))
    if concurrency and not memory:
        return "concurrency"
    if memory and not concurrency:
        return "memory"
    return None


def fix_signal_present(issue):
    return any(function(issue) is not None for function in FIX_LFS)


FIX_LFS = [
    lf_commit_keywords,
    lf_changed_paths,
    lf_changed_methods,
    lf_exception_type,
]
