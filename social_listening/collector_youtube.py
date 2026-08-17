from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from social_listening.collector_base import BaseCollector
from social_listening.utils import normalize_text


class YouTubeCollector(BaseCollector):
    platform_name = "youtube"

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        super().__init__(keywords, output_path, config)
        self.api_key = os.environ.get("YOUTUBE_API_KEY") or self.config.get("api_key")
        self.search_max_results = int(self.config.get("search_max_results", 5))
        self.comments_max_results = int(self.config.get("comments_max_results", 20))

    def collect(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            print("YouTube API Key not provided. Skipping YouTube live query.")
            return []

        query = " OR ".join(self.keywords)
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(self.search_max_results, 25),
            "key": self.api_key,
        }

        try:
            search_response = requests.get(search_url, params=search_params, timeout=30)
            search_response.raise_for_status()
            search_data = search_response.json()
            videos = [item for item in search_data.get("items", []) if item.get("id", {}).get("kind") == "youtube#video"]
        except Exception as e:
            print(f"YouTube search note: {e}")
            videos = []
        results: List[Dict[str, Any]] = []

        for video in videos:
            video_id = video["id"]["videoId"]
            snippet = video["snippet"]
            comments = self._fetch_comments(video_id)
            results.append({
                "id": video_id,
                "platform": "youtube",
                "query": query,
                "video_title": normalize_text(snippet.get("title")),
                "video_description": normalize_text(snippet.get("description")),
                "video_channel": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "comments": comments,
            })
        # Apply exclude_keywords filter - remove political poll content
        return self.filter_items(results, title_keys=["video_title", "video_description"])

    def _fetch_comments(self, video_id: str) -> List[Dict[str, Any]]:
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(self.comments_max_results, 100),
            "textFormat": "plainText",
            "key": self.api_key,
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        comment_items: List[Dict[str, Any]] = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = normalize_text(snippet.get("textDisplay"))
            comment_items.append({
                "comment_id": item.get("id"),
                "author": snippet.get("authorDisplayName"),
                "published_at": snippet.get("publishedAt"),
                "like_count": snippet.get("likeCount"),
                "text": text,
                "comment_url": f"https://www.youtube.com/watch?v={video_id}&lc={item.get('id')}",
            })
        return comment_items
