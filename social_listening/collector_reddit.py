from __future__ import annotations

import os
from typing import Any, Dict, List

import praw

from social_listening.collector_base import BaseCollector
from social_listening.utils import normalize_text


class RedditCollector(BaseCollector):
    platform_name = "reddit"

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        super().__init__(keywords, output_path, config)
        self.client_id = os.environ.get("REDDIT_CLIENT_ID") or self.config.get("client_id")
        self.client_secret = os.environ.get("REDDIT_CLIENT_SECRET") or self.config.get("client_secret")
        self.user_agent = os.environ.get("REDDIT_USER_AGENT") or self.config.get("user_agent", "social-listening-bot/0.1")
        if not self.client_id or not self.client_secret:
            raise ValueError("Reddit credentials are required via environment or config")
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        )
        self.max_results = int(self.config.get("max_results", 100))
        self.comments_max_results = int(self.config.get("comments_max_results", 20))
        self.subreddits = self.config.get("subreddits", ["all"])

    def collect(self) -> List[Dict[str, Any]]:
        query = " OR ".join([f'"{normalize_text(keyword)}"' for keyword in self.keywords])
        results: List[Dict[str, Any]] = []

        subreddit_query = "+".join(self.subreddits) if self.subreddits else "all"
        subreddit = self.reddit.subreddit(subreddit_query)
        for submission in subreddit.search(query, limit=self.max_results):
            submission.comments.replace_more(limit=0)
            comments: List[Dict[str, Any]] = []
            for comment in submission.comments.list()[: self.comments_max_results]:
                comments.append({
                    "comment_id": comment.id,
                    "author": str(comment.author) if comment.author else None,
                    "body": normalize_text(comment.body),
                    "created_utc": comment.created_utc,
                    "score": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}",
                })

            results.append({
                "id": submission.id,
                "platform": "reddit",
                "query": query,
                "title": normalize_text(submission.title),
                "selftext": normalize_text(submission.selftext),
                "subreddit": submission.subreddit.display_name,
                "author": str(submission.author) if submission.author else None,
                "created_utc": submission.created_utc,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "url": submission.url,
                "permalink": f"https://reddit.com{submission.permalink}",
                "comments": comments,
            })
        return results
