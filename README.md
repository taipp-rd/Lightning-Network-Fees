# Lightning Network Fee Distribution Visualizer

Lightning Network（LN）のゴシッププロトコルから収集したチャネル更新データを AWS PostgreSQL から取得し、手数料の分布を可視化するツールです。

## 概要

BOLT #7 `channel_update` メッセージに含まれる以下の4種類の手数料について、**チャネルごとに ORDER 時刻が最新の 1 行**を選び、ヒストグラム・ECDF・散布図を生成します。

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
│   ├── run_all.py                      # 全分析を一括実行（期間指定オプションあり）
│   ├── discover_channels_table.py      # 互換テーブルを自動検索
│   └── inspect_channel_update_types.py # 列型・統計の調査
├── src/
│   ├── db/
│   │   ├── connection.py               # PostgreSQL接続（.env読み込み）
│   │   ├── channels_relation.py        # スキーマ.テーブル名の解決
│   │   └── fee_snapshot_query.py     # クエリ組み立て（チャネルごと最新・期間フィルタ）
│   ├── analysis/
│   │   ├── run_helpers.py              # DB取得・ログ出力の共通処理
│   │   ├── time_range_cli.py           # コマンドライン用の期間引数（ISO 8601）
│   │   ├── base_fee.py                 # base_fee_msat 分析
│   │   ├── fee_rate.py                 # fee_rate_ppm 分析
│   │   ├── fee_rate_when_base_fee_zero.py
│   │   ├── inbound_base_fee.py
│   │   ├── inbound_fee_rate.py
│   │   ├── base_fee_vs_fee_rate.py     # 散布図
│   │   └── inbound_base_fee_vs_inbound_fee_rate.py
│   ├── visualization/
│   │   └── charts.py                   # ヒストグラム・ECDF・散布図描画
└── output/                             # 生成グラフの保存先（Git管理外）
```

---

## セットアップ

### 1. 依存パッケージのインストール

```bash
python3 -m venv .venv
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
LN_COLUMN_SNAPSHOT=timestamp
LN_COLUMN_BASE_FEE_MSAT=rp_base_fee_msat
LN_COLUMN_FEE_RATE_PPM=rp_feerate_ppm
LN_COLUMN_INBOUND_BASE_FEE=rp_inbound_base_fee_msat
LN_COLUMN_INBOUND_FEE_RATE=rp_inbound_feerate_ppm
```

### 3. 期間指定を使うときの補足（時刻列が整数の場合）

`channel_update` の `timestamp` 列などが **PostgreSQL の `integer`（Unix 秒など）** の場合、`--time-mode range` で日時を渡すと型不一致になることがあります。そのときは `.env` に次を設定します。

```dotenv
LN_QUERY_TIME_STORAGE=unix_sec    # 秒（int / bigint）
# または
LN_QUERY_TIME_STORAGE=unix_ms    # ミリ秒
```

日時型の列なら **未設定のまま**（内部的に `timestamptz` 相当として `datetime` をバインド）で問題ありません。

---

## 実行方法

### 全分析を一括実行

```bash
python3 -m scripts.run_all
```

プロジェクトルートで実行してください。**7** ステップが順に処理されます。

### クエリ対象の時刻窓（任意）

`scripts.run_all` および各 `src.analysis.*` モジュールに共通のオプションがあります。

| オプション | 説明 |
|------------|------|
| `--time-mode latest` | 既定。期間を絞らない（従来どおり）。 |
| `--time-mode range` | `--time-start` と `--time-end` の **両方**が必須（**両端含む**）。日時は **ISO 8601**（例: `2025-12-01T00:00:00+00:00`）。末尾 `Z` は UTC として解釈されます。 |

**例（2025年12月・UTC）**

```bash
python3 -m scripts.run_all --time-mode range \
  --time-start 2025-12-01T00:00:00+00:00 \
  --time-end 2025-12-31T23:59:59+00:00
```

**例（単体の分析のみ）**

```bash
python3 -m src.analysis.base_fee --time-mode range \
  --time-start 2025-09-01T00:00:00+00:00 \
  --time-end 2025-09-08T23:59:59+00:00
```

`--time-mode latest` のときに `--time-start` / `--time-end` を付けるとエラー終了します。

### 個別に実行

```bash
python3 -m src.analysis.base_fee
python3 -m src.analysis.fee_rate
python3 -m src.analysis.fee_rate_when_base_fee_zero
python3 -m src.analysis.inbound_base_fee
python3 -m src.analysis.inbound_fee_rate
python3 -m src.analysis.base_fee_vs_fee_rate
python3 -m src.analysis.inbound_base_fee_vs_inbound_fee_rate
```

各コマンドは `python3 -m ... --help` で期間オプションを確認できます。

---

## 取得ロジックと期間指定

常に **`DISTINCT ON (chan_id)`** で、ORDER 時刻列（`LN_COLUMN_ORDER_TIME` が無ければ `LN_COLUMN_SNAPSHOT` など）が **最も新しい 1 行**をチャネルごとに採用します。`channel_update` のように行ごとに時刻が異なるテーブルを想定しています。

**`--time-mode range`** のときは、まず ORDER 時刻列が **指定区間に入る行**に限定し、そのうえで **チャネルごとに区間内で最新の 1 行**を採用します。

---

## 生成されるグラフ

出力先は既定で `output/` です。ファイル名は実行ごとに上書きされます。

| ファイル | 内容 | X軸範囲 | ビン幅 | Y軸 |
|---------|------|---------|--------|-----|
| `base_fee_msat.png` | ベース手数料ヒストグラム | 0〜10,000 msat | 100 msat | 対数 |
| `base_fee_msat_0_1000_50msat.png` | ベース手数料（拡大） | 0〜1,000 msat | 50 msat | 線形 |
| `base_fee_msat_cdf.png` | ベース手数料 ECDF | 0〜10,000 msat | — | 累積確率 |
| `fee_rate_ppm.png` | 比例手数料率ヒストグラム | 0〜2,000 ppm | 50 ppm | 線形 |
| `fee_rate_ppm_0_50.png` | 比例手数料率（低レンジ） | 0〜50 ppm | 1 ppm | 線形 |
| `fee_rate_ppm_cdf.png` | 比例手数料率 ECDF | 0〜2,000 ppm | — | 累積確率 |
| `fee_rate_ppm_when_base_fee_0_*.png` | base_fee=0 限定の帯別・低レンジ・ECDF | 同上系 | — | — |
| `inbound_base_fee.png` | インバウンドベース手数料ヒストグラム | −1,000〜500 msat | 50 msat | 対数 |
| `inbound_base_fee_cdf.png` | インバウンドベース手数料 ECDF | −1,000〜500 msat | — | 累積確率 |
| `inbound_fee_rate.png` | インバウンド比例手数料率ヒストグラム | −1,000〜500 ppm | 50 ppm | 対数 |
| `inbound_fee_rate_cdf.png` | インバウンド比例手数料率 ECDF | −1,000〜500 ppm | — | 累積確率 |
| `base_fee_msat_vs_fee_rate_ppm_scatter.png` | base_fee × fee_rate 散布図 | 0〜2,000 msat | — | 0〜2,000 ppm |
| `inbound_base_fee_vs_inbound_fee_rate_scatter.png` | inbound系2変数散布図 | −1,000〜500 msat | — | −1,000〜500 ppm |

---

## 調査用スクリプト

### 互換テーブルの自動検索

DBに接続し、手数料列を持つテーブルを列挙します。

```bash
python3 scripts/discover_channels_table.py
```

### 列型・統計の確認

テーブルの列型、全行数、チャネルごと最新1行の統計を表示します。

```bash
python3 scripts/inspect_channel_update_types.py
```

---

## セキュリティ

- `.env` は `.gitignore` により Git 管理外
- テーブル名・列名はすべて `_validate_ident()` で識別子として検証し、SQLインジェクションを防止
- クエリは `psycopg2.sql.Composed` で構築（文字列結合なし）
- 期間指定の境界値はプレースホルダ経由でバインド（日時は `datetime`、Unix 列は整数に変換してからバインド）
