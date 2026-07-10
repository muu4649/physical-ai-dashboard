# -*- coding: utf-8 -*-
"""ダッシュボードの監視対象トピック定義。

クエリを追加・変更する場合はこのファイルだけ編集すればよい。
lang は Google News RSS の地域パラメータ切替に使う("en" / "ja")。
"""

# トレンドチャートの系列 = このトピックリスト(最大8つまで。色は登録順に固定割当)
TOPICS = [
    {"id": "physical_ai_en", "label": "Physical AI (EN)", "query": '"physical AI"', "lang": "en"},
    {"id": "physical_ai_ja", "label": "フィジカルAI", "query": "フィジカルAI", "lang": "ja"},
    {"id": "embodied_ai", "label": "Embodied AI (EN)", "query": '"embodied AI"', "lang": "en"},
    {"id": "humanoid_en", "label": "Humanoid robot (EN)", "query": '"humanoid robot"', "lang": "en"},
    {"id": "humanoid_ja", "label": "ヒューマノイド (JA)", "query": "ヒューマノイドロボット", "lang": "ja"},
]

# PatentsView 検索フレーズ(タイトル・要約の完全フレーズ一致)
PATENT_PHRASES = [
    "humanoid robot",
    "embodied artificial intelligence",
    "physical artificial intelligence",
    "robot foundation model",
]
PATENT_DATE_FROM = "2019-01-01"

# ワードクラウドから除外する語(クエリ語そのものは常に上位に来るため除外)
EXCLUDE_WORDS = {
    # EN
    "ai", "robot", "robots", "robotics", "physical", "embodied", "humanoid",
    "artificial", "intelligence", "the", "and", "for", "with", "its", "new",
    "from", "that", "this", "will", "are", "has", "have", "can", "how", "why",
    "what", "into", "more", "over", "after", "amid", "says", "say", "said",
    "could", "would", "may", "not", "but", "you", "your", "their", "our",
    "about", "than", "just", "now", "out", "all", "get", "gets", "set", "sets",
    "here", "when", "where", "who", "them", "they", "his", "her", "was", "were",
    "been", "being", "them", "these", "those", "first", "next", "year", "years",
    # JA(クエリ語・トピック語)
    "フィジカル", "ヒューマノイド", "ヒューマノイドロボット", "ロボット",
    "ロボ", "人型", "人工知能",
    # JA(一般語)
    "こと", "ため", "これ", "それ", "さん", "する", "した", "して", "できる",
    "など", "よう", "もの", "ところ", "とき", "ら", "的", "化", "性", "系",
    "年", "月", "日", "株式会社", "会社", "ニュース", "記事", "発表", "提供",
    "開始", "実施", "予定", "今回", "同社", "本", "件", "円", "人", "社",
}
