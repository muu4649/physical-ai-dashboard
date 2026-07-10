# -*- coding: utf-8 -*-
"""PatentsView Search API からフィジカルAI関連の米国特許を取得し data/patents.json に保存する。

APIキーは環境変数 PATENTSVIEW_API_KEY で渡す(無料: https://patentsview.org/apis/keyrequest)。
キー未設定の場合はスキップし、ダッシュボード側に「未接続」と表示させる。
"""
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import PATENT_DATE_FROM, PATENT_PHRASES

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_PATH = DATA_DIR / "patents.json"
API_URL = "https://search.patentsview.org/api/v1/patent/"
MAX_PAGES = 5
PAGE_SIZE = 1000


def build_query() -> dict:
    phrase_conditions = []
    for phrase in PATENT_PHRASES:
        phrase_conditions.append({"_text_phrase": {"patent_title": phrase}})
        phrase_conditions.append({"_text_phrase": {"patent_abstract": phrase}})
    return {
        "_and": [
            {"_gte": {"patent_date": PATENT_DATE_FROM}},
            {"_or": phrase_conditions},
        ]
    }


def fetch_all(api_key: str) -> tuple:
    patents = []
    total_hits = 0
    after = None
    for _ in range(MAX_PAGES):
        options = {"size": PAGE_SIZE}
        if after:
            options["after"] = after
        body = {
            "q": build_query(),
            "f": ["patent_id", "patent_title", "patent_date",
                  "assignees.assignee_organization"],
            "s": [{"patent_id": "asc"}],
            "o": options,
        }
        resp = requests.post(
            API_URL,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        page = data.get("patents") or []
        total_hits = data.get("total_hits", len(patents) + len(page))
        patents.extend(page)
        if len(page) < PAGE_SIZE:
            break
        after = page[-1]["patent_id"]
    return patents, total_hits


def aggregate(patents: list, total_hits: int) -> dict:
    by_year = Counter()
    assignees = Counter()
    for p in patents:
        by_year[p["patent_date"][:4]] += 1
        for a in p.get("assignees") or []:
            org = (a or {}).get("assignee_organization")
            if org:
                assignees[org] += 1
    recent = sorted(patents, key=lambda p: p["patent_date"], reverse=True)[:10]
    return {
        "available": True,
        "total_hits": total_hits,
        "fetched": len(patents),
        "by_year": dict(sorted(by_year.items())),
        "top_assignees": assignees.most_common(10),
        "recent": [
            {
                "id": p["patent_id"],
                "title": p["patent_title"],
                "date": p["patent_date"],
                "assignee": next(
                    (a.get("assignee_organization")
                     for a in (p.get("assignees") or []) if a.get("assignee_organization")),
                    "",
                ),
                "url": f"https://patents.google.com/patent/US{p['patent_id']}",
            }
            for p in recent
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("PATENTSVIEW_API_KEY", "").strip()
    if not api_key:
        print("[warn] PATENTSVIEW_API_KEY 未設定のため特許データをスキップ")
        if not OUT_PATH.exists():
            OUT_PATH.write_text(
                json.dumps({"available": False}, ensure_ascii=False), encoding="utf-8"
            )
        return
    try:
        patents, total_hits = fetch_all(api_key)
    except requests.RequestException as e:
        print(f"[error] PatentsView 取得失敗: {e}")
        if not OUT_PATH.exists():
            OUT_PATH.write_text(
                json.dumps({"available": False}, ensure_ascii=False), encoding="utf-8"
            )
        return
    result = aggregate(patents, total_hits)
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"[done] 特許 {result['fetched']} 件取得 (total_hits={total_hits}) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
