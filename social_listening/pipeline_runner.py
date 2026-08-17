"""
social_listening/pipeline_runner.py
Enterprise Automated Data Pipeline (ETL) & Spam-Filtered Ingestion Runner for NIDA.
Handles Automated Batch Fetching, Spam/Bot Filtering, Sentiment Enrichment, and SQLite Storage.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.models.database import ingest_social_mentions, get_system_stats
from social_listening.collector_news import NewsCollector
from social_listening.collector_pantip import PantipCollector
from social_listening.collector_youtube import YouTubeCollector
from social_listening.analyzer import analyze_sentiment_and_intent
from social_listening.utils import normalize_text


SPAM_PATTERNS = [
    r"บาคาร่า|สล็อต|เว็บพนัน|แทงบอล|คาสิโน|pgslot",
    r"เงินกู้|ปล่อยกู้|กู้เงินด่วน|สินเชื่อดอกเบี้ยต่ำ",
    r"สมัครงานรายได้เสริม|กดรับออเดอร์|ทำงานออนไลน์วันละ",
    r"แจกฟรี.*เครดิต",
]

SPAM_REGEX = [re.compile(p, re.IGNORECASE) for p in SPAM_PATTERNS]


def is_spam_or_noise(text: str) -> bool:
    """Detect promotional spam, gambling bots, or irrelevant noise."""
    if not text or len(text.strip()) < 5:
        return True
    for pattern in SPAM_REGEX:
        if pattern.search(text):
            return True
    return False


class NIDADataPipelineRunner:
    """Automated ETL Orchestrator for NIDA Social Listening Warehouse."""

    @classmethod
    def run_full_pipeline(
        cls,
        max_results_per_source: int = 25,
        target_platforms: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Execute full ETL run across Pantip, News, and YouTube with deduplication and spam filtering."""
        platforms = target_platforms or ["pantip", "news"]
        base_dir = Path(__file__).resolve().parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        raw_items: List[Dict[str, Any]] = []
        stats: Dict[str, int] = {"fetched": 0, "spam_dropped": 0, "ingested": 0}

        # 1. Extract from Sources
        if "pantip" in platforms:
            try:
                p_col = PantipCollector(
                    keywords=["นิด้า ปริญญาโท", "นิด้า ปริญญาเอก", "NIDA MBA", "เรียนต่อนิด้า"],
                    output_path=str(data_dir / "comments_pantip.jsonl"),
                    config={"max_results": max_results_per_source},
                )
                p_items = p_col.collect()
                raw_items.extend(p_items)
            except Exception as e:
                print(f"Pantip ETL extraction note: {e}")

        if "news" in platforms:
            try:
                n_col = NewsCollector(
                    keywords=["นิด้า ปริญญาโท", "นิด้า ปริญญาเอก", "รับสมัคร ป.โท นิด้า"],
                    output_path=str(data_dir / "comments_news.jsonl"),
                    config={"max_results": max_results_per_source},
                )
                n_items = n_col.collect()
                raw_items.extend(n_items)
            except Exception as e:
                print(f"News ETL extraction note: {e}")

        if "youtube" in platforms and os.environ.get("YOUTUBE_API_KEY"):
            try:
                y_col = YouTubeCollector(
                    keywords=["นิด้า ปริญญาโท", "NIDA Open House", "รีวิว ป.โท นิด้า"],
                    output_path=str(data_dir / "comments_youtube.jsonl"),
                    config={"search_max_results": 5},
                )
                y_items = y_col.collect()
                raw_items.extend(y_items)
            except Exception as e:
                print(f"YouTube ETL extraction note: {e}")

        stats["fetched"] = len(raw_items)

        # 2. Transform: Cleanse, Filter Spam, and Enrich Sentiment
        clean_items: List[Dict[str, Any]] = []
        for item in raw_items:
            title = normalize_text(item.get("title") or item.get("video_title", ""))
            comments = item.get("comments", [])
            
            # Check title spam
            if is_spam_or_noise(title) and not comments:
                stats["spam_dropped"] += 1
                continue

            filtered_comments: List[Dict[str, Any]] = []
            for c in comments:
                txt = normalize_text(c.get("text", ""))
                if is_spam_or_noise(txt):
                    stats["spam_dropped"] += 1
                    continue
                # Enrich with sentiment
                res = analyze_sentiment_and_intent(txt)
                c["sentiment"] = res["sentiment"]
                c["intent"] = res["intent"]
                filtered_comments.append(c)

            item["comments"] = filtered_comments
            clean_items.append(item)

        # 3. Load: Ingest into SQLite Warehouse with Deduplication
        new_count = ingest_social_mentions(clean_items)
        stats["ingested"] = new_count

        total_db_stats = get_system_stats()
        return {
            "status": "success",
            "batch_stats": stats,
            "warehouse_total_mentions": total_db_stats.get("total_mentions", 0),
        }
