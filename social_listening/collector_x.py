from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from social_listening.collector_base import BaseCollector
from social_listening.utils import build_x_query, normalize_text


class TwitterXCollector(BaseCollector):
    platform_name = "x"

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        super().__init__(keywords, output_path, config)
        self.bearer_token = os.environ.get("TWITTER_BEARER_TOKEN") or self.config.get("bearer_token")
        if not self.bearer_token:
            raise ValueError("Twitter/X bearer token is required via TWITTER_BEARER_TOKEN or config['bearer_token']")

    def collect(self) -> List[Dict[str, Any]]:
        query = build_x_query(self.keywords, include_retweets=self.config.get("include_retweets", False))
        max_results = self.config.get("max_results", 100)
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "id,text,author_id,created_at,lang,public_metrics,source",
            "expansions": "author_id"
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        tweets = payload.get("data", [])
        users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
        results: List[Dict[str, Any]] = []
        for tweet in tweets:
            text = normalize_text(tweet.get("text"))
            results.append({
                "id": tweet.get("id"),
                "platform": "x",
                "query": query,
                "text": text,
                "language": tweet.get("lang"),
                "author_id": tweet.get("author_id"),
                "author_username": users.get(tweet.get("author_id"), {}).get("username"),
                "created_at": tweet.get("created_at"),
                "public_metrics": tweet.get("public_metrics"),
                "source": tweet.get("source"),
                "url": f"https://twitter.com/{users.get(tweet.get('author_id'), {}).get('username', 'unknown')}/status/{tweet.get('id')}"
            })
        return results
