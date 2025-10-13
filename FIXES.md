# 修正内容の詳細 (FIXES.md)

## 修正の概要

このドキュメントは、Lightning Network手数料分析ツールに加えられた修正と改善をまとめたものです。

---

## 🔧 修正された問題

### 1. チャネル数の不正確なカウント

**問題の詳細:**
- 元のコードは `chan_id` と `advertising_nodeid` の組み合わせを個別にカウント
- 各チャネルには2つの方向（両ノードからのポリシー）があるため、実際のチャネル数の約2倍が報告されていた
- ユーザー報告: 実際49,296チャネルなのに75,773と表示

**修正内容:**
```python
# 修正前
SELECT DISTINCT ON (cu.chan_id, cu.advertising_nodeid)
    ...
FROM channel_update cu
-- 結果: チャネル方向数（約75,773）

# 修正後
SELECT DISTINCT ON (cu.chan_id, cu.advertising_nodeid)
    cu.chan_id,  # chan_idを追加
    ...
FROM channel_update cu

# Pythonコードで正確にカウント
unique_channels = df['chan_id'].nunique()  # ユニークチャネル数
total_directions = len(df)  # チャネル方向数

# 両方を表示
print(f"ユニークチャネル数: {unique_channels:,}")
print(f"チャネル方向数: {total_directions:,}")
```

**影響:**
- ✅ ユーザーは正確なチャネル数を確認可能
- ✅ 統計の解釈が正確になった
- ✅ 学術研究での引用時の信頼性向上

---

### 2. グラフ形式の不一致

**問題の詳細:**
- ユーザーは14段階の詳細なヒストグラムを期待
- 元のコードは4パネルの標準的な可視化のみ提供
- ビン数が100で、特定の範囲の詳細が不明瞭

**修正内容:**
```python
def create_fee_bins():
    """14段階のビン区分"""
    bins = [0, 1, 2, 6, 11, 26, 51, 101, 201, 501, 1001, 2001, 5001, 10001, np.inf]
    labels = [
        '0', '1', '2-5', '6-10', '11-25', '26-50', '51-100', '101-200',
        '201-500', '501-1000', '1001-2000', '2001-5000', '5001-10000', '10000+'
    ]
    return bins, labels

# カテゴリー別に集計
fee_categories = pd.cut(fees, bins=bins, labels=labels, right=False)
category_counts = fee_categories.value_counts().sort_index()

# 棒グラフで可視化
bars = ax.bar(range(len(category_counts)), category_counts.values, ...)
```

**影響:**
- ✅ ユーザー期待に沿ったグラフ形式
- ✅ 手数料分布の詳細な傾向を把握可能
- ✅ カテゴリー別CSV出力で後続分析が容易

---

### 3. データベース接続エラーの不適切な処理

**問題の詳細:**
- 一括実行スクリプトで接続エラーが発生
- エラーメッセージが不明瞭
- タイムアウトがなく、応答なしで待機

**修正内容:**

**Pythonコード:**
```python
def fetch_dataframe(conf: DBConf, sql: str) -> pd.DataFrame:
    """エラーハンドリングを強化"""
    try:
        conn = psycopg2.connect(
            host=conf.host, 
            port=conf.port, 
            dbname=conf.db,
            user=conf.user, 
            password=conf.password,
            connect_timeout=10  # 10秒タイムアウト追加
        )
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Query execution failed: {e}", file=sys.stderr)
        sys.exit(1)
```

**一括実行スクリプト:**
```bash
# 事前接続テストを追加
echo "[TEST] Testing database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='${HOST}', port=${PORT}, dbname='${DB}',
        user='${USER}', password='${PASS}', connect_timeout=10
    )
    conn.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"

# エラーハンドリングとログ出力
if python3 "${script}" ... 2>&1 | tee "${OUTPUT_DIR}/${name}_log.txt"; then
    echo "✓ ${name} complete"
else
    echo "✗ ${name} failed (see ${OUTPUT_DIR}/${name}_log.txt)"
fi
```

**影響:**
- ✅ 早期にエラーを検出
- ✅ 明確なエラーメッセージ
- ✅ ログファイルによるデバッグの容易化

---

## 📊 新機能

### 1. カテゴリー別分布CSV

**内容:**
```csv
category,count
0,350000
1,820000
2-5,120000
...
```

**用途:**
- 後続分析での使用
- 他のツールへのインポート
- 時系列比較

### 2. 統計サマリーの拡張

**追加項目:**
```python
stats = {
    'unique_channels': unique_channels,  # 新規追加
    'count': total_directions,           # 既存（チャネル方向数）
    ...
}
```

### 3. ログファイルの自動生成

一括実行時に各スクリプトのログを自動保存：
```
results_fixed_YYYYMMDD_HHMMSS/
  ├── 1_base_fee_log.txt
  ├── 2_fee_rate_log.txt
  ├── 3_inbound_base_fee_log.txt
  └── 4_inbound_feerate_log.txt
```

---

## 🔄 互換性

### 従来版との関係

- **従来版スクリプト**: そのまま残存（後方互換性）
- **修正版スクリプト**: `*_fixed.py` として追加
- **推奨**: 新規ユーザーは修正版を使用

### ファイル名の対応

| 従来版 | 修正版 |
|--------|--------|
| `1_base_fee_analysis.py` | `1_base_fee_analysis_fixed.py` |
| `2_fee_rate_analysis.py` | `2_fee_rate_analysis_fixed.py` |
| `run_all_analyses.sh` | `run_all_analyses_fixed.sh` |
| `run_all_analyses.bat` | `run_all_analyses_fixed.bat` |

### 出力ファイルの違い

**従来版:**
- `*_distribution.png` - 4パネル可視化
- `*_stats.csv` - 基本統計
- `*_data.csv` - 全データ

**修正版:**
- `*_fixed.png` - 14段階ヒストグラム
- `*_stats.csv` - 拡張統計（ユニークチャネル数含む）
- `*_categories.csv` - カテゴリー別分布（新規）
- `*_original.png` - 4パネル可視化（オプション）

---

## 🧪 テスト方法

### 1. 基本動作確認

```bash
# データベース接続テスト
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost', port=5432, dbname='lndb',
    user='readonly', password='secret', connect_timeout=10
)
print('Connection OK')
conn.close()
"

# 修正版スクリプト実行
python 1_base_fee_analysis_fixed.py \
    --pg-host localhost --pg-port 5432 \
    --pg-db lndb --pg-user readonly --pg-pass secret
```

### 2. チャネル数検証

```python
# 期待される結果
# ユニークチャネル数: 約49,000-50,000
# チャネル方向数: 約98,000-100,000（2倍）

# 確認方法
import pandas as pd
df = pd.read_csv('1_base_fee_distribution_fixed_data.csv')
print(f"Unique channels: {df['chan_id'].nunique()}")
print(f"Total directions: {len(df)}")
```

### 3. グラフ検証

期待されるグラフ:
- X軸: 14個のカテゴリーラベル
- Y軸: チャネル数
- 各バーの上に数値表示
- 右上に統計サマリー

---

## 📝 マイグレーションガイド

### 既存ユーザー向け

#### ステップ1: 修正版スクリプトのダウンロード

```bash
cd Lightning-Network-Fees
git pull origin main
```

#### ステップ2: 実行権限の付与

```bash
chmod +x run_all_analyses_fixed.sh
```

#### ステップ3: 実行

```bash
# 従来版（非推奨）
./run_all_analyses.sh localhost 5432 lndb readonly secret

# 修正版（推奨）
./run_all_analyses_fixed.sh localhost 5432 lndb readonly secret
```

#### ステップ4: 結果の比較

```bash
# 従来版出力
results_YYYYMMDD_HHMMSS/

# 修正版出力
results_fixed_YYYYMMDD_HHMMSS/
```

---

## 🐛 既知の制限事項

### 1. Inbound手数料分析

- 修正版は現在、base_feeとfee_rateのみ対応
- inbound手数料分析は従来版を使用

### 2. 大規模データセット

- 100万件以上のレコードでメモリ不足の可能性
- 必要に応じてサンプリング実装

### 3. タイムゾーン

- タイムスタンプはUTC想定
- ローカルタイムゾーンでの集計は未対応

---

## 🔮 今後の予定

### 短期（1-2週間）

- [x] チャネル数修正
- [x] 詳細ヒストグラム
- [x] エラーハンドリング
- [ ] Inbound手数料の修正版
- [ ] 統計的検定の追加

### 中期（1-2ヶ月）

- [ ] 時系列分析機能
- [ ] インタラクティブなダッシュボード
- [ ] ドキュメントの多言語化

### 長期（3ヶ月以上）

- [ ] 機械学習による予測
- [ ] リアルタイム監視
- [ ] API提供

---

## 📞 サポート

### 問題報告

GitHub Issues: https://github.com/taipp-rd/Lightning-Network-Fees/issues

### 貢献

Pull Requestsを歓迎します！

---

**最終更新**: 2025-10-13
**バージョン**: 2.0.0 (Fixed)
