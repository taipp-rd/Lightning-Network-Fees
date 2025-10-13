# Lightning Network 手数料分布分析

Lightning Networkにおける手数料構造の包括的な分析ツール。基本手数料、比例手数料、およびInbound手数料を分析します。

## 概要

このリポジトリには、Lightning Networkのルーティング手数料のさまざまな側面を分析する4つのスクリプトが含まれています：

1. **基本手数料分析** (`1_base_fee_analysis.py`) - 支払いごとの固定手数料の分布
2. **比例手数料分析** (`2_fee_rate_analysis.py`) - 支払い額に比例する手数料の分布
3. **Inbound基本手数料分析** (`3_inbound_base_fee_analysis.py`) - 受信時の固定手数料の分布
4. **Inbound比例手数料分析** (`4_inbound_feerate_analysis.py`) - 受信時の比例手数料の分布

## 理論的背景

Lightning Networkのルーティング手数料は2つの要素で構成されます：

### Outbound手数料
- **基本手数料 (rp_base_fee_msat)**: 支払い額に関係なく課される固定手数料
- **比例手数料 (rp_feerate_ppm)**: 支払い額に比例する手数料（百万分率で表現）

### Inbound手数料
- **Inbound基本手数料 (rp_inbound_base_fee_msat)**: 支払い受信時の固定手数料
- **Inbound比例手数料 (rp_inbound_feerate_ppm)**: 支払い受信時の比例手数料

Inbound手数料は、ペイメントチャネルにおける**流動性不均衡問題**に対処するもので、ノードは以下が可能になります：
- 流入する流動性に対して手数料を課金
- チャネル残高に基づいて動的に価格調整
- バランスの取れたチャネル状態を促進

## 学術的参考文献

- **Pickhardt & Richter (2021)**: "Optimally Reliable & Cheap Payment Flows on the Lightning Network" - https://arxiv.org/abs/2107.05322
- **Rohrer et al. (2019)**: "Discharged Payment Channels: Quantifying the Lightning Network's Resilience" - https://arxiv.org/abs/1904.10253
- **Pickhardt & Richter (2022)**: "A Mathematical Theory of Payment Channel Networks"
- **Nisslmueller et al. (2023)**: "Towards Fee Estimation in Lightning Network"
- **Tikhomirov et al. (2020)**: "Quantifying Blockchain Extractable Value"

## 必要な環境

```bash
pip install -r requirements.txt
```

## データベースセットアップ

これらのスクリプトは、以下のテーブルを含むLightning Networkグラフデータを格納したPostgreSQLデータベースに接続します：

- `channel_update`: チャネルのルーティングポリシーと手数料
- `closed_channel`: 過去のチャネル閉鎖記録
- `node_announcement`: ノードのメタデータとエイリアス

### テーブル構造

#### channel_update
- `chan_id`: チャネル識別子
- `advertising_nodeid`: ポリシーを告知するノード
- `connecting_nodeid`: 接続先ノード
- `rp_base_fee_msat`: Outbound基本手数料（ミリサトシ）
- `rp_feerate_ppm`: Outbound比例手数料（百万分率）
- `rp_inbound_base_fee_msat`: Inbound基本手数料
- `rp_inbound_feerate_ppm`: Inbound比例手数料
- `rp_disabled`: チャネルが無効かどうか
- `rp_last_update`: 最終ポリシー更新タイムスタンプ
- `timestamp`: レコード作成タイムスタンプ

## 使用方法

### 1. 基本手数料分析

```bash
python 1_base_fee_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**出力:**
- `1_base_fee_distribution.png`: マルチパネル可視化
- `1_base_fee_distribution_stats.csv`: 統計サマリー
- `1_base_fee_distribution_data.csv`: 生データ

**可視化内容:**
- 線形ヒストグラム: 全体的な分布
- 対数スケールヒストグラム: 裾野の挙動
- CDF: 累積確率
- ボックスプロット: 外れ値検出

### 2. 比例手数料分析

```bash
python 2_fee_rate_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**出力:**
- `2_fee_rate_distribution.png`: マルチパネル可視化
- `2_fee_rate_distribution_stats.csv`: 統計サマリー
- `2_fee_rate_distribution_data.csv`: 生データ

**可視化内容:**
- 線形ヒストグラム: 手数料率の分布
- 対数スケールヒストグラム: 高手数料チャネル
- CDF: 手数料パーセンタイル
- バイオリンプロット: 密度推定

### 3. Inbound基本手数料分析

```bash
python 3_inbound_base_fee_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**出力:**
- `3_inbound_base_fee_distribution.png`: マルチパネル可視化
- `3_inbound_base_fee_distribution_stats.csv`: 統計サマリー
- `3_inbound_base_fee_distribution_data.csv`: 生データ

**可視化内容:**
- 線形ヒストグラム: Inbound手数料分布
- 対数スケールヒストグラム: 正の手数料
- CDF: 累積分布
- 散布図: InboundとOutboundの比較

### 4. Inbound比例手数料分析

```bash
python 4_inbound_feerate_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**出力:**
- `4_inbound_feerate_distribution.png`: マルチパネル可視化
- `4_inbound_feerate_distribution_stats.csv`: 統計サマリー
- `4_inbound_feerate_distribution_data.csv`: 生データ

**可視化内容:**
- 線形ヒストグラム: 分布
- 対数スケールヒストグラム: 正の手数料
- CDF: パーセンタイル分析
- 散布図: InboundとOutbound
- ヒートマップ: 手数料パターン分析

## データ選択戦略

すべてのスクリプトは以下のデータフィルタリングアプローチを実装しています：

1. **最新レコードのみ**: `DISTINCT ON (chan_id, advertising_nodeid)` と `ORDER BY timestamp DESC` を使用して、各チャネル方向の最新のルーティングポリシーを取得

2. **オープンチャネルのみ**: `closed_channel` テーブルとのLEFT JOINでクローズドチャネルを除外

3. **有効なチャネルのみ**: 無効なチャネル（`rp_disabled = false`）を除外

4. **有効な手数料**: 無効またはNULLの手数料値を除外

これにより、分析がLightning Networkの**現在の状態**を反映します（約40,000〜50,000のアクティブチャネル）。

## 計算される主要統計量

各スクリプトは包括的な統計を計算します：

- **中心傾向**: 平均、中央値
- **ばらつき**: 標準偏差、最小値、最大値
- **パーセンタイル**: Q25、Q75、Q90、Q95、Q99
- **手数料カテゴリ**: 
  - ゼロ手数料チャネル（%）
  - 低手数料チャネル（≤100 ppm または同等の基本手数料）
  - 中手数料チャネル（100-1000 ppm）
  - 高手数料チャネル（>1000 ppm）
  - 正と負の手数料（Inbound手数料の場合）


### PostgreSQLクエリ最適化

SQLクエリは以下を使用：
- 効率的な重複排除のための`DISTINCT ON`
- NULL処理のための`COALESCE`
- 除外ロジックのための`LEFT JOIN`
- `chan_id`、`advertising_nodeid`、`timestamp`への適切なインデックスを推奨

### 可視化技術

1. **ヒストグラム**: 頻度分布を表示
2. **対数スケール**: 偏った分布の裾野の挙動を明らかに
3. **CDF**: 「手数料 ≤ X のチャネルは何%か？」に回答
4. **ボックスプロット**: 統計的に外れ値を特定
5. **バイオリンプロット**: ボックスプロットとカーネル密度推定を組み合わせ
6. **散布図**: InboundとOutbound手数料の相関
7. **ヒートマップ**: パターン認識のための2D密度

### 統計手法

- **パーセンタイル**: ノンパラメトリック、外れ値に頑健
- **ボックスプロット**: IQR法による外れ値検出
- **カーネル密度**: 滑らかな確率密度推定
- **累積分布**: 単調、解釈可能な確率

## 研究への応用

これらの分析ツールは以下の研究をサポートできます：

1. **ルーティング経済学**: 手数料構造とインセンティブの理解
2. **ネットワークトポロジー**: 手数料とネットワーク位置の関係
3. **流動性管理**: Inbound手数料の採用と有効性
4. **支払い実現可能性**: 異なる支払いサイズに対する手数料の影響
5. **ノード戦略**: ルーティングノードの最適な手数料設定
6. **市場動態**: 手数料競争と時間経過による進化

## 一括実行

### Unix/Linux/macOS

```bash
chmod +x run_all_analyses.sh
./run_all_analyses.sh localhost 5432 lndb readonly secret
```

### Windows

```cmd
run_all_analyses.bat localhost 5432 lndb readonly secret
```

すべての結果は `results_YYYYMMDD_HHMMSS` ディレクトリに保存されます。

## 今後の拡張案

以下の追加が可能です：

- 時系列分析: 手数料の時間経過による進化
- 地理的分析: 地域別の手数料差異
- 容量相関: 手数料とチャネルサイズの関係
- ノード中心性: ハブノードの手数料戦略
- 経路探索: 最適ルートに対する手数料の影響
- 予測モデリング: 手数料予測


## ライセンス

MIT License 

---

**注意**: Lightning Networkデータにアクセスして分析する前に、適切な許可を得ていることを確認してください。ノード運営者のプライバシーを尊重し、責任ある開示慣行に従ってください。
