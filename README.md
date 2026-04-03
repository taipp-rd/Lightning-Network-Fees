# Lightning Network Fee Distribution Visualizer

Lightning Network（LN）のゴシッププロトコルから収集したチャネル更新データを AWS PostgreSQL から取得し、手数料の分布を可視化するツールです。

## 概要

BOLT #7 `channel_update` メッセージに含まれる以下の4種類の手数料について、チャネルごとの最新ゴシップのみを使用してヒストグラム・ECDF・散布図を生成します。

| 手数料 | 説明 |
|--------|------|
| `base_fee_msat` | ベース手数料（ミリサトシ） |
| `fee_rate_ppm` | 比例手数料率（parts per million） |
| `inbound_base_fee` | インバウンドベース手数料（msat） |
| `inbound_fee_rate` | インバウンド比例手数料率（ppm） |

---

## ディレクトリ構造

```
Lightning-Network-Fees/
├── .env                    # DB認証情報（Git管理外）
├── .env.example            # .envのテンプレート
├── requirements.txt
├── scripts/
│   ├── run_all.py                      # 全分析を一括実行
│   ├── discover_channels_table.py      # 互換テーブルを自動検索
│   └── inspect_channel_update_types.py # 列型・統計の調査
├── src/
│   ├── db/
│   │   ├── connection.py               # PostgreSQL接続（.env読み込み）
│   │   ├── channels_relation.py        # スキーマ.テーブル名の解決
│   │   └── fee_snapshot_query.py       # クエリ組み立て（モード切替）
│   ├── analysis/
│   │   ├── run_helpers.py              # DB取得・ログ出力の共通処理
│   │   ├── base_fee.py                 # base_fee_msat 分析
│   │   ├── fee_rate.py                 # fee_rate_ppm 分析
│   │   ├── inbound_base_fee.py         # inbound_base_fee 分析
│   │   ├── inbound_fee_rate.py         # inbound_fee_rate 分析
│   │   ├── base_fee_vs_fee_rate.py     # base_fee × fee_rate 散布図
│   │   └── inbound_base_fee_vs_inbound_fee_rate.py  # inbound系散布図
│   ├── visualization/
│   │   └── charts.py                   # ヒストグラム・ECDF・散布図描画
│   └── gossip/
│       └── bolt7_channel_update.py     # BOLT #7 仕様メモ
└── output/                             # 生成グラフの保存先（Git管理外）
```

---

## セットアップ

### 1. 依存パッケージのインストール

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. `.env` の設定

`.env.example` をコピーして `.env` を作成し、接続情報を記入します。

```bash
cp .env.example .env
```

```dotenv
# AWS PostgreSQL
LN_DB_HOST=your-rds-host.region.rds.amazonaws.com
LN_DB_PORT=5432
LN_DB_NAME=graph
LN_DB_USER=your_username
LN_DB_PASSWORD=your_password

# テーブル・列名（DBスキーマに合わせて変更）
LN_DB_SCHEMA=public
LN_CHANNELS_TABLE=channel_update
LN_FEE_QUERY_MODE=latest_per_channel   # または snapshot_batch
LN_COLUMN_SNAPSHOT=timestamp
LN_COLUMN_BASE_FEE_MSAT=rp_base_fee_msat
LN_COLUMN_FEE_RATE_PPM=rp_feerate_ppm
LN_COLUMN_INBOUND_BASE_FEE=rp_inbound_base_fee_msat
LN_COLUMN_INBOUND_FEE_RATE=rp_inbound_feerate_ppm
```

---

## 実行方法

### 全分析を一括実行

```bash
python -m scripts.run_all
```

プロジェクトルートで実行してください。6ステップが順に処理されます。

```
=== Lightning Network Fee Distribution Analysis ===

[1/6] base_fee_msat — 開始
[2/6] fee_rate_ppm — 開始
...
All graphs saved to output/
```

### 個別に実行

```bash
python -m src.analysis.base_fee
python -m src.analysis.fee_rate
python -m src.analysis.inbound_base_fee
python -m src.analysis.inbound_fee_rate
```

---

## 生成されるグラフ

| ファイル | 内容 | X軸範囲 | ビン幅 | Y軸 |
|---------|------|---------|--------|-----|
| `base_fee_msat.png` | ベース手数料ヒストグラム | 0〜10,000 msat | 100 msat | 対数 |
| `base_fee_msat_0_1000_50msat.png` | ベース手数料（拡大） | 0〜1,000 msat | 50 msat | 線形 |
| `base_fee_msat_cdf.png` | ベース手数料 ECDF | 0〜10,000 msat | — | 累積確率 |
| `fee_rate_ppm.png` | 比例手数料率ヒストグラム | 0〜2,000 ppm | 50 ppm | 線形 |
| `fee_rate_ppm_cdf.png` | 比例手数料率 ECDF | 0〜2,000 ppm | — | 累積確率 |
| `inbound_base_fee.png` | インバウンドベース手数料ヒストグラム | −1,000〜500 msat | 50 msat | 対数 |
| `inbound_base_fee_cdf.png` | インバウンドベース手数料 ECDF | −1,000〜500 msat | — | 累積確率 |
| `inbound_fee_rate.png` | インバウンド比例手数料率ヒストグラム | −1,000〜500 ppm | 50 ppm | 対数 |
| `inbound_fee_rate_cdf.png` | インバウンド比例手数料率 ECDF | −1,000〜500 ppm | — | 累積確率 |
| `base_fee_msat_vs_fee_rate_ppm_scatter.png` | base_fee × fee_rate 散布図 | 0〜2,000 msat | — | 0〜2,000 ppm |
| `inbound_base_fee_vs_inbound_fee_rate_scatter.png` | inbound系2変数散布図 | −1,000〜500 msat | — | −1,000〜500 ppm |

---

## クエリモード

`LN_FEE_QUERY_MODE` で取得方式を切り替えられます。

| モード | 説明 | 適するテーブル |
|--------|------|---------------|
| `latest_per_channel` | `DISTINCT ON (chan_id)` で各チャネルの最新ゴシップ1行のみ取得 | `channel_update`（行ごとにtimestampが異なる） |
| `snapshot_batch` | `snapshot_time = MAX(snapshot_time)` のバッチ全行を取得 | スナップショット型テーブル |

---

## 調査用スクリプト

### 互換テーブルの自動検索

DBに接続し、手数料列を持つテーブルを列挙します。

```bash
python scripts/discover_channels_table.py
```

### 列型・統計の確認

テーブルの列型、全行数、チャネルごと最新1行の統計を表示します。

```bash
python scripts/inspect_channel_update_types.py
```

---

## セキュリティ

- `.env` は `.gitignore` により Git 管理外
- テーブル名・列名はすべて `_validate_ident()` で識別子として検証し、SQLインジェクションを防止
- クエリは `psycopg2.sql.Composed` で構築（文字列結合なし）
