import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

PATH = Path("data/comments_news.jsonl")
SELECTORS = [
    "[class*=comment]",
    "[id*=comment]",
    ".comment",
    ".comment-box",
    ".comment-list",
    ".comment-item",
    ".comment-body",
    ".comment-text",
    ".comment-content",
    ".comment-entry",
    ".reply",
    ".reply-item",
    ".post-comment",
    ".article-comments",
    ".discussion",
]

class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.iframes = []
        self.scripts = []
        self._in_script = False
        self._current_script = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "iframe":
            self.iframes.append(dict(attrs))
        if tag.lower() == "script":
            self._in_script = True
            self._current_script = []

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self._in_script = False
            self.scripts.append("".join(self._current_script))
            self._current_script = []

    def handle_data(self, data):
        if self._in_script:
            self._current_script.append(data)


def has_selector(html: str, sel: str) -> bool:
    text = html.lower()
    if sel.startswith("[class*=") or sel.startswith("[id*="):
        attr, value = sel[1:-1].split("*=", 1)
        return attr in text and value.strip('"').lower() in text
    return sel.lower() in text


def main():
    if not PATH.exists():
        print(f"Missing file: {PATH}")
        return

    with PATH.open("r", encoding="utf-8") as fh:
        items = [json.loads(line) for line in fh if line.strip()]

    pattern = re.compile(r"([\"'])(https?://[^\"']+?)\1")
    for idx, item in enumerate(items, 1):
        url = item.get("url")
        print(f"[{idx}] {url}")
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            print("  fetch failed:", type(exc).__name__, exc)
            print()
            continue

        found = [(sel, html.lower().count(sel.lower()) if not sel.startswith("[") else "maybe") for sel in SELECTORS if has_selector(html, sel)]
        print("  selectors found:", found[:10] if found else "none")

        parser = ScriptParser()
        parser.feed(html)
        print("  iframe count:", len(parser.iframes))
        for iframe in parser.iframes[:5]:
            print("   iframe src:", iframe.get("src") or iframe.get("data-src"))

        comment_scripts = sum(1 for s in parser.scripts if s and any(k in s.lower() for k in ("comment", "iframe", "disqus", "fb:comments", "giscus", "utterances", "utterances.github.io")))
        script_urls = {m.group(2) for m in pattern.finditer(html)}
        print("  comment-like scripts count:", comment_scripts)
        print("  candidate script URLs:", len(script_urls))
        for s in list(script_urls)[:10]:
            print("    ", s)
        print()


if __name__ == "__main__":
    main()
