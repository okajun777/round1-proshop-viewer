# ROUND1 ビューア

ラウンドワン関連データを見やすくまとめるサイトです。

## 公開URL（LINEでも可）

- プロショップ商品一覧: https://okajun777.github.io/round1-proshop-viewer/
- ボウリング混雑一覧: https://okajun777.github.io/round1-proshop-viewer/queue.html

LINEのトークにURLを貼ると、アプリ内ブラウザで開けます。

---

## ボウリング混雑一覧

全国店舗の待ち時間・待ち組数を一覧表示します（公式予約サイトの混雑状況）。

```bash
# 混雑データを取得
python fetch_queue.py

# 表示
python -m http.server 8791
# → http://127.0.0.1:8791/queue.html
```

または `update_queue.bat` を実行。

GitHub Actions が **5分ごと（日本時間 10:00〜24:00頃）** に再取得し、`queue.json` を更新します。

- 手動実行: GitHub の Actions タブ → **Queue status update** → **Run workflow**
- 店舗名の ★ でお気に入り固定（端末に保存）
- 店舗をタップすると公式の順番待ちページへ

---

## プロショップ商品一覧

[r1b.jp](http://r1b.jp/) の取扱商品を、カテゴリ・実ブランド別に見やすく表示するビューアです。

### ローカルでの使い方

```bash
# 商品データ取得
python fetch_goods.py

# 表示（ブラウザで開く）
python -m http.server 8791
# → http://127.0.0.1:8791/
```

または `open.bat` を実行。

### 毎日自動更新

GitHub Actions が **毎朝 6:00（日本時間）** に r1b.jp から商品を再取得し、`goods.json` を更新して公開サイトへ反映します。

- 手動実行: GitHub の Actions タブ → **Daily goods update** → **Run workflow**
- ローカルでも更新したい場合: `update_goods.bat`

PC側のタスクスケジューラ（`Round1GoodsUpdate`）は不要です。残っている場合は削除して構いません。

---

## ファイル

| ファイル | 内容 |
|---|---|
| `index.html` | プロショップ商品ビューア |
| `goods.json` | 取得済み商品データ |
| `fetch_goods.py` | r1b.jp から取得するスクリプト |
| `queue.html` | ボウリング混雑一覧 |
| `queue.json` | 取得済み混雑データ |
| `stores.json` | 店舗マスタ（地区・都道府県） |
| `fetch_queue.py` | 公式予約サイトから混雑を取得 |
| `update_queue.bat` | 混雑データ更新＋表示 |
| `share-line.bat` | 一時公開（Cloudflare Tunnel） |
| `update_goods.bat` | 商品データ更新 |

価格は税込。店舗取扱・待ち時間は各自公式情報を確認してください。
