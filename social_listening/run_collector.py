from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from social_listening.collector_x import TwitterXCollector
from social_listening.collector_youtube import YouTubeCollector
from social_listening.collector_reddit import RedditCollector
from social_listening.collector_pantip import PantipCollector
from social_listening.collector_news import NewsCollector
from social_listening.collector_crowdtangle import CrowdTangleCollector
from social_listening.storage import write_jsonl


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run social listening collector")
    parser.add_argument("--platform", choices=["x", "youtube", "reddit", "pantip", "news", "crowdtangle"], required=True)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--output", default="data/comments_x.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path) if config_path.exists() else {}
    keywords = config.get("keywords", [])
    exclude_keywords = config.get("exclude_keywords", [])
    platform_config = config.get("platforms", {}).get(args.platform, {})
    # Merge top-level exclude_keywords into platform config so BaseCollector can filter results
    if exclude_keywords:
        platform_config = {**platform_config, "exclude_keywords": exclude_keywords}

    if args.platform == "x":
        collector = TwitterXCollector(keywords, args.output, platform_config)
    elif args.platform == "youtube":
        collector = YouTubeCollector(keywords, args.output, platform_config)
    elif args.platform == "reddit":
        collector = RedditCollector(keywords, args.output, platform_config)
    elif args.platform == "pantip":
        collector = PantipCollector(keywords, args.output, platform_config)
    elif args.platform == "news":
        collector = NewsCollector(keywords, args.output, platform_config)
    elif args.platform == "crowdtangle":
        collector = CrowdTangleCollector(keywords, args.output, platform_config)
    else:
        raise ValueError("Unsupported platform")

    if args.dry_run:
        print("Query:", collector.config.get("query") or collector.config.get("query_override") or collector.keywords)
        return

    items = collector.collect()
    collector.save(items)
    print(f"Saved {len(items)} items to {args.output}")

    # Ingest into SQLite database warehouse
    try:
        from app.models.database import ingest_social_mentions
        inserted = ingest_social_mentions(items, platform_override=args.platform)
        print(f"Indexed {inserted} items into Enterprise SQLite Warehouse.")
    except Exception as e:
        print(f"Database ingestion note: {e}")


if __name__ == "__main__":
    main()
