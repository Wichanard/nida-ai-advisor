from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from social_listening.storage import write_jsonl

# Configure logger
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger = logging.getLogger("NIDA_SocialListening")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s: %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)


class BaseCollector(ABC):
    platform_name: str

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        self.keywords = keywords
        self.output_path = Path(output_path)
        self.config = config or {}
        self.exclude_keywords: List[str] = [kw.lower() for kw in self.config.get("exclude_keywords", [])]
        self.logger = logger

    def is_excluded(self, text: str) -> bool:
        """Return True if the text contains any exclude keyword (case-insensitive)."""
        if not self.exclude_keywords or not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.exclude_keywords)

    def filter_items(self, items: List[Dict[str, Any]], title_keys: List[str] | None = None) -> List[Dict[str, Any]]:
        """Filter out items whose title/body matches any exclude keyword."""
        if not self.exclude_keywords:
            return items
        keys = title_keys or ["title", "thread_title", "video_title", "description", "thread_body", "query"]
        filtered: List[Dict[str, Any]] = []
        for item in items:
            combined = " ".join(str(item.get(k, "")) for k in keys)
            if not self.is_excluded(combined):
                filtered.append(item)
        self.logger.info(f"[{self.platform_name}] Filtered {len(items) - len(filtered)} noise items. Remaining: {len(filtered)}")
        return filtered

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=False)
    def fetch_url(self, url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Optional[requests.Response]:
        """Fetch URL with exponential backoff retry and random rate-limiting delay."""
        time.sleep(random.uniform(0.5, 1.5))
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            self.logger.warning(f"[{self.platform_name}] HTTP Request warning for {url}: {e}")
            raise

    @abstractmethod
    def collect(self) -> List[Dict[str, Any]]:
        ...

    def save(self, items: Iterable[Dict[str, Any]]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        items_list = list(items)
        write_jsonl(self.output_path, items_list, append=True)
        self.logger.info(f"[{self.platform_name}] Saved/Appended {len(items_list)} items to {self.output_path}")
