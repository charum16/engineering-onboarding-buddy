"""Tokenising helpers shared by BM25, the hashing embedder, guardrails and evaluation."""
from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset("""
a an and are as at be been but by can could did do does for from get got had has have how i if in into is
it its me my of on or our should so than that the their them then there these they this to was we were
what when where which who whom why will with would you your s t re ll ve d m about any much many
""".split())


def stem(tok: str) -> str:
    """Very light suffix stripping, enough to match day/days and carry/carried. Not a real stemmer."""
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 5 and tok.endswith("ing"):
        return tok[:-3]
    if len(tok) > 4 and tok.endswith("ed"):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize(text: str, drop_stopwords: bool = True) -> list[str]:
    toks = _TOKEN.findall(text.lower())
    if drop_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    return [stem(t) for t in toks]
