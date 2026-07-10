# -*- coding: utf-8 -*-
"""analysis.json / patents.json から自己完結型の静的ダッシュボード docs/index.html を生成する。

外部CDN・外部フォントに依存しない(GitHub Pages でもプレビュー環境でもそのまま動く)。
チャートは Python 側で SVG を生成し、ホバーツールチップだけ最小限の JS で付与する。
"""
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# dataviz 検証済みパレット(light / dark)
SERIES_LIGHT = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7"]
SERIES_DARK = ["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9"]


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def nice_ceil(v: float) -> int:
    if v <= 5:
        return 5
    mag = 10 ** int(math.floor(math.log10(v)))
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * mag:
            return int(m * mag)
    return int(v)


def time_ago(iso: str, now: datetime) -> str:
    dt = datetime.fromisoformat(iso)
    hours = (now - dt).total_seconds() / 3600
    if hours < 1:
        return "1時間以内"
    if hours < 24:
        return f"{int(hours)}時間前"
    return f"{int(hours // 24)}日前"


def rounded_bar(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    """上端のみ角丸・ベースライン接地の縦棒パス。"""
    if h <= r:
        r = max(h / 2, 0.5)
    return (f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
            f"L{x + w:.1f},{y + h:.1f} Z")


def rounded_hbar(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    """右端のみ角丸・左接地の横棒パス。"""
    if w <= r:
        r = max(w / 2, 0.5)
    return (f"M{x:.1f},{y:.1f} L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
            f"L{x + w:.1f},{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} "
            f"L{x:.1f},{y + h:.1f} Z")


# ---------------------------------------------------------------- trend chart

def render_trend_chart(trend: dict) -> str:
    dates = trend["dates"]
    series = trend["series"]
    W, H = 860, 300
    ml, mr, mt, mb = 40, 16, 14, 30
    pw, ph = W - ml - mr, H - mt - mb
    vmax = nice_ceil(max((max(s["values"]) for s in series), default=1) or 1)
    n = len(dates)

    def px(i: int) -> float:
        return ml + pw * i / max(n - 1, 1)

    def py(v: float) -> float:
        return mt + ph * (1 - v / vmax)

    grid = []
    ticks = 4 if vmax % 4 == 0 else 5  # 目盛りが整数になる分割数を選ぶ
    for k in range(ticks + 1):
        v = vmax * k / ticks
        y = py(v)
        grid.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml + pw}" y2="{y:.1f}" class="grid"/>')
        grid.append(f'<text x="{ml - 8}" y="{y + 4:.1f}" class="tick" text-anchor="end">{int(v)}</text>')

    xticks = []
    step = max(n // 6, 1)
    for i in range(0, n, step):
        label = dates[i][5:].replace("-", "/")
        xticks.append(f'<text x="{px(i):.1f}" y="{H - 8}" class="tick" text-anchor="middle">{label}</text>')

    paths = []
    for si, s in enumerate(series):
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(s["values"]))
        paths.append(f'<polyline points="{pts}" fill="none" class="line s{si + 1}"/>')

    legend = "".join(
        f'<span class="lg"><i class="chip s{si + 1}"></i>{esc(s["label"])}</span>'
        for si, s in enumerate(series)
    )
    payload = json.dumps(
        {"dates": dates, "series": [{"label": s["label"], "values": s["values"]} for s in series],
         "ml": ml, "pw": pw, "mt": mt, "ph": ph, "vmax": vmax},
        ensure_ascii=False,
    )
    return f'''
<div class="chart-wrap">
<svg id="trend" viewBox="0 0 {W} {H}" role="img" aria-label="トピック別 日次記事数(直近30日)">
  <line x1="{ml}" y1="{mt + ph}" x2="{ml + pw}" y2="{mt + ph}" class="axis"/>
  {"".join(grid)}
  {"".join(xticks)}
  {"".join(paths)}
  <line id="trend-cross" x1="0" y1="{mt}" x2="0" y2="{mt + ph}" class="cross" style="display:none"/>
  <rect id="trend-hit" x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="transparent"/>
</svg>
<div class="legend">{legend}</div>
<p class="chart-note">※ RSSは直近約100件のみ取得のため、運用開始直後は過去日の件数が実際より少なく表示される(日次実行の蓄積で精度が上がる)</p>
<script type="application/json" id="trend-data">{payload}</script>
</div>'''


def render_trend_table(trend: dict) -> str:
    heads = "".join(f"<th>{esc(s['label'])}</th>" for s in trend["series"])
    rows = []
    for i, d in enumerate(trend["dates"]):
        cells = "".join(f"<td>{s['values'][i]}</td>" for s in trend["series"])
        rows.append(f"<tr><td>{d}</td>{cells}</tr>")
    return (f'<details class="tbl"><summary>データテーブルを表示(日次件数)</summary>'
            f'<div class="scroll"><table><thead><tr><th>日付</th>{heads}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></details>')


# ----------------------------------------------------------------- word cloud

def render_wordcloud(words: list) -> str:
    if not words:
        return '<p class="muted">データが不足しています。数日分の収集後に表示されます。</p>'
    cmax = words[0][1]
    spans = []
    for rank, (word, count) in enumerate(words):
        size = 13 + 30 * math.sqrt(count / cmax)
        tier = "wc-a" if rank < 10 else ("wc-b" if rank < 30 else "wc-c")
        spans.append(
            f'<span class="wc {tier}" style="font-size:{size:.0f}px" '
            f'data-tip="{esc(word)}: {count} 記事">{esc(word)}</span>'
        )
    return f'<div class="cloud">{"".join(spans)}</div>'


# ------------------------------------------------------------------ hot news

def render_hot_news(hot: list, now: datetime) -> str:
    if not hot:
        return '<p class="muted">データが不足しています。</p>'
    items = []
    for i, h in enumerate(hot):
        badge = f'<span class="badge">{h["count"]} 媒体</span>' if h["count"] > 1 else ""
        srcs = " / ".join(esc(s) for s in h["sources"][:4])
        items.append(f'''<li class="hot">
  <span class="rank">{i + 1}</span>
  <div class="hot-body">
    <a href="{esc(h["link"])}" target="_blank" rel="noopener">{esc(h["title"])}</a>
    <div class="meta">{badge}<span>{time_ago(h["published"], now)}</span><span class="srcs">{srcs}</span></div>
  </div>
</li>''')
    return f'<ol class="hotlist">{"".join(items)}</ol>'


# ------------------------------------------------------------------- patents

def render_patents(patents: dict) -> str:
    if not patents.get("available"):
        return '''<div class="notice">
<strong>特許データは未接続です。</strong>
<p>PatentsView の無料APIキーを取得し(<a href="https://patentsview.org/apis/keyrequest"
target="_blank" rel="noopener">patentsview.org/apis/keyrequest</a>)、
GitHub リポジトリの Secrets に <code>PATENTSVIEW_API_KEY</code> として登録すると、
次回の自動更新から米国特許の出願動向がここに表示されます。</p></div>'''

    by_year = patents["by_year"]
    years = sorted(by_year.keys())
    vmax = nice_ceil(max(by_year.values()))
    W, H = 560, 240
    ml, mt, mb = 40, 26, 26
    pw, ph = W - ml - 16, H - mt - mb
    n = len(years)
    slot = pw / max(n, 1)
    bw = min(slot * 0.6, 48)
    bars = []
    peak = max(by_year, key=lambda y: by_year[y])
    for i, y in enumerate(years):
        v = by_year[y]
        bh = ph * v / vmax
        x = ml + slot * i + (slot - bw) / 2
        top = mt + ph - bh
        bars.append(f'<path d="{rounded_bar(x, top, bw, bh)}" class="bar" '
                    f'data-tip="{y}年: {v} 件"/>')
        if y in (peak, years[-1]):
            bars.append(f'<text x="{x + bw / 2:.1f}" y="{top - 6:.1f}" class="val" '
                        f'text-anchor="middle">{v}</text>')
        bars.append(f'<text x="{x + bw / 2:.1f}" y="{H - 8}" class="tick" '
                    f'text-anchor="middle">{y}</text>')
    grid = []
    ticks = 4 if vmax % 4 == 0 else 5
    for k in range(1, ticks):
        gy = mt + ph * (1 - k / ticks)
        grid.append(f'<line x1="{ml}" y1="{gy:.1f}" x2="{ml + pw}" y2="{gy:.1f}" class="grid"/>')
        grid.append(f'<text x="{ml - 8}" y="{gy + 4:.1f}" class="tick" text-anchor="end">{int(vmax * k / ticks)}</text>')

    year_chart = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-label="登録年別の特許件数">
  {"".join(grid)}
  <line x1="{ml}" y1="{mt + ph}" x2="{ml + pw}" y2="{mt + ph}" class="axis"/>
  {"".join(bars)}
</svg>
<p class="chart-note">※ 直近年は権利化までのタイムラグで少なく見える点に注意</p>'''

    top = patents["top_assignees"]
    amax = top[0][1] if top else 1
    HB_W = 560
    row_h, gap = 26, 8
    hb_h = len(top) * (row_h + gap) + 10
    hbars = []
    for i, (org, cnt) in enumerate(top):
        y = 5 + i * (row_h + gap)
        w = (HB_W - 230) * cnt / amax
        label = org if len(org) <= 28 else org[:27] + "…"
        hbars.append(f'<text x="196" y="{y + row_h / 2 + 4}" class="alabel" text-anchor="end">{esc(label)}</text>')
        hbars.append(f'<path d="{rounded_hbar(204, y, max(w, 3), row_h)}" class="bar" '
                     f'data-tip="{esc(org)}: {cnt} 件"/>')
        hbars.append(f'<text x="{204 + max(w, 3) + 8:.1f}" y="{y + row_h / 2 + 4}" class="val">{cnt}</text>')
    assignee_chart = f'<svg viewBox="0 0 {HB_W} {hb_h}" role="img" aria-label="出願人別の特許件数トップ10">{"".join(hbars)}</svg>'

    recent = "".join(
        f'<li><a href="{esc(p["url"])}" target="_blank" rel="noopener">{esc(p["title"])}</a>'
        f'<span class="meta">{esc(p["date"])} ・ {esc(p["assignee"] or "個人/不明")}</span></li>'
        for p in patents["recent"]
    )
    return f'''<div class="grid2">
<div class="panel"><h3>登録年別件数(米国特許)</h3>{year_chart}</div>
<div class="panel"><h3>主要出願人 Top 10</h3>{assignee_chart}</div>
</div>
<div class="panel"><h3>最新の登録特許</h3><ul class="patlist">{recent}</ul></div>'''


# ---------------------------------------------------------------------- page

def build_page(analysis: dict, patents: dict) -> str:
    now = datetime.now(timezone.utc)
    kpi = analysis["kpi"]
    delta = kpi["articles_7d"] - kpi["articles_prev_7d"]
    delta_html = ""
    if kpi["articles_prev_7d"] > 0 or delta != 0:
        cls = "up" if delta >= 0 else "down"
        sign = "+" if delta >= 0 else ""
        delta_html = f'<span class="delta {cls}">{sign}{delta} vs 前週</span>'
    pat_kpi = f'{patents["total_hits"]:,}' if patents.get("available") else "未接続"
    updated = datetime.fromisoformat(analysis["updated_at"]).strftime("%Y-%m-%d %H:%M UTC")

    light_vars = "".join(f"--s{i + 1}:{c};" for i, c in enumerate(SERIES_LIGHT))
    dark_vars = "".join(f"--s{i + 1}:{c};" for i, c in enumerate(SERIES_DARK))

    return f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Physical AI Market Intelligence</title>
<style>
:root {{
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,.10);
  --good:#006300; --bad:#d03b3b; {light_vars}
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --page:#0d0d0d; --surface:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10);
    --good:#0ca30c; --bad:#e66767; {dark_vars}
  }}
}}
:root[data-theme="light"] {{
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,.10);
  --good:#006300; --bad:#d03b3b; {light_vars}
}}
:root[data-theme="dark"] {{
  --page:#0d0d0d; --surface:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10);
  --good:#0ca30c; --bad:#e66767; {dark_vars}
}}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--page); color:var(--ink);
  font:15px/1.6 system-ui,-apple-system,"Segoe UI","Hiragino Sans",sans-serif; padding:24px 16px 64px; }}
main {{ max-width:960px; margin:0 auto; }}
header h1 {{ font-size:26px; letter-spacing:.01em; }}
header p {{ color:var(--ink2); margin-top:4px; font-size:14px; }}
section {{ margin-top:36px; }}
h2 {{ font-size:18px; margin-bottom:14px; }}
h3 {{ font-size:14px; color:var(--ink2); margin-bottom:10px; font-weight:600; }}
.panel {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-top:20px; }}
.kpi {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }}
.kpi .label {{ font-size:12px; color:var(--muted); }}
.kpi .value {{ font-size:30px; font-weight:700; line-height:1.2; }}
.kpi .delta {{ font-size:12px; }}
.delta.up {{ color:var(--good); }} .delta.down {{ color:var(--bad); }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
@media (max-width:760px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
svg {{ width:100%; height:auto; display:block; }}
.grid {{ stroke:var(--grid); stroke-width:1; }}
.axis {{ stroke:var(--axis); stroke-width:1; }}
.tick {{ fill:var(--muted); font-size:11px; }}
.val {{ fill:var(--ink2); font-size:11px; }}
.alabel {{ fill:var(--ink2); font-size:12px; }}
.line {{ stroke-width:2; }} .cross {{ stroke:var(--axis); stroke-width:1; }}
.s1 {{ stroke:var(--s1); }} .s2 {{ stroke:var(--s2); }} .s3 {{ stroke:var(--s3); }}
.s4 {{ stroke:var(--s4); }} .s5 {{ stroke:var(--s5); }}
.bar {{ fill:var(--s1); }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 18px; margin-top:10px; font-size:13px; color:var(--ink2); }}
.lg {{ display:inline-flex; align-items:center; gap:6px; }}
.chip {{ width:12px; height:12px; border-radius:3px; display:inline-block; }}
.chip.s1 {{ background:var(--s1); }} .chip.s2 {{ background:var(--s2); }} .chip.s3 {{ background:var(--s3); }}
.chip.s4 {{ background:var(--s4); }} .chip.s5 {{ background:var(--s5); }}
.cloud {{ display:flex; flex-wrap:wrap; gap:6px 14px; align-items:baseline; }}
.wc {{ cursor:default; }} .wc-a {{ color:var(--ink); font-weight:700; }}
.wc-b {{ color:var(--ink2); font-weight:600; }} .wc-c {{ color:var(--muted); }}
.hotlist {{ list-style:none; padding:0; display:flex; flex-direction:column; gap:10px; }}
.hot {{ display:flex; gap:14px; background:var(--surface); border:1px solid var(--border);
  border-radius:12px; padding:12px 16px; }}
.rank {{ font-size:20px; font-weight:700; color:var(--muted); min-width:26px; }}
.hot a {{ color:var(--ink); text-decoration:none; font-weight:600; }}
.hot a:hover {{ text-decoration:underline; }}
.meta {{ display:flex; flex-wrap:wrap; gap:10px; font-size:12px; color:var(--muted); margin-top:4px; }}
.badge {{ background:var(--s1); color:#fff; border-radius:10px; padding:0 8px; font-weight:600; }}
.patlist {{ list-style:none; padding:0; display:flex; flex-direction:column; gap:10px; }}
.patlist a {{ color:var(--ink); text-decoration:none; font-weight:600; }}
.patlist a:hover {{ text-decoration:underline; }}
.patlist .meta {{ display:block; }}
.notice {{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
  padding:16px 18px; color:var(--ink2); font-size:14px; }}
.notice code {{ background:var(--page); padding:1px 6px; border-radius:4px; }}
.muted {{ color:var(--muted); }}
.chart-note {{ font-size:12px; color:var(--muted); margin-top:6px; }}
.tbl summary {{ cursor:pointer; color:var(--ink2); font-size:13px; margin-top:10px; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; font-size:12px; margin-top:8px;
  font-variant-numeric:tabular-nums; }}
th,td {{ border:1px solid var(--grid); padding:3px 8px; text-align:right; }}
th:first-child,td:first-child {{ text-align:left; }}
#tip {{ position:fixed; pointer-events:none; background:var(--ink); color:var(--page);
  font-size:12px; padding:6px 10px; border-radius:8px; display:none; z-index:10;
  max-width:280px; line-height:1.5; }}
footer {{ margin-top:48px; font-size:12px; color:var(--muted); }}
a {{ color:var(--s1); }}
</style>
</head>
<body>
<main>
<header>
  <h1>Physical AI Market Intelligence</h1>
  <p>フィジカルAI(ヒューマノイド・Embodied AI)の報道動向と特許動向を毎日自動収集 ・ 最終更新 {updated}</p>
</header>

<div class="kpis">
  <div class="kpi"><div class="label">記事数(直近7日)</div>
    <div class="value">{kpi["articles_7d"]}</div>{delta_html}</div>
  <div class="kpi"><div class="label">情報ソース数(7日)</div>
    <div class="value">{kpi["sources_7d"]}</div></div>
  <div class="kpi"><div class="label">記事数(30日)</div>
    <div class="value">{kpi["articles_30d"]}</div></div>
  <div class="kpi"><div class="label">関連米国特許(2019〜)</div>
    <div class="value">{pat_kpi}</div></div>
</div>

<section>
  <h2>トレンド — トピック別 日次記事数(30日)</h2>
  <div class="panel">{render_trend_chart(analysis["trend"])}{render_trend_table(analysis["trend"])}</div>
</section>

<section>
  <h2>ワードクラウド — 直近の頻出キーワード</h2>
  <div class="panel">{render_wordcloud(analysis["wordcloud"])}</div>
</section>

<section>
  <h2>ホットニュース — 報道量×新しさスコア Top 10</h2>
  {render_hot_news(analysis["hot_news"], now)}
</section>

<section>
  <h2>特許動向(PatentsView / 米国特許)</h2>
  {render_patents(patents)}
</section>

<footer>
  <p>データソース: Google News RSS ・ PatentsView (USPTO) ・ 本ダッシュボードは GitHub Actions により毎日自動更新。
  記事の著作権は各媒体に帰属します。集計値は自動収集に基づく参考値であり網羅性を保証しません。</p>
</footer>
</main>
<div id="tip"></div>
<script>
(function () {{
  var tip = document.getElementById("tip");
  function show(text, x, y) {{
    tip.innerHTML = text; tip.style.display = "block";
    var w = tip.offsetWidth;
    tip.style.left = Math.min(x + 14, window.innerWidth - w - 8) + "px";
    tip.style.top = (y + 14) + "px";
  }}
  function hide() {{ tip.style.display = "none"; }}

  document.querySelectorAll("[data-tip]").forEach(function (el) {{
    el.addEventListener("mousemove", function (e) {{ show(el.getAttribute("data-tip"), e.clientX, e.clientY); }});
    el.addEventListener("mouseleave", hide);
  }});

  var dataEl = document.getElementById("trend-data");
  if (dataEl) {{
    var d = JSON.parse(dataEl.textContent);
    var svg = document.getElementById("trend");
    var hit = document.getElementById("trend-hit");
    var cross = document.getElementById("trend-cross");
    hit.addEventListener("mousemove", function (e) {{
      var box = svg.getBoundingClientRect();
      var sx = box.width / svg.viewBox.baseVal.width;
      var mx = (e.clientX - box.left) / sx;
      var i = Math.round((mx - d.ml) / d.pw * (d.dates.length - 1));
      i = Math.max(0, Math.min(d.dates.length - 1, i));
      var x = d.ml + d.pw * i / (d.dates.length - 1);
      cross.setAttribute("x1", x); cross.setAttribute("x2", x);
      cross.style.display = "";
      var rows = d.series.map(function (s) {{
        return s.label + ": <b>" + s.values[i] + "</b>";
      }}).join("<br>");
      show("<b>" + d.dates[i] + "</b><br>" + rows, e.clientX, e.clientY);
    }});
    hit.addEventListener("mouseleave", function () {{ cross.style.display = "none"; hide(); }});
  }}
}})();
</script>
</body>
</html>'''


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    analysis = json.loads((DATA_DIR / "analysis.json").read_text(encoding="utf-8"))
    patents_path = DATA_DIR / "patents.json"
    patents = json.loads(patents_path.read_text(encoding="utf-8")) if patents_path.exists() else {"available": False}
    (DOCS_DIR / "index.html").write_text(build_page(analysis, patents), encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"[done] ダッシュボード生成 -> {DOCS_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
