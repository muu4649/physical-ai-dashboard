# -*- coding: utf-8 -*-
"""Google News RSS からトピック別にニュースを取得し data/news_store.json に蓄積する。

- 記事はタイトルの正規化ハッシュで重複排除
- 既存記事に新トピックがヒットした場合はトピックリストに追記
- 実行のたびに増分蓄積されるため、日次実行でトレンドデータが育つ
"""
import hashlib
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

from config import TOPICS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STORE_PATH = DATA_DIR / "news_store.json"

USER_AGENT = "Mozilla/5.0 (compatible; physical-ai-dashboard/1.0)"


def feed_url(query: str, lang: str) -> str:
    q = urllib.parse.quote(query)
    if lang == "ja":
        return f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title).strip().lower()
    # Google News はタイトル末尾に " - ソース名" を付けるため除去して同一記事を束ねる
    t = re.sub(r"\s+-\s+[^-]+$", "", t)
    return t


def article_id(title: str) -> str:
    return hashlib.sha1(normalize_title(title).encode("utf-8")).hexdigest()[:16]


def parse_published(entry) -> str:
    if getattr(entry, "published_parsed", None):
        dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()


def fetch_topic(topic: dict) -> list:
    url = feed_url(topic["query"], topic["lang"])
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[warn] {topic['id']}: 取得失敗 ({e})")
        return []
    feed = feedparser.parse(resp.text)
    items = []
    for entry in feed.entries:
        title = re.sub(r"\s+-\s+[^-]+$", "", entry.title).strip()
        source = ""
        if getattr(entry, "source", None) is not None:
            source = getattr(entry.source, "title", "") or ""
        items.append({
            "id": article_id(entry.title),
            "title": title,
            "link": entry.link,
            "source": source,
            "published": parse_published(entry),
            "topics": [topic["id"]],
        })
    print(f"[info] {topic['id']}: {len(items)} 件")
    return items


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    store = {}
    if STORE_PATH.exists():
        store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    articles = store.get("articles", {})

    new_count = 0
    for topic in TOPICS:
        for item in fetch_topic(topic):
            existing = articles.get(item["id"])
            if existing:
                topics = set(existing["topics"]) | set(item["topics"])
                existing["topics"] = sorted(topics)
            else:
                articles[item["id"]] = item
                new_count += 1
        time.sleep(1)  # RSSエンドポイントへの連続アクセスを抑制

    store["articles"] = articles
    store["updated_at"] = datetime.now(timezone.utc).isoformat()
    STORE_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"[done] 新規 {new_count} 件 / 累計 {len(articles)} 件 -> {STORE_PATH}")


if __name__ == "__main__":
    main()
