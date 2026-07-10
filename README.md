# Physical AI Market Intelligence Dashboard

フィジカルAI(ヒューマノイド・Embodied AI)の**報道動向**と**米国特許動向**を毎日自動収集し、
静的ダッシュボードとして GitHub Pages に無料公開するプロジェクト。

## 構成

```
scripts/
  config.py         # 監視トピック・特許検索フレーズ・除外語(ここだけ編集すればOK)
  fetch_news.py     # Google News RSS → data/news_store.json に蓄積
  fetch_patents.py  # PatentsView API → data/patents.json
  analyze.py        # ワードクラウド・ホットニュース・トレンド → data/analysis.json
  build_site.py     # docs/index.html(自己完結型HTML)を生成
data/               # 収集データ(リポジトリにコミットして蓄積)
docs/               # GitHub Pages 公開ディレクトリ
.github/workflows/update.yml  # 毎日 06:00 JST に自動更新
```

## ローカル実行

```bash
pip install -r requirements.txt
python scripts/fetch_news.py
python scripts/fetch_patents.py   # PATENTSVIEW_API_KEY 未設定ならスキップされる
python scripts/analyze.py
python scripts/build_site.py
open docs/index.html
```

## 公開手順(すべて無料枠)

1. GitHub に新規リポジトリを作成し、このフォルダを push する
2. リポジトリの **Settings → Pages** で
   Source: `Deploy from a branch` / Branch: `main` / Folder: `/docs` を選択
3. **Settings → Actions → General** で
   Workflow permissions を `Read and write permissions` に設定
4. (特許データを使う場合)[PatentsView APIキー](https://patentsview.org/apis/keyrequest)を
   無料取得し、**Settings → Secrets and variables → Actions** に
   `PATENTSVIEW_API_KEY` として登録
5. **Actions** タブから `Update dashboard` を手動実行(Run workflow)して初回データを生成

以降は毎日 06:00 JST に自動更新される。

## データソースと制約

- **ニュース**: Google News RSS(1クエリあたり直近約100件)。トレンドは日次実行の
  蓄積で精度が上がる(運用開始から2〜4週間で30日トレンドが埋まる)
- **特許**: PatentsView(USPTO公式・無料)。**米国登録特許のみ**。直近1〜2年は
  権利化タイムラグで件数が少なく見える
- Google Alerts の RSS フィード URL を持っている場合は、`fetch_news.py` の
  フィードURLリストに追加すれば併用できる

## トピックの変更

`scripts/config.py` の `TOPICS` を編集(最大8トピック。チャートの色は登録順に固定割当)。
特許の検索フレーズは同ファイルの `PATENT_PHRASES`。
