# Lightning Network 手数料分布分析

Lightning Networkにおける手数料構造の包括的な分析ツール。基本手数料、比例手数料、およびInbound手数料を分析します。

## 🆕 修正版 (Fixed Version) - 重要な更新

以下の問題を修正した新バージョンを追加しました:

1. **✅ チャネル数の正確なカウント**: 各チャネル方向ではなく、ユニークチャネル数を正しくカウント
2. **✅ 14段階詳細ヒストグラム**: 詳細な分布グラフを生成
3. **✅ データベース接続エラー処理**: 接続テストとエラーハンドリングを改善

### 修正版スクリプト（推奨）

- `1_base_fee_analysis_fixed.py` - 基本手数料分析（修正版）
- `2_fee_rate_analysis_fixed.py` - 比例手数料分析（修正版）
- `run_all_analyses_fixed.sh` - 一括実行（Unix/Linux/macOS）
- `run_all_analyses_fixed.bat` - 一括実行（Windows）

### クイックスタート（修正版）

```bash
# Unix/Linux/macOS
chmod +x run_all_analyses_fixed.sh
./run_all_analyses_fixed.sh localhost 5432 lndb readonly secret

# Windows
run_all_analyses_fixed.bat localhost 5432 lndb readonly secret
```

### 主な改善点

#### チャネル数の正確性
- **従来版**: ~75,773 チャネル方向
- **修正版**: ~49,296 ユニークチャネル（正確）

#### 14段階詳細ヒストグラム
```
0, 1, 2-5, 6-10, 11-25, 26-50, 51-100, 101-200, 
201-500, 501-1000, 1001-2000, 2001-5000, 5001-10000, 10000+
```

---

## 概要

Lightning Networkのルーティング手数料を分析する4つのスクリプト：

1. **基本手数料分析** - 支払いごとの固定手数料
2. **比例手数料分析** - 支払い額に比例する手数料
3. **Inbound基本手数料分析** - 受信時の固定手数料
4. **Inbound比例手数料分析** - 受信時の比例手数料

## 理論的背景

### Outbound手数料
- **基本手数料 (rp_base_fee_msat)**: 固定手数料
- **比例手数料 (rp_feerate_ppm)**: 金額比例手数料

### Inbound手数料
- **Inbound基本手数料**: 受信時固定手数料
- **Inbound比例手数料**: 受信時比例手数料

Inbound手数料は流動性管理のための重要なツールです。

## 学術的参考文献

- Pickhardt & Richter (2021): "Optimally Reliable & Cheap Payment Flows"
- Rohrer et al. (2019): "Discharged Payment Channels"
- Nisslmueller et al. (2023): "Towards Fee Estimation in Lightning Network"

## 必要な環境

```bash
pip install -r requirements.txt
```

## 使用方法（従来版）

### 個別実行

```bash
python 1_base_fee_analysis.py \
    --pg-host localhost --pg-port 5432 \
    --pg-db lndb --pg-user readonly --pg-pass secret
```

### 一括実行

```bash
# Unix/Linux/macOS
./run_all_analyses.sh localhost 5432 lndb readonly secret

# Windows
run_all_analyses.bat localhost 5432 lndb readonly secret
```

## トラブルシューティング

### データベース接続エラー

**エラー**: `psycopg2.OperationalError: could not connect to server`

**解決策**:
1. PostgreSQLサーバーが起動しているか確認
2. ホスト名、ポート、データベース名を確認
3. ファイアウォール設定を確認
4. 修正版スクリプト（`*_fixed.py`）を使用

### チャネル数の不一致

**問題**: 表示されるチャネル数が実際と異なる

**解決策**: 修正版スクリプト（`*_fixed.py`）を使用してください。

## 出力ファイル

### 修正版
- `*_fixed.png` - 14段階詳細ヒストグラム
- `*_stats.csv` - 統計サマリー
- `*_categories.csv` - カテゴリー別分布
- `*_log.txt` - 実行ログ

### 従来版
- `*_distribution.png` - 4パネル可視化
- `*_stats.csv` - 統計サマリー
- `*_data.csv` - 生データ

## データ選択戦略

1. **最新レコード**: `DISTINCT ON` で各チャネル方向の最新ポリシーを取得
2. **オープンチャネルのみ**: クローズドチャネルを除外
3. **有効なチャネル**: `rp_disabled = false`
4. **有効な手数料**: NULL値を除外

## 計算される統計量

- 中心傾向: 平均、中央値
- ばらつき: 標準偏差、最小値、最大値
- パーセンタイル: Q25、Q75、Q90、Q95、Q99
- 手数料カテゴリ: ゼロ/低/中/高

## 技術的注釈

### PostgreSQL最適化
- `DISTINCT ON` による効率的な重複排除
- `COALESCE` によるNULL処理
- `LEFT JOIN` による除外ロジック

### 可視化技術
1. ヒストグラム: 頻度分布
2. 対数スケール: 裾野の挙動
3. CDF: 累積確率
4. ボックスプロット: 外れ値検出
5. バイオリンプロット: 密度推定
6. 散布図: 相関分析
7. ヒートマップ: 2D密度

## 研究への応用

1. ルーティング経済学
2. ネットワークトポロジー
3. 流動性管理
4. 支払い実現可能性
5. ノード戦略
6. 市場動態

## 今後の拡張案

- ✅ 修正版スクリプト（実装済み）
- ✅ 詳細ヒストグラム（実装済み）
- ✅ エラーハンドリング（実装済み）
- 時系列分析
- 地理的分析
- 容量相関
- ノード中心性
- 予測モデリング

## ライセンス

MIT License

## 引用

```bibtex
@software{lightning_fee_analysis,
  title = {Lightning Network 手数料分布分析},
  author = {taipp-rd},
  year = {2025},
  url = {https://github.com/taipp-rd/Lightning-Network-Fees}
}
```

## お問い合わせ

GitHub Issues: https://github.com/taipp-rd/Lightning-Network-Fees/issues

---

**注意**: Lightning Networkデータにアクセスする前に適切な許可を得てください。
