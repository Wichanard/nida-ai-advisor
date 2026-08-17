from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from social_listening.collector_base import BaseCollector
from social_listening.utils import build_search_query, normalize_text


class CrowdTangleCollector(BaseCollector):
    platform_name = "crowdtangle"

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        super().__init__(keywords, output_path, config)
        self.api_token = os.environ.get("CROWDTANGLE_API_TOKEN") or self.config.get("api_token")
        if not self.api_token:
            raise ValueError("CrowdTangle API token is required via CROWDTANGLE_API_TOKEN or config['api_token']")
        self.max_results = int(self.config.get("max_results", 25))
        self.list_id = self.config.get("list_id")
        self.account_ids = self.config.get("account_ids", [])
        self.platforms = self.config.get("platforms", [])
        self.include_history = bool(self.config.get("include_history", False))
        self.query_operator = self.config.get("query_operator", "OR")

    def collect(self) -> List[Dict[str, Any]]:
        query = self._build_query()
        url = "https://api.crowdtangle.com/posts"
        params: Dict[str, Any] = {
            "token": self.api_token,
            "count": min(self.max_results, 100),
            "sortBy": self.config.get("sort_by", "date"),
        }
        if query:
            params["searchTerm"] = query
        if self.list_id:
            params["listId"] = self.list_id
        if self.account_ids:
            params["accountId"] = ",".join(map(str, self.account_ids))
        if self.platforms:
            params["platform"] = ",".join(self.platforms)
        if self.include_history:
            params["includeHistory"] = "true"

        results: List[Dict[str, Any]] = []

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        for post in data.get("result", {}).get("posts", [])[: self.max_results]:
            results.append({
                "id": post.get("id"),
                "platform": "crowdtangle",
                "query": query,
                "date": post.get("date"),
                "account_name": post.get("account", {}).get("name"),
                "account_type": post.get("account", {}).get("type"),
                "platform_type": post.get("platform"),
                "message": normalize_text(post.get("message")),
                "title": normalize_text(post.get("title")),
                "stats": post.get("statistics"),
                "url": post.get("url"),
                "tags": post.get("tags"),
                "links": post.get("links"),
                "language": post.get("language"),
            })

        return results

    def _build_query(self) -> str:
        return build_search_query(self.keywords, operator=self.query_operator, quote_phrases=True)
