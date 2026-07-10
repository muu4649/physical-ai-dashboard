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
python scripts/fetch_patents.py   # CSV未配置・Drive未設定ならスキップされる
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
4. (特許データを使う場合)下記「特許CSVの取り込み」を設定
5. **Actions** タブから `Update dashboard` を手動実行(Run workflow)して初回データを生成

以降は毎日 06:00 JST に自動更新される。

## 特許CSVの取り込み

特許データはAPI経由ではなく、**自分でエクスポートしたCSVを取り込む方式**
(PatentsView/USPTO ODP のAPIキーが ID.me 本人確認必須になったため)。
Patsnap・Google Patents・J-PlatPat 等のエクスポートCSVをそのまま使える。
列名は自動判定される: 番号(公開番号/publication number等)・名称(標題/title等)・
日付(出願日優先、なければ公開日)・出願人(出願人/assignee等)。
文字コードは UTF-8 / Shift_JIS(cp932) 両対応。複数ファイルは番号で重複排除してマージ。

### 方法A: Google Drive 共有フォルダ(推奨・アップロードするだけで反映)

1. Google Drive にフォルダを作り、特許CSVを入れる
2. フォルダを右クリック → 共有 → 「リンクを知っている全員」(閲覧者)に設定
3. フォルダを開いたときのURL `drive.google.com/drive/folders/【この部分】` がフォルダID
4. [Google Cloud Console](https://console.cloud.google.com/) で無料プロジェクトを作成
   (課金登録不要)→「APIとサービス」で **Google Drive API を有効化** →
   「認証情報」→ **APIキーを作成**
5. リポジトリの **Settings → Secrets and variables → Actions** に登録:
   - `GDRIVE_FOLDER_ID`: 手順3のフォルダID
   - `GDRIVE_API_KEY`: 手順4のAPIキー

以降はDriveのフォルダにCSVを入れ替えるだけで、翌日の自動更新(または手動実行)で反映。

### 方法B: リポジトリに直接コミット

`data/patents_csv/` フォルダにCSVを置いてpush(GitHubのWeb画面からドラッグ&ドロップでも可)。
Driveと併用した場合は両方をマージする。

## データソースと制約

- **ニュース**: Google News RSS(1クエリあたり直近約100件)。トレンドは日次実行の
  蓄積で精度が上がる(運用開始から2〜4週間で30日トレンドが埋まる)
- **特許**: ユーザー提供CSV。公開リポジトリのため、**CSVの内容も公開される**点に注意
  (商用DBの書誌データを置く場合は利用規約を確認)。直近1〜2年は未公開案件の分
  件数が少なく見える
- Google Alerts の RSS フィード URL を持っている場合は、`fetch_news.py` の
  フィードURLリストに追加すれば併用できる

## トピックの変更

`scripts/config.py` の `TOPICS` を編集(最大8トピック。チャートの色は登録順に固定割当)。
特許の検索フレーズは同ファイルの `PATENT_PHRASES`。
