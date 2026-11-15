"""Mask selection keywords to measure performance beyond the shortcut."""

import re
import runpy
from pathlib import Path


CONST = Path("data/raw/keywordSearch/constants.py")


def load_selection_keywords():
    """Load exactly the concurrency and memory regexes used by the baseline."""
    values = runpy.run_path(str(CONST))
    keywords = list(values["KEYWORDS_CONCURRENCY_RE"]) + list(
        values["KEYWORDS_MEMORY_RE"]
    )
    print(
        f"loaded {len(keywords)} selection regexes from the C/M lexicon:"
    )
    print(keywords)
    pattern = "|".join(f"(?:{keyword})" for keyword in keywords)
    return keywords, re.compile(pattern, re.I)


def mask(text, regex, token="<KW>"):
    return regex.sub(token, text or "")
