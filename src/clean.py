"""Non-destructive text cleaning and diagnostic-text extraction."""

import re
import unicodedata

import pandas as pd


CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
INDENT_CODE = re.compile(r"(?:^(?: {4}|\t).*(?:\n|$))+", re.MULTILINE)
STACK_FRAME = re.compile(
    r"^[ \t]*at\s+[\w.$<>]+\([^()\n]*\)[ \t]*$", re.MULTILINE
)
EXC_LINE = re.compile(
    r"^.*?\b[\w.]*(?:Exception|Error)\b.*$", re.MULTILINE
)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
MENTION = re.compile(r"(?<!\w)@[A-Za-z0-9_-]+")
REF = re.compile(r"(?<!\w)#\d+")
WS = re.compile(r"\s+")


def clean_text(raw):
    if not isinstance(raw, str):
        return {
            "clean": "",
            "code": "",
            "stack": "",
            "has_code": False,
            "has_stack": False,
        }

    text = unicodedata.normalize("NFKC", raw)
    text = HTML_COMMENT.sub(" ", text)

    stack_frames = STACK_FRAME.findall(text)
    text = STACK_FRAME.sub(" ", text)
    exception_lines = EXC_LINE.findall(text)
    text = EXC_LINE.sub(" ", text)

    code_blocks = CODE_FENCE.findall(text)
    text = CODE_FENCE.sub(" ", text)
    indented_code = INDENT_CODE.findall(text)
    text = INDENT_CODE.sub(" ", text)

    text = MD_IMAGE.sub(" ", text)
    text = URL.sub("<URL>", text)
    text = SHA.sub("<SHA>", text)
    text = MENTION.sub("<USER>", text)
    text = REF.sub("<REF>", text)
    text = WS.sub(" ", text).strip()

    code = " ".join(code_blocks + indented_code).strip()
    stack = " ".join(stack_frames + exception_lines).strip()
    return {
        "clean": text,
        "code": code,
        "stack": stack,
        "has_code": bool(code),
        "has_stack": bool(stack),
    }


def add_clean_columns(df, src_col, prefix):
    values = df[src_col].apply(clean_text)
    df[f"{prefix}_clean"] = values.map(lambda value: value["clean"])
    df[f"{prefix}_code"] = values.map(lambda value: value["code"])
    df[f"{prefix}_stack"] = values.map(lambda value: value["stack"])
    df[f"{prefix}_has_code"] = values.map(lambda value: value["has_code"])
    df[f"{prefix}_has_stack"] = values.map(lambda value: value["has_stack"])
    df[f"{prefix}_len_chars"] = df[f"{prefix}_clean"].str.len()
    df[f"{prefix}_len_tokens"] = (
        df[f"{prefix}_clean"].str.split().apply(len)
    )
    return df
