from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from social_listening.analyzer import analyze_sentiment_and_intent


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    return items


def write_jsonl(path: Path, items: Iterable[Dict[str, Any]], append: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_items: List[Dict[str, Any]] = read_jsonl(path) if append else []

    seen = set()
    combined_items: List[Dict[str, Any]] = []

    for item in list(existing_items) + list(items):
        text = item.get("text") or item.get("thread_title") or item.get("title") or ""
        if text and ("sentiment" not in item or "intent" not in item):
            analysis = analyze_sentiment_and_intent(text)
            item.setdefault("sentiment", analysis["sentiment"])
            item.setdefault("intent", analysis["intent"])

        item_id = str(item.get("id") or item.get("url") or item.get("comment_id") or text).strip()
        if item_id and item_id not in seen:
            seen.add(item_id)
            combined_items.append(item)

    with path.open("w", encoding="utf-8") as fh:
        for item in combined_items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def dedupe_by_id(items: List[Dict[str, Any]], id_key: str = "id") -> List[Dict[str, Any]]:
    seen: set[str] = set()
    unique_items: List[Dict[str, Any]] = []
    for item in items:
        item_id = str(item.get(id_key, ""))
        if item_id and item_id not in seen:
            seen.add(item_id)
            unique_items.append(item)
    return unique_items


def dedupe_by_text(items: List[Dict[str, Any]], text_key: str = "text") -> List[Dict[str, Any]]:
    seen: set[str] = set()
    unique_items: List[Dict[str, Any]] = []
    for item in items:
        text = str(item.get(text_key, "")).strip()
        if text and text not in seen:
            seen.add(text)
            unique_items.append(item)
    return unique_items
