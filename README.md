# npb-standings

2026年プロ野球（NPB）の**順位表**と**順位推移**を表示する Streamlit アプリです。

## 機能

- セ・リーグ / パ・リーグ の最新順位表（NPB公式サイトから取得）
- 日次スナップショットによる順位推移グラフ
- チームカラー付き折れ線グラフ
- GitHub Actions による毎日自動更新

## デモ

ローカルで動かす場合:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 自動更新

`.github/workflows/update-all.yml` が毎日 03:00 UTC（日本時間 12:00）に実行され、

1. NPB公式サイトから最新順位を取得
2. `data/standings.json` を更新
3. `data/rank_history.json` に当日の順位を追記
4. 変更があれば main に push

します。

手動実行も可能です（Actions タブ → Run workflow）。

## データファイル

| ファイル | 内容 |
|---------|------|
| `data/standings.json` | 最新のセ・パ順位 |
| `data/rank_history.json` | 日付ごとの順位履歴 |

## 注意

- スクレイピング先（npb.jp）の利用規約を遵守してください
- サイト構造が変わった場合は `scripts/fetch_all.py` のパーサーを調整する必要があります

## ライセンス

MIT
