# -*- coding: utf-8 -*-
"""news_store.json を分析して data/analysis.json を生成する。

出力:
- wordcloud: 直近7日のタイトルから頻出語トップ60(日本語は janome で名詞抽出)
- hot_news:  直近7日の記事をタイトル類似度でクラスタリングし、報道量×新しさでスコアリング
- trend:     直近30日のトピック別日次記事数
- kpi:       7日間記事数・前週比・ユニークソース数など
"""
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from janome.tokenizer import Tokenizer

from config import EXCLUDE_WORDS, TOPICS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STORE_PATH = DATA_DIR / "news_store.json"
OUT_PATH = DATA_DIR / "analysis.json"

JA_PATTERN = re.compile(r"[ぁ-ゟァ-ヿ一-鿿]")
EN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")

tokenizer = Tokenizer()


def parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def tokenize(title: str) -> list:
    """タイトルを日英混在対応でトークン化する(ワードクラウド・類似度判定の共通処理)。"""
    tokens = []
    if JA_PATTERN.search(title):
        for token in tokenizer.tokenize(title):
            pos = token.part_of_speech.split(",")
            if pos[0] == "名詞" and pos[1] not in ("非自立", "代名詞", "数", "接尾"):
                surface = token.surface.strip()
                if len(surface) >= 2 and not surface.isdigit():
                    tokens.append(surface)
    for m in EN_WORD.findall(title):
        tokens.append(m.lower())
    return [t for t in tokens if t.lower() not in EXCLUDE_WORDS]


def build_wordcloud(articles: list) -> list:
    counter = Counter()
    for a in articles:
        counter.update(set(tokenize(a["title"])))  # 同一記事内の重複はカウントしない
    return counter.most_common(60)


def build_hot_news(articles: list, now: datetime) -> list:
    """タイトルのトークン集合の Jaccard 類似度 >= 0.3 で貪欲クラスタリング。"""
    items = []
    for a in sorted(articles, key=lambda x: x["published"], reverse=True):
        tokens = set(tokenize(a["title"]))
        if tokens:
            items.append((a, tokens))
    clusters = []
    for a, tokens in items:
        placed = False
        for cluster in clusters:
            sim = len(tokens & cluster["tokens"]) / len(tokens | cluster["tokens"])
            if sim >= 0.3:
                cluster["members"].append(a)
                cluster["tokens"] |= tokens
                placed = True
                break
        if not placed:
            clusters.append({"rep": a, "tokens": set(tokens), "members": [a]})
    scored = []
    for c in clusters:
        latest = max(parse_dt(m["published"]) for m in c["members"])
        hours = max((now - latest).total_seconds() / 3600, 0)
        score = len(c["members"]) * math.exp(-hours / 72)
        sources = sorted({m["source"] for m in c["members"] if m["source"]})
        scored.append({
            "title": c["rep"]["title"],
            "link": c["rep"]["link"],
            "source": c["rep"]["source"],
            "published": c["rep"]["published"],
            "count": len(c["members"]),
            "sources": sources[:6],
            "score": round(score, 2),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:10]


def build_trend(articles: list, now: datetime, days: int = 30) -> dict:
    start = (now - timedelta(days=days - 1)).date()
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    counts = {t["id"]: defaultdict(int) for t in TOPICS}
    for a in articles:
        d = parse_dt(a["published"]).date().isoformat()
        if d < dates[0]:
            continue
        for tid in a["topics"]:
            if tid in counts:
                counts[tid][d] += 1
    return {
        "dates": dates,
        "series": [
            {"id": t["id"], "label": t["label"],
             "values": [counts[t["id"]].get(d, 0) for d in dates]}
            for t in TOPICS
        ],
    }


def main() -> None:
    store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    articles = list(store.get("articles", {}).values())
    now = datetime.now(timezone.utc)

    week = [a for a in articles if parse_dt(a["published"]) >= now - timedelta(days=7)]
    prev_week = [
        a for a in articles
        if now - timedelta(days=14) <= parse_dt(a["published"]) < now - timedelta(days=7)
    ]
    month = [a for a in articles if parse_dt(a["published"]) >= now - timedelta(days=30)]

    analysis = {
        "updated_at": now.isoformat(),
        "kpi": {
            "articles_7d": len(week),
            "articles_prev_7d": len(prev_week),
            "sources_7d": len({a["source"] for a in week if a["source"]}),
            "articles_30d": len(month),
            "total_articles": len(articles),
        },
        "wordcloud": build_wordcloud(week if len(week) >= 30 else month),
        "hot_news": build_hot_news(week if len(week) >= 10 else month, now),
        "trend": build_trend(articles, now),
    }
    OUT_PATH.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"[done] 分析完了: 7日 {len(week)} 件 / 30日 {len(month)} 件 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
