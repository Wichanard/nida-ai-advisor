from __future__ import annotations

import re
import urllib.parse
import warnings
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from social_listening.collector_base import BaseCollector
from social_listening.utils import normalize_text


class PantipCollector(BaseCollector):
    platform_name = "pantip"

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        super().__init__(keywords, output_path, config)
        self.max_results = int(self.config.get("max_results", 25))
        self.max_comments_per_thread = int(self.config.get("max_comments_per_thread", 15))
        self.headers = {
            "User-Agent": self.config.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
            "X-Requested-With": "XMLHttpRequest",
        }

    def collect(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        search_queries = [
            "site:pantip.com นิด้า ปริญญาโท",
            "site:pantip.com นิด้า ปริญญาเอก",
            "site:pantip.com นิด้า MBA",
            "site:pantip.com เรียนต่อ นิด้า",
            "site:pantip.com นิด้า DADS",
            "site:pantip.com นิด้า HROD",
        ]
        seen_urls = set()

        for q in search_queries:
            try:
                rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=th&gl=TH&ceid=TH:th"
                response = requests.get(rss_url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    continue
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    soup = BeautifulSoup(response.content, "html.parser")

                for item in soup.find_all("item"):
                    title = normalize_text(item.title.text if item.title else "")
                    clean_title = title.replace("- Pantip", "").strip()
                    link = item.link.text if item.link else ""
                    if not link and item.find("guid"):
                        link = item.find("guid").text.strip()

                    if clean_title and link not in seen_urls:
                        seen_urls.add(link)
                        pub_date = item.pubDate.text if item.find("pubDate") else ""
                        topic_id = self._extract_topic_id(link)

                        comments_list: List[Dict[str, Any]] = []
                        if topic_id:
                            comments_list = self._fetch_pantip_ajax_comments(topic_id, link)

                        if not comments_list:
                            comments_list = [
                                {
                                    "author": "สมาชิก Pantip",
                                    "text": f"กระทู้: {clean_title}",
                                    "source_url": link,
                                    "published_at": pub_date,
                                }
                            ]

                        results.append({
                            "id": topic_id or link or clean_title,
                            "platform": "pantip",
                            "query": q,
                            "thread_title": clean_title,
                            "thread_body": clean_title,
                            "url": link,
                            "published_at": pub_date,
                            "comments": comments_list,
                        })
                    if len(results) >= self.max_results:
                        break
            except Exception as e:
                print(f"Pantip search warning for '{q}': {e}")
            if len(results) >= self.max_results:
                break

        return self.filter_items(results, title_keys=["thread_title", "thread_body"])

    def _extract_topic_id(self, url: str) -> Optional[str]:
        match = re.search(r"pantip\.com/topic/(\d+)", url)
        return match.group(1) if match else None

    def _fetch_pantip_ajax_comments(self, topic_id: str, thread_url: str) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        try:
            ajax_url = f"https://pantip.com/forum/topic/get_comment?topic_id={topic_id}&type=3"
            resp = requests.get(ajax_url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                raw_comments = data.get("comments", [])
                for item in raw_comments[: self.max_comments_per_thread]:
                    raw_msg = item.get("message", "")
                    clean_msg = normalize_text(BeautifulSoup(raw_msg, "html.parser").get_text())
                    if not clean_msg:
                        continue
                    author = item.get("user", {}).get("name", "สมาชิก Pantip")
                    created_at = item.get("data_time", {}).get("created_time", "")
                    comments.append({
                        "comment_id": item.get("comment_no"),
                        "author": author,
                        "text": clean_msg,
                        "published_at": created_at,
                        "source_url": f"{thread_url}#comment-{item.get('comment_no')}",
                    })
        except Exception as e:
            print(f"Pantip AJAX comment fetch warning for topic {topic_id}: {e}")

        return comments
