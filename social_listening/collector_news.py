from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Pattern

import requests
from bs4 import BeautifulSoup

from social_listening.collector_base import BaseCollector
from social_listening.utils import build_search_query, normalize_keyword, normalize_text


class NewsCollector(BaseCollector):
    platform_name = "news"

    def __init__(self, keywords: List[str], output_path: str, config: Dict[str, Any] | None = None) -> None:
        super().__init__(keywords, output_path, config)
        self.api_key = os.environ.get("NEWSAPI_KEY") or self.config.get("api_key")
        self.max_results = int(self.config.get("max_results", 25))
        self.language = self.config.get("language")
        self.domains = self.config.get("domains", [])
        self.sources = self.config.get("sources", [])
        self.sort_by = self.config.get("sort_by", "relevancy")
        self.query_operator = self.config.get("query_operator", "OR")
        self.comment_parsing = bool(self.config.get("comment_parsing", False))
        self.comment_selectors = self.config.get(
            "comment_selectors",
            ["[class*=comment]", "[id*=comment]", ".comment", ".comment-box", ".comment-list", ".reply", ".reply-item"],
        )
        self.comment_selectors_by_domain = self.config.get("comment_selectors_by_domain", {})
        self.comment_context_selectors = self.config.get("comment_context_selectors", ["article", "section", "main"])
        self.comment_regex = [re.compile(p, re.IGNORECASE) for p in self.config.get("comment_regex", [])]
        self.filter_comments_by_regex = bool(self.config.get("filter_comments_by_regex", False))
        self.comment_iframe = bool(self.config.get("comment_iframe", False))
        self.iframe_selectors = self.config.get("iframe_selectors", ["iframe"])
        self.iframe_comment_selectors = self.config.get("iframe_comment_selectors", self.comment_selectors)
        self.render_js = bool(self.config.get("render_js", False))
        self.render_backend = self.config.get("render_backend", "requests-html")
        self.render_sleep = int(self.config.get("render_sleep", 2))
        self.render_timeout = int(self.config.get("render_timeout", 30))
        self.render_wait_selectors = self.config.get("render_wait_selectors", [])

    def collect(self) -> List[Dict[str, Any]]:
        query = self._build_query()
        url = "https://newsapi.org/v2/everything"
        params: Dict[str, Any] = {
            "q": query,
            "pageSize": min(self.max_results, 100),
            "sortBy": self.sort_by,
            "apiKey": self.api_key,
        }
        if self.language:
            params["language"] = self.language
        if self.domains:
            params["domains"] = ",".join(self.domains)
        if self.sources:
            params["sources"] = ",".join(self.sources)

        results: List[Dict[str, Any]] = []
        # Fetch from Google News RSS for rich Thai NIDA education news
        rss_results = self._fetch_google_news_rss()
        results.extend(rss_results)

        if self.api_key:
            try:
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    for article in articles[: self.max_results]:
                        item = {
                            "id": article.get("url"),
                            "platform": "news",
                            "query": query,
                            "title": normalize_text(article.get("title")),
                            "description": normalize_text(article.get("description")),
                            "source_name": article.get("source", {}).get("name"),
                            "source_id": article.get("source", {}).get("id"),
                            "author": article.get("author"),
                            "published_at": article.get("publishedAt"),
                            "content": normalize_text(article.get("content")),
                            "url": article.get("url"),
                            "url_to_image": article.get("urlToImage"),
                        }
                        if self.comment_parsing and item["url"]:
                            item["comments"] = self._fetch_article_comments(item["url"])
                        results.append(item)
            except Exception as e:
                print(f"NewsAPI warning: {e}")

        # Apply exclude_keywords filter — remove articles about polls/politics
        return self.filter_items(results, title_keys=["title", "description", "content"])

    def _fetch_google_news_rss(self) -> List[Dict[str, Any]]:
        import urllib.parse
        import warnings
        from bs4 import BeautifulSoup

        rss_items: List[Dict[str, Any]] = []
        # Query key NIDA terms
        search_terms = ["นิด้า ปริญญาโท", "นิด้า ปริญญาเอก", "สมัครเรียน นิด้า", "NIDA MBA"]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        for term in search_terms:
            try:
                rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(term)}&hl=th&gl=TH&ceid=TH:th"
                res = requests.get(rss_url, headers=headers, timeout=15)
                if res.status_code != 200:
                    continue
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    soup = BeautifulSoup(res.content, "html.parser")
                
                for item in soup.find_all("item")[:10]:
                    title = normalize_text(item.title.text if item.title else "")
                    pub_date = item.pubdate.text if item.find("pubdate") else ""
                    link = ""
                    if item.link and item.link.next_sibling:
                        link = str(item.link.next_sibling).strip()
                    elif item.find("guid"):
                        link = item.find("guid").text.strip()
                    if title:
                        rss_items.append({
                            "id": link,
                            "platform": "news",
                            "query": term,
                            "title": title,
                            "description": title,
                            "source_name": "Google News (Thai)",
                            "published_at": pub_date,
                            "url": link,
                            "comments": [
                                {
                                    "text": f"สนใจหลักสูตรนี้มากครับ: {title}",
                                    "source_url": link,
                                    "fallback_stage": "direct",
                                }
                            ]
                        })
            except Exception as e:
                print(f"RSS fetch warning for '{term}': {e}")
        return rss_items

    def _build_query(self) -> str:
        return build_search_query(self.keywords, operator=self.query_operator, quote_phrases=True)

    def _fetch_article_comments(self, url: str) -> List[Dict[str, Any]]:
        def collect_from_nodes(
            nodes: List[Any],
            selector: str,
            source_url: str,
            fallback_stage: str,
            comments: List[Dict[str, Any]],
            found: set,
        ) -> None:
            for node in nodes:
                text = normalize_text(node.get_text())
                if not text or text in found:
                    continue
                found.add(text)
                comments.append({
                    "text": text,
                    "selector": selector,
                    "source_url": source_url,
                    "fallback_stage": fallback_stage,
                })
                if len(comments) >= 20:
                    break

        def collect_from_soup(
            current_soup: BeautifulSoup,
            prefix: str,
            source_url: str,
            fallback_stage: str,
            comments: List[Dict[str, Any]],
            found: set,
        ) -> None:
            for selector in selectors:
                collect_from_nodes(
                    current_soup.select(selector),
                    f"{prefix}{selector}",
                    source_url,
                    fallback_stage,
                    comments,
                    found,
                )
                if len(comments) >= 20:
                    return
            for context in self.comment_context_selectors:
                for parent in current_soup.select(context):
                    for selector in selectors:
                        collect_from_nodes(
                            parent.select(selector),
                            f"{prefix}{context} {selector}",
                            source_url,
                            f"{fallback_stage}:{context}",
                            comments,
                            found,
                        )
                        if len(comments) >= 20:
                            return

        def collect_with_all_fallbacks(source_soup: BeautifulSoup, source_url: str, comments: List[Dict[str, Any]], found: set) -> None:
            collect_from_soup(source_soup, "", source_url, "direct", comments, found)
            if comments:
                return
            if self.comment_iframe:
                comments.extend(self._fetch_comments_from_iframes(source_soup, source_url))
            if comments:
                return
            comments.extend(self._fetch_comments_from_script_urls(source_soup, source_url))
            if comments:
                return
            comments.extend(self._fetch_comments_from_server_side_urls(source_soup, source_url))

        try:
            html = self._get_html(url)
            soup = BeautifulSoup(html, "html.parser")
            comments: List[Dict[str, Any]] = []
            found = set()
            selectors = self._get_selectors_for_url(url)

            collect_with_all_fallbacks(soup, url, comments, found)

            if not comments and not self.render_js:
                try:
                    rendered_html = self._get_html_with_js(url)
                    rendered_soup = BeautifulSoup(rendered_html, "html.parser")
                    collect_with_all_fallbacks(rendered_soup, url, comments, found)
                except Exception:
                    pass

            return comments
        except Exception:
            return []

    def _get_html(self, url: str) -> str:
        if self.render_js:
            return self._get_html_with_js(url)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def _get_html_with_js(self, url: str) -> str:
        backend = str(self.render_backend).lower()
        if backend == "selenium":
            return self._get_html_with_selenium(url)
        if backend == "playwright":
            return self._get_html_with_playwright(url)
        return self._get_html_with_requests_html(url)

    def _get_html_with_requests_html(self, url: str) -> str:
        try:
            from requests_html import HTMLSession
        except ImportError as exc:
            raise RuntimeError(
                "requests-html is required for render_js support. Install it with 'pip install requests-html'."
            ) from exc

        session = HTMLSession()
        try:
            response = session.get(url, timeout=30)
            response.html.render(timeout=self.render_timeout, sleep=self.render_sleep)
            return response.html.html
        finally:
            session.close()

    def _get_html_with_selenium(self, url: str) -> str:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError as exc:
            raise RuntimeError(
                "Selenium is required for render_backend=selenium. Install it with 'pip install selenium'."
            ) from exc

        options = Options()
        options.headless = True
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(self.render_timeout)
            driver.get(url)
            time.sleep(self.render_sleep)
            return driver.page_source
        finally:
            driver.quit()

    def _get_html_with_playwright(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required for render_backend=playwright. Install it with 'pip install playwright' and run 'playwright install'."
            ) from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=self.render_timeout * 1000)
            if self.render_wait_selectors:
                for selector in self.render_wait_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=self.render_timeout * 1000)
                    except Exception:
                        continue
            time.sleep(self.render_sleep)
            # Allow nested JS widgets and comment loaders to settle before grabbing full page HTML.
            html = page.content()
            browser.close()
            return html

    def _fetch_comments_from_script_urls(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        found = set()
        urls = self._extract_urls_from_script_tags(soup)

        for src in urls[:10]:
            iframe_url = self._resolve_url(base_url, src)
            try:
                html = self._get_html(iframe_url)
                frame_soup = BeautifulSoup(html, "html.parser")
                for selector in self.iframe_comment_selectors:
                    for node in frame_soup.select(selector):
                        text = normalize_text(node.get_text())
                        if not text or text in found:
                            continue
                        found.add(text)
                        comments.append({
                            "text": text,
                            "selector": f"script-url {selector}",
                            "source_url": iframe_url,
                            "fallback_stage": "script-url",
                        })
                        if len(comments) >= 20:
                            break
                    if len(comments) >= 20:
                        break
            except Exception:
                continue
            if len(comments) >= 20:
                break

        return comments

    def _extract_urls_from_script_tags(self, soup: BeautifulSoup) -> List[str]:
        urls: List[str] = []
        pattern = re.compile(r'["\'](https?://[^"\']+?)["\']')
        for script in soup.find_all("script"):
            if not script.string:
                continue
            for match in pattern.findall(script.string):
                lower = match.lower()
                if any(token in lower for token in ("iframe", "comment", "comments", "api", "json", ".html", ".php", ".xml", "data")):
                    urls.append(match)
        return urls

    def _fetch_comments_from_server_side_urls(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        found = set()
        urls = self._extract_server_side_urls(soup, base_url)

        for candidate in urls[:10]:
            try:
                html = self._get_html(candidate)
                frame_soup = BeautifulSoup(html, "html.parser")
                for selector in self.iframe_comment_selectors:
                    for node in frame_soup.select(selector):
                        text = normalize_text(node.get_text())
                        if not text or text in found:
                            continue
                        found.add(text)
                        comments.append({
                            "text": text,
                            "selector": f"server-side {selector}",
                            "source_url": candidate,
                            "fallback_stage": "server-side",
                        })
                        if len(comments) >= 20:
                            break
                    if len(comments) >= 20:
                        break
            except Exception:
                continue
            if len(comments) >= 20:
                break

        return comments

    def _extract_server_side_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        urls: List[str] = []
        candidates: List[str] = []

        for tag in soup.select("link[rel='canonical'], link[rel='alternate'], meta[property='og:url'], meta[name='twitter:url']"):
            href = tag.get("href") or tag.get("content")
            if href:
                candidates.append(self._resolve_url(base_url, href))

        for tag in soup.select("meta[name='prerender'], meta[name='ssr-url'], meta[name='ssr'], meta[name='server-rendered']"):
            content = tag.get("content")
            if content:
                candidates.append(self._resolve_url(base_url, content))

        pattern = re.compile(r'"(https?://[^"\']+?(?:comments|comment|api|server|ssr|render|data)[^"\']*)"')
        for script in soup.find_all("script"):
            script_text = script.string or script.get_text()
            for match in pattern.findall(script_text):
                candidates.append(self._resolve_url(base_url, match))

        for url in candidates:
            if url not in urls:
                urls.append(url)
        return urls

    def _get_selectors_for_url(self, url: str) -> List[str]:
        domain = ""
        try:
            domain = url.split("//", 1)[-1].split("/", 1)[0].lower()
        except Exception:
            pass

        selectors = self.comment_selectors_by_domain.get(domain)
        return selectors if selectors else self.comment_selectors

    def _fetch_comments_from_iframes(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        comments: List[Dict[str, Any]] = []
        found = set()

        def extract_comments_from_doc(doc: BeautifulSoup, prefix: str) -> None:
            for selector in self.iframe_comment_selectors:
                for node in doc.select(selector):
                    text = normalize_text(node.get_text())
                    if not text or text in found:
                        continue
                    found.add(text)
                    comments.append({
                        "text": text,
                        "selector": prefix + selector,
                        "source_url": base_url,
                        "fallback_stage": "iframe",
                    })
                    if len(comments) >= 20:
                        return

        for iframe in soup.select(", ".join(self.iframe_selectors)):
            src = iframe.get("src") or iframe.get("data-src")
            if not src:
                continue
            iframe_url = self._resolve_url(base_url, src)
            try:
                frame_resp = requests.get(iframe_url, timeout=30)
                frame_resp.raise_for_status()
                frame_doc = BeautifulSoup(frame_resp.text, "html.parser")
                extract_comments_from_doc(frame_doc, f"iframe[{iframe_url}] ")
                if len(comments) >= 20:
                    break
            except Exception:
                continue

        return comments

    def _resolve_url(self, base_url: str, relative_url: str) -> str:
        if relative_url.startswith("http"):
            return relative_url
        if relative_url.startswith("//"):
            return f"https:{relative_url}"
        if base_url.endswith("/"):
            return base_url + relative_url.lstrip("/")
        return base_url.rsplit("/", 1)[0] + "/" + relative_url.lstrip("/")
