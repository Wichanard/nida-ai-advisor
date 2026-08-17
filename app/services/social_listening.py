"""
app/services/social_listening.py
Bridges the social_listening module to the app layer.
Provides summarize_comments() using the upgraded Thai NLP analyzer.
"""
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parents[2]


def summarize_comments(jsonl_dir: str | None = None, limit: int = 100) -> Dict[str, Any]:
    """
    Load collected JSONL files and return a full social listening summary
    using the Thai NLP analyzer (Word Cloud, Sentiment, Intent).
    """
    from social_listening.analyzer import summarize_dataset
    from social_listening.storage import read_jsonl
    from social_listening.utils import normalize_text

    data_dirs = [
        BASE_DIR / "social_listening" / "data",
        BASE_DIR / "data",
    ]
    if jsonl_dir:
        data_dirs.insert(0, Path(jsonl_dir))

    comments: List[Dict[str, Any]] = []
    seen: set = set()

    for data_dir in data_dirs:
        if not data_dir.exists():
            continue
        for filepath in data_dir.glob("*.jsonl"):
            try:
                for item in read_jsonl(filepath):
                    platform = item.get("platform", "unknown")
                    sub_comments = item.get("comments", [])
                    if isinstance(sub_comments, list):
                        for c in sub_comments:
                            txt = normalize_text(c.get("text"))
                            if txt and txt not in seen:
                                seen.add(txt)
                                comments.append({
                                    "platform": platform,
                                    "text": txt,
                                    "author": c.get("author", ""),
                                    "url": c.get("comment_url") or c.get("url") or item.get("url", ""),
                                    "published_at": c.get("published_at", ""),
                                })
                    else:
                        txt = normalize_text(item.get("text"))
                        if txt and txt not in seen:
                            seen.add(txt)
                            comments.append({
                                "platform": platform,
                                "text": txt,
                                "author": item.get("author", ""),
                                "url": item.get("url", ""),
                                "published_at": item.get("published_at", ""),
                            })
            except Exception:
                continue

    sample = comments[:limit]
    summary = summarize_dataset(sample)
    summary["sample_comments"] = sample
    return summary
