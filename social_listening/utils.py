from __future__ import annotations

import re
from typing import Dict, Iterable, List

from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0


def normalize_keyword(keyword: str) -> str:
    text = keyword.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_x_query(keywords: Iterable[str], include_retweets: bool = False) -> str:
    terms = []
    for keyword in keywords:
        kw = normalize_keyword(keyword)
        if " " in kw:
            terms.append(f'"{kw}"')
        else:
            terms.append(kw)
    query = " OR ".join(terms)
    if not include_retweets:
        query += " -is:retweet"
    return query


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "und"


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_search_query(keywords: Iterable[str], operator: str = "OR", quote_phrases: bool = True) -> str:
    terms: List[str] = []
    op = operator.strip().upper() if isinstance(operator, str) else "OR"
    if op not in {"AND", "OR"}:
        op = "OR"

    for keyword in keywords:
        text = normalize_keyword(keyword)
        if not text:
            continue
        if quote_phrases and " " in text:
            terms.append(f'"{text}"')
        else:
            terms.append(text)

    return f" {op} ".join(terms)
