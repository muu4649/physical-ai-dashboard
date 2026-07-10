# -*- coding: utf-8 -*-
"""ユーザーが用意した特許CSVを取り込み、集計して data/patents.json に保存する。

取り込み元(両方対応・マージして重複排除):
1. Google Drive の共有フォルダ(推奨)
   - フォルダを「リンクを知っている全員が閲覧可」で共有
   - 環境変数 GDRIVE_FOLDER_ID にフォルダID、GDRIVE_API_KEY にGoogle APIキーを設定
     (APIキーは Google Cloud Console で無料発行。課金登録・ID.me不要)
   - フォルダ内の CSV と Googleスプレッドシートを自動取得
2. リポジトリ内 data/patents_csv/ に置いた CSV ファイル

CSVの列名は自動判定する(Patsnap・Google Patents・J-PlatPat等のエクスポートを想定):
- 番号:   公開番号 / 公開(公告)番号 / publication number / id など
- 名称:   標題 / 発明の名称 / タイトル / title など
- 日付:   出願日 / application date / filing date を優先、なければ 公開日 / publication date
- 出願人: 出願人 / 権利者 / assignee / applicant など
"""
import csv
import io
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOCAL_CSV_DIR = DATA_DIR / "patents_csv"
OUT_PATH = DATA_DIR / "patents.json"

DRIVE_LIST_URL = "https://www.googleapis.com/drive/v3/files"

# 列名判定パターン(先にマッチしたものを採用)
COLUMN_PATTERNS = {
    "number": [r"公開\s*[(（]?公告[)）]?\s*番号", r"公開番号", r"公告番号", r"登録番号",
               r"publication\s*number", r"patent\s*number", r"display\s*key",  # Display Key = Lens.org
               r"lens\s*id", r"文献番号", r"^id$", r"番号"],
    "title": [r"発明の名称", r"標題", r"タイトル", r"^title$", r"名称"],
    "app_date": [r"出願日", r"application\s*date", r"filing\s*date", r"出願年月日"],
    "pub_date": [r"公開日", r"公告日", r"登録日", r"publication\s*date", r"grant\s*date", r"^date$"],
    "assignee": [r"出願人", r"権利者", r"現所有者", r"assignee", r"applicant", r"譲受人"],
}

ASSIGNEE_SPLIT = re.compile(r"[;|;]|、|\s*\|\s*")
DATE_PATTERN = re.compile(r"(\d{4})[/\-年.]?\s*(\d{1,2})?")


def detect_columns(headers: list) -> dict:
    mapping = {}
    for role, patterns in COLUMN_PATTERNS.items():
        for pat in patterns:
            hit = next((h for h in headers if re.search(pat, h.strip(), re.IGNORECASE)), None)
            if hit:
                mapping[role] = hit
                break
    return mapping


def decode_csv(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_year(value: str) -> str:
    m = DATE_PATTERN.search(value or "")
    return m.group(1) if m else ""


def parse_ym(value: str) -> str:
    """日付文字列から 'YYYY-MM'(月が取れなければ 'YYYY')を返す。"""
    m = DATE_PATTERN.search(value or "")
    if not m:
        return ""
    if m.group(2):
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return m.group(1)


def parse_csv(name: str, text: str) -> list:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        print(f"[warn] {name}: ヘッダー行が読めません")
        return []
    cols = detect_columns(reader.fieldnames)
    if "number" not in cols and "title" not in cols:
        print(f"[warn] {name}: 番号・名称列を判定できずスキップ (headers={reader.fieldnames[:8]})")
        return []
    date_col = cols.get("app_date") or cols.get("pub_date")
    date_label = "出願年" if "app_date" in cols else "公開・登録年"
    rows = []
    for row in reader:
        number = (row.get(cols.get("number", ""), "") or "").strip()
        title = (row.get(cols.get("title", ""), "") or "").strip()
        date_raw = (row.get(date_col, "") or "").strip() if date_col else ""
        assignee_raw = (row.get(cols.get("assignee", ""), "") or "").strip()
        if not (number or title):
            continue
        rows.append({
            "number": number,
            "title": title,
            "year": parse_year(date_raw),
            "date": date_raw,
            "assignees": [a.strip() for a in ASSIGNEE_SPLIT.split(assignee_raw) if a.strip()],
            "date_label": date_label,
        })
    print(f"[info] {name}: {len(rows)} 行 (列判定: {cols})")
    return rows


def fetch_drive_files() -> list:
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "").strip()
    api_key = os.environ.get("GDRIVE_API_KEY", "").strip()
    if not folder_id or not api_key:
        print("[info] GDRIVE_FOLDER_ID / GDRIVE_API_KEY 未設定のためDrive取得をスキップ")
        return []
    try:
        resp = requests.get(DRIVE_LIST_URL, params={
            "q": f"'{folder_id}' in parents and trashed=false",
            "fields": "files(id,name,mimeType)",
            "key": api_key,
        }, timeout=30)
        resp.raise_for_status()
        files = resp.json().get("files", [])
    except requests.RequestException as e:
        print(f"[error] Driveフォルダ一覧の取得失敗: {e}")
        return []
    rows = []
    for f in files:
        try:
            if f["mimeType"] == "application/vnd.google-apps.spreadsheet":
                url = f"{DRIVE_LIST_URL}/{f['id']}/export"
                r = requests.get(url, params={"mimeType": "text/csv", "key": api_key}, timeout=60)
            elif f["name"].lower().endswith(".csv"):
                url = f"{DRIVE_LIST_URL}/{f['id']}"
                r = requests.get(url, params={"alt": "media", "key": api_key}, timeout=60)
            else:
                print(f"[info] {f['name']}: CSV/スプレッドシート以外のためスキップ")
                continue
            r.raise_for_status()
            rows.extend(parse_csv(f["name"], decode_csv(r.content)))
        except requests.RequestException as e:
            print(f"[error] {f['name']} のダウンロード失敗: {e}")
    return rows


def fetch_local_files() -> list:
    if not LOCAL_CSV_DIR.exists():
        return []
    rows = []
    for path in sorted(LOCAL_CSV_DIR.glob("*.csv")):
        rows.extend(parse_csv(path.name, decode_csv(path.read_bytes())))
    return rows


def google_patents_url(number: str) -> str:
    compact = re.sub(r"[\s\-]", "", number)
    return f"https://patents.google.com/patent/{compact}" if compact else ""


def aggregate(rows: list) -> dict:
    seen = set()
    unique = []
    for r in rows:
        key = r["number"] or r["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    by_year = Counter(r["year"] for r in unique if r["year"])
    assignees = Counter(a for r in unique for a in r["assignees"])
    recent = sorted((r for r in unique if r["year"]), key=lambda r: r["date"], reverse=True)[:10]
    date_label = unique[0]["date_label"] if unique else "出願年"
    yms = sorted(ym for ym in (parse_ym(r["date"]) for r in unique) if ym)
    return {
        "available": True,
        "source": "csv",
        "date_label": date_label,
        "oldest": yms[0] if yms else "",
        "newest": yms[-1] if yms else "",
        "total_hits": len(unique),
        "fetched": len(unique),
        "by_year": dict(sorted(by_year.items())),
        "top_assignees": assignees.most_common(10),
        "recent": [
            {
                "id": r["number"],
                "title": r["title"] or r["number"],
                "date": r["date"],
                "assignee": r["assignees"][0] if r["assignees"] else "",
                "url": google_patents_url(r["number"]),
            }
            for r in recent
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = fetch_drive_files() + fetch_local_files()
    if not rows:
        print("[warn] 特許CSVが見つからないため未接続状態を維持")
        if not OUT_PATH.exists():
            OUT_PATH.write_text(
                json.dumps({"available": False}, ensure_ascii=False), encoding="utf-8"
            )
        return
    result = aggregate(rows)
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"[done] 特許 {result['total_hits']} 件(重複排除後) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
