# -*- coding: utf-8 -*-
"""ダッシュボードの週次スナップショットを保存する。

- 毎日のCI実行時に呼ばれ、JSTで月曜日のときだけ docs/snapshots/YYYY-MM-DD.html を保存
  (初回実行時はスナップショットが1つもないため曜日に関係なく保存する。
   FORCE_SNAPSHOT=1 で強制保存も可能)
- スナップショットは自己完結HTML。上部に「時点」注記を挿入し、相対パスを補正する
- docs/snapshots/index.html(一覧ページ)も毎回再生成する
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
SNAP_DIR = DOCS_DIR / "snapshots"


def build_index(snapshots: list) -> str:
    items = "".join(
        f'<li><a href="{name}">{name[:-5]}</a></li>'
        for name in sorted(snapshots, reverse=True)
    )
    return f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>週次スナップショット一覧 | Physical AI Market Intelligence</title>
<style>
:root {{ --page:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e; --link:#2a78d6; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --page:#0d0d0d; --ink:#ffffff; --ink2:#c3c2b7; --link:#3987e5; }}
}}
body {{ background:var(--page); color:var(--ink);
  font:15px/1.8 system-ui,-apple-system,"Hiragino Sans",sans-serif;
  max-width:640px; margin:0 auto; padding:40px 16px; }}
h1 {{ font-size:22px; }}
p {{ color:var(--ink2); font-size:14px; }}
a {{ color:var(--link); }}
ul {{ padding-left:24px; }}
</style>
</head>
<body>
<h1>週次スナップショット一覧</h1>
<p>毎週月曜 06:00 JST 時点のダッシュボードを保存しています。
<a href="../index.html">最新のダッシュボードに戻る</a></p>
<ul>{items}</ul>
</body>
</html>'''


def main() -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    existing = [p.name for p in SNAP_DIR.glob("*.html") if p.name != "index.html"]

    jst_now = datetime.now(timezone.utc) + timedelta(hours=9)
    force = os.environ.get("FORCE_SNAPSHOT", "") == "1"
    is_monday = jst_now.weekday() == 0

    if force or is_monday or not existing:
        date = jst_now.strftime("%Y-%m-%d")
        html = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
        # スナップショットは docs/snapshots/ 配下に置くため相対パスを補正
        html = html.replace('src="assets/', 'src="../assets/')
        html = html.replace('href="snapshots/"', 'href="./"')
        notice = (
            f'<div style="background:#2a78d6;color:#fff;font-size:13px;'
            f'padding:8px 16px;border-radius:8px;margin-bottom:20px;">'
            f'これは {date} 時点の週次スナップショットです ・ '
            f'<a href="../index.html" style="color:#fff;font-weight:600;">最新版を見る →</a></div>'
        )
        html = html.replace("<main>", "<main>" + notice, 1)
        (SNAP_DIR / f"{date}.html").write_text(html, encoding="utf-8")
        if f"{date}.html" not in existing:
            existing.append(f"{date}.html")
        print(f"[done] スナップショット保存: snapshots/{date}.html")
    else:
        print(f"[skip] 本日はJST {['月','火','水','木','金','土','日'][jst_now.weekday()]}曜のためスナップショットなし(月曜のみ)")

    (SNAP_DIR / "index.html").write_text(build_index(existing), encoding="utf-8")
    print(f"[done] 一覧ページ更新: {len(existing)} 件")


if __name__ == "__main__":
    main()
