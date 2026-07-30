# npb-standings

このリポジトリには、公式サイト（npb.jp など）から取得したプロ野球データを自動で更新するワークフローとスクリプトを追加しました。

- 更新頻度: 毎日 03:00 UTC に自動実行
- 手動トリガー: GitHub Actions の "Run workflow" で手動実行可能
- 直接 main に push して更新します

生成されるファイル（data/ ディレクトリ）:
- standings.json
- schedule.json
- results.json
- rosters.json
- stats.json

注意点:
- スクレイピング先の利用規約に従ってください。
- 初回実装は汎用的なテーブルパーサを用いています。実際のページ構造に合わせて scripts/fetch_all.py のパーサを調整する必要があります。

次のステップ:
- 具体的なページ（npb.jp の各ページ）のセレクタを私に教えるか、許可があれば私が確認して調整します。
- ワークフローの時刻を変える場合はお知らせください。
