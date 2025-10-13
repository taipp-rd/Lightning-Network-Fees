#!/usr/bin/env python3
"""
Lightning Network: Proportional Fee Rate Distribution Analysis (Fixed)

Fixed issues:
1. Channel counting: Now counts unique channels
2. Detailed histogram with custom bins
3. Better error handling

Usage:
    python 2_fee_rate_analysis_fixed.py \
        --pg-host HOST --pg-port 5432 --pg-db DBNAME \
        --pg-user USER --pg-pass PASS
"""
import argparse
import sys
from typing import Dict

import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)
plt.rcParams['font.size'] = 11

# --------------------------------------
# Database Configuration
# --------------------------------------
@dataclass
class DBConf:
    host: str
    port: int
    db: str
    user: str
    password: str

# --------------------------------------
# SQL Query: Latest fee rate data (FIXED)
# --------------------------------------
FEE_RATE_SQL_FIXED = r"""
WITH latest_channel AS (
  SELECT DISTINCT ON (cu.chan_id, cu.advertising_nodeid)
         cu.chan_id,
         cu.advertising_nodeid,
         cu.connecting_nodeid,
         COALESCE(cu.rp_feerate_ppm, 0) AS fee_rate_ppm,
         cu.rp_disabled,
         COALESCE(cu.rp_last_update, cu.timestamp) AS last_ts
  FROM channel_update cu
  ORDER BY cu.chan_id, cu.advertising_nodeid, COALESCE(cu.rp_last_update, cu.timestamp) DESC
),
open_channel AS (
  SELECT lc.*
  FROM latest_channel lc
  LEFT JOIN closed_channel cc
    ON cc.chan_id = lc.chan_id
  WHERE cc.chan_id IS NULL
    AND lc.rp_disabled = false
)
SELECT 
    chan_id,
    fee_rate_ppm
FROM open_channel
WHERE fee_rate_ppm >= 0;
"""

# --------------------------------------
# Helper Functions
# --------------------------------------

def fetch_dataframe(conf: DBConf, sql: str) -> pd.DataFrame:
    """Fetch data from PostgreSQL database with error handling."""
    try:
        conn = psycopg2.connect(
            host=conf.host, 
            port=conf.port, 
            dbname=conf.db,
            user=conf.user, 
            password=conf.password,
            connect_timeout=10
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

def get_unique_channel_count(df: pd.DataFrame) -> int:
    """Get count of unique channels."""
    return df['chan_id'].nunique()

def compute_statistics(data: pd.Series) -> Dict:
    """Compute comprehensive statistics for fee rate distribution."""
    return {
        'count': len(data),
        'mean': data.mean(),
        'median': data.median(),
        'std': data.std(),
        'min': data.min(),
        'max': data.max(),
        'q25': data.quantile(0.25),
        'q75': data.quantile(0.75),
        'q90': data.quantile(0.90),
        'q95': data.quantile(0.95),
        'q99': data.quantile(0.99),
        'zero_fee_pct': (data == 0).sum() / len(data) * 100,
        'low_fee_pct': (data <= 100).sum() / len(data) * 100,
        'medium_fee_pct': ((data > 100) & (data <= 1000)).sum() / len(data) * 100,
        'high_fee_pct': (data > 1000).sum() / len(data) * 100
    }

def create_feerate_bins():
    """Create 14-step fee rate bins."""
    bins = [0, 1, 2, 6, 11, 26, 51, 101, 201, 501, 1001, 2001, 5001, 10001, np.inf]
    labels = [
        '0', '1', '2-5', '6-10', '11-25', '26-50', '51-100', '101-200',
        '201-500', '501-1000', '1001-2000', '2001-5000', '5001-10000', '10000+'
    ]
    return bins, labels

def plot_detailed_histogram(df: pd.DataFrame, unique_channels: int,
                           output_file: str = "2_fee_rate_distribution_fixed.png"):
    """Create detailed 14-step histogram for fee rates."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    fees = df['fee_rate_ppm'].values
    stats = compute_statistics(df['fee_rate_ppm'])
    
    bins, labels = create_feerate_bins()
    fee_categories = pd.cut(fees, bins=bins, labels=labels, right=False)
    category_counts = fee_categories.value_counts().sort_index()
    
    colors = plt.cm.plasma(np.linspace(0.3, 0.9, len(category_counts)))
    bars = ax.bar(range(len(category_counts)), category_counts.values,
                   color=colors, edgecolor='black', linewidth=1.5, alpha=0.8)
    
    ax.set_xlabel('Fee Rate (ppm)', fontsize=14, fontweight='bold')
    ax.set_ylabel('チャネル数', fontsize=14, fontweight='bold')
    ax.set_title('Fee Rate 詳細分布 (14段階)', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(range(len(category_counts)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    for i, (bar, count) in enumerate(zip(bars, category_counts.values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count):,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    stats_text = f"""統計サマリー:
━━━━━━━━━━━━━━━
ユニークチャネル数: {unique_channels:,}
チャネル方向数: {len(fees):,}
━━━━━━━━━━━━━━━
平均: {stats['mean']:.0f} ppm
中央値: {stats['median']:.0f} ppm
標準偏差: {stats['std']:.0f} ppm
━━━━━━━━━━━━━━━
ゼロ手数料: {stats['zero_fee_pct']:.1f}%
低 (≤100): {stats['low_fee_pct']:.1f}%
中 (100-1000): {stats['medium_fee_pct']:.1f}%
高 (>1000): {stats['high_fee_pct']:.1f}%
"""
    
    ax.text(0.98, 0.97, stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            family='monospace')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()
    
    return category_counts

def main():
    parser = argparse.ArgumentParser(
        description="Lightning Network Fee Rate Distribution Analysis (Fixed)"
    )
    
    parser.add_argument("--pg-host", required=True, help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-db", required=True, help="PostgreSQL database name")
    parser.add_argument("--pg-user", required=True, help="PostgreSQL username")
    parser.add_argument("--pg-pass", required=True, help="PostgreSQL password")
    parser.add_argument("--output", default="2_fee_rate_distribution_fixed.png", 
                       help="Output file name")
    
    args = parser.parse_args()
    
    conf = DBConf(
        host=args.pg_host,
        port=args.pg_port,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_pass
    )
    
    print("[INFO] Connecting to database...", file=sys.stderr)
    df = fetch_dataframe(conf, FEE_RATE_SQL_FIXED)
    
    unique_channels = get_unique_channel_count(df)
    total_directions = len(df)
    
    print(f"[INFO] Fetched {total_directions:,} channel directions", file=sys.stderr)
    print(f"[INFO] Unique channels: {unique_channels:,}", file=sys.stderr)
    
    if len(df) == 0:
        print("[ERROR] No data retrieved.", file=sys.stderr)
        sys.exit(1)
    
    stats = compute_statistics(df['fee_rate_ppm'])
    
    print("\n" + "="*60)
    print("  PROPORTIONAL FEE RATE STATISTICS")
    print("="*60)
    print(f"Unique Channels:    {unique_channels:,}")
    print(f"Channel Directions: {total_directions:,}")
    print(f"Mean:               {stats['mean']:.2f} ppm")
    print(f"Median:             {stats['median']:.2f} ppm")
    print(f"Zero fee:           {stats['zero_fee_pct']:.2f}%")
    print("="*60 + "\n")
    
    print("[INFO] Generating detailed histogram...", file=sys.stderr)
    category_counts = plot_detailed_histogram(df, unique_channels, args.output)
    
    csv_file = args.output.replace('.png', '_stats.csv')
    stats_df = pd.DataFrame([stats])
    stats_df.to_csv(csv_file, index=False)
    print(f"✅ Saved statistics: {csv_file}")
    
    category_file = args.output.replace('.png', '_categories.csv')
    category_counts.to_csv(category_file, header=['count'])
    print(f"✅ Saved category distribution: {category_file}")
    
    print("\n[INFO] Analysis complete!")

if __name__ == "__main__":
    main()
