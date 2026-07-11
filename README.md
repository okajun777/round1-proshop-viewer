# ROUND1 プロショップ商品一覧

[r1b.jp](http://r1b.jp/) の取扱商品を、カテゴリ・実ブランド別に見やすく表示するビューアです。

## 公開URL（LINEでも可）

https://okajun777.github.io/round1-proshop-viewer/

LINEのトークにこのURLを貼ると、アプリ内ブラウザで開けます。

## ローカルでの使い方

```bash
# 商品データ取得
python fetch_goods.py

# 表示（ブラウザで開く）
python -m http.server 8791
# → http://127.0.0.1:8791/
```

または `open.bat` を実行。

## 毎日自動更新

`install_daily_update.bat` で Windows タスクを登録すると、毎朝 6:00 に `goods.json` を更新します。

- 手動更新: `update_goods.bat`
- タスク名: `Round1GoodsUpdate`
- 更新後は GitHub Desktop で commit & push すると公開サイトも最新になります

## ファイル

| ファイル | 内容 |
|---|---|
| `index.html` | カテゴリ別ビューア |
| `goods.json` | 取得済み商品データ |
| `fetch_goods.py` | r1b.jp から取得するスクリプト |
| `share-line.bat` | 一時公開（Cloudflare Tunnel） |
| `update_goods.bat` | データ更新 |
| `install_daily_update.bat` | 毎朝6時のタスク登録 |

価格は税込。店舗取扱は各自確認してください。
