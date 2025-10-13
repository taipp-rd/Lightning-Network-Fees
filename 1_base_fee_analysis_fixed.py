#!/usr/bin/env python3
"""
Lightning Network: Base Fee Distribution Analysis (Fixed)

Fixed issues:
1. Channel counting: Now counts unique channels, not channel directions
2. Histogram bins: Matches the 14-step detailed distribution
3. Better error handling and validation

Usage:
    python 1_base_fee_analysis_fixed.py \
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
# SQL Query: Latest base fee data (FIXED)
# --------------------------------------
BASE_FEE_SQL_FIXED = r"""
WITH latest_channel AS (
  -- Get latest update for each channel direction
  SELECT DISTINCT ON (cu.chan_id, cu.advertising_nodeid)
         cu.chan_id,
         cu.advertising_nodeid,
         cu.connecting_nodeid,
         COALESCE(cu.rp_base_fee_msat, 0) AS base_fee_msat,
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
  WHERE cc.chan_id IS NULL  -- Only open channels
    AND lc.rp_disabled = false  -- Only enabled channels
)
SELECT 
    chan_id,
    base_fee_msat
FROM open_channel
WHERE base_fee_msat >= 0;
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
    """Get count of unique channels (not channel directions)."""
    return df['chan_id'].nunique()

def compute_statistics(data: pd.Series) -> Dict:
    """Compute comprehensive statistics for fee distribution."""
    return {
        'count': len(data),
        'unique_channels': len(data),  # Will be updated in main
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
        'zero_fee_pct': (data == 0).sum() / len(data) * 100
    }

def create_fee_bins():
    """
    Create 14-step fee bins matching the reference image.
    
    Bins: 0, 1, 2-5, 6-10, 11-25, 26-50, 51-100, 101-200, 
          201-500, 501-1000, 1001-2000, 2001-5000, 5001-10000, 10000+
    """
    bins = [0, 1, 2, 6, 11, 26, 51, 101, 201, 501, 1001, 2001, 5001, 10001, np.inf]
    labels = [
        '0', '1', '2-5', '6-10', '11-25', '26-50', '51-100', '101-200',
        '201-500', '501-1000', '1001-2000', '2001-5000', '5001-10000', '10000+'
    ]
    return bins, labels

def plot_detailed_histogram(df: pd.DataFrame, unique_channels: int, 
                           output_file: str = "1_base_fee_distribution_fixed.png"):
    """
    Create detailed 14-step histogram matching the reference image.
    """
    fig, ax = plt.subplots(figsize=(14, 8))
    
    fees = df['base_fee_msat'].values
    stats = compute_statistics(df['base_fee_msat'])
    stats['unique_channels'] = unique_channels
    
    # Create bins
    bins, labels = create_fee_bins()
    
    # Categorize data
    fee_categories = pd.cut(fees, bins=bins, labels=labels, right=False)
    category_counts = fee_categories.value_counts().sort_index()
    
    # Create bar plot
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(category_counts)))
    bars = ax.bar(range(len(category_counts)), category_counts.values, 
                   color=colors, edgecolor='black', linewidth=1.5, alpha=0.8)
    
    # Customize
    ax.set_xlabel('Base Fee (msat)', fontsize=14, fontweight='bold')
    ax.set_ylabel('チャネル数', fontsize=14, fontweight='bold')
    ax.set_title('Fee Rate 詳細分布 (14段階)', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(range(len(category_counts)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, category_counts.values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count):,}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Add statistics box
    stats_text = f"""統計サマリー:
━━━━━━━━━━━━━━━
ユニークチャネル数: {unique_channels:,}
チャネル方向数: {len(fees):,}
━━━━━━━━━━━━━━━
平均: {stats['mean']:.0f} msat
中央値: {stats['median']:.0f} msat
標準偏差: {stats['std']:.0f} msat
━━━━━━━━━━━━━━━
最小値: {stats['min']:.0f} msat
Q25: {stats['q25']:.0f} msat
Q75: {stats['q75']:.0f} msat
最大値: {stats['max']:.0f} msat
━━━━━━━━━━━━━━━
ゼロ手数料: {stats['zero_fee_pct']:.1f}%
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

def plot_base_fee_distribution_original(df: pd.DataFrame, unique_channels: int,
                                       output_file: str = "1_base_fee_distribution_original.png"):
    """
    Create the original 4-panel visualization (kept for compatibility).
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    fees = df['base_fee_msat'].values
    stats = compute_statistics(df['base_fee_msat'])
    stats['unique_channels'] = unique_channels
    
    # 1. Linear histogram
    ax1 = axes[0, 0]
    ax1.hist(fees, bins=100, edgecolor='black', alpha=0.7, color='steelblue')
    ax1.axvline(stats['median'], color='red', linestyle='--', linewidth=2, 
                label=f"Median: {stats['median']:.0f} msat")
    ax1.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, 
                label=f"Mean: {stats['mean']:.0f} msat")
    ax1.set_xlabel('Base Fee (msat)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
    ax1.set_title('Base Fee Distribution (Linear Scale)', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. Log-scale histogram
    ax2 = axes[0, 1]
    fees_log = fees[fees > 0]
    if len(fees_log) > 0:
        ax2.hist(fees_log, bins=100, edgecolor='black', alpha=0.7, color='forestgreen')
        ax2.set_xscale('log')
        ax2.axvline(stats['median'], color='red', linestyle='--', linewidth=2, 
                    label=f"Median: {stats['median']:.0f} msat")
        ax2.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, 
                    label=f"Mean: {stats['mean']:.0f} msat")
    ax2.set_xlabel('Base Fee (msat, log scale)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
    ax2.set_title('Base Fee Distribution (Log Scale)', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. Cumulative Distribution Function (CDF)
    ax3 = axes[1, 0]
    sorted_fees = np.sort(fees)
    cumulative = np.arange(1, len(sorted_fees) + 1) / len(sorted_fees) * 100
    ax3.plot(sorted_fees, cumulative, linewidth=2, color='purple')
    ax3.axhline(50, color='red', linestyle='--', linewidth=1, alpha=0.7, label='50th percentile')
    ax3.axhline(90, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='90th percentile')
    ax3.axvline(stats['median'], color='red', linestyle=':', linewidth=1, alpha=0.7)
    ax3.axvline(stats['q90'], color='orange', linestyle=':', linewidth=1, alpha=0.7)
    ax3.set_xlabel('Base Fee (msat)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Cumulative Percentage (%)', fontsize=12, fontweight='bold')
    ax3.set_title('Cumulative Distribution Function (CDF)', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 4. Box plot
    ax4 = axes[1, 1]
    bp = ax4.boxplot(fees, vert=True, patch_artist=True, widths=0.5)
    bp['boxes'][0].set_facecolor('lightcoral')
    bp['medians'][0].set_color('darkred')
    bp['medians'][0].set_linewidth(2)
    ax4.set_ylabel('Base Fee (msat)', fontsize=12, fontweight='bold')
    ax4.set_title('Box Plot (Outlier Detection)', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add statistics text box
    stats_text = f"""
    Statistics Summary:
    ─────────────────────
    Unique Channels: {unique_channels:,}
    Channel Directions: {len(fees):,}
    ─────────────────────
    Mean: {stats['mean']:.0f} msat
    Median: {stats['median']:.0f} msat
    Std Dev: {stats['std']:.0f} msat
    ─────────────────────
    Min: {stats['min']:.0f} msat
    Q25: {stats['q25']:.0f} msat
    Q75: {stats['q75']:.0f} msat
    Q90: {stats['q90']:.0f} msat
    Q95: {stats['q95']:.0f} msat
    Q99: {stats['q99']:.0f} msat
    Max: {stats['max']:.0f} msat
    ─────────────────────
    Zero Fee: {stats['zero_fee_pct']:.2f}%
    """
    
    fig.text(0.98, 0.5, stats_text, 
             fontsize=10, 
             family='monospace',
             verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('Lightning Network: Base Fee Distribution Analysis', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout(rect=[0, 0, 0.95, 0.99])
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

# --------------------------------------
# Main Function
# --------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Lightning Network Base Fee Distribution Analysis (Fixed)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--pg-host", required=True, help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-db", required=True, help="PostgreSQL database name")
    parser.add_argument("--pg-user", required=True, help="PostgreSQL username")
    parser.add_argument("--pg-pass", required=True, help="PostgreSQL password")
    parser.add_argument("--output", default="1_base_fee_distribution_fixed.png", 
                       help="Output file name")
    parser.add_argument("--original-format", action="store_true",
                       help="Also generate original 4-panel format")
    
    args = parser.parse_args()
    
    conf = DBConf(
        host=args.pg_host,
        port=args.pg_port,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_pass
    )
    
    # Fetch data
    print("[INFO] Connecting to database...", file=sys.stderr)
    print(f"[INFO] Host: {conf.host}:{conf.port}, Database: {conf.db}", file=sys.stderr)
    df = fetch_dataframe(conf, BASE_FEE_SQL_FIXED)
    
    # Count unique channels
    unique_channels = get_unique_channel_count(df)
    total_directions = len(df)
    
    print(f"[INFO] Fetched {total_directions:,} channel directions", file=sys.stderr)
    print(f"[INFO] Unique channels: {unique_channels:,}", file=sys.stderr)
    
    if len(df) == 0:
        print("[ERROR] No data retrieved.", file=sys.stderr)
        sys.exit(1)
    
    # Compute and display statistics
    stats = compute_statistics(df['base_fee_msat'])
    stats['unique_channels'] = unique_channels
    
    print("\n" + "="*60)
    print("  BASE FEE STATISTICS")
    print("="*60)
    print(f"Unique Channels:    {unique_channels:,}")
    print(f"Channel Directions: {total_directions:,}")
    print(f"Mean:               {stats['mean']:.2f} msat")
    print(f"Median:             {stats['median']:.2f} msat")
    print(f"Std Dev:            {stats['std']:.2f} msat")
    print(f"Min:                {stats['min']:.2f} msat")
    print(f"Max:                {stats['max']:.2f} msat")
    print(f"25th percentile:    {stats['q25']:.2f} msat")
    print(f"75th percentile:    {stats['q75']:.2f} msat")
    print(f"90th percentile:    {stats['q90']:.2f} msat")
    print(f"95th percentile:    {stats['q95']:.2f} msat")
    print(f"99th percentile:    {stats['q99']:.2f} msat")
    print(f"Zero fee channels:  {stats['zero_fee_pct']:.2f}%")
    print("="*60 + "\n")
    
    # Generate detailed histogram (14-step)
    print("[INFO] Generating detailed 14-step histogram...", file=sys.stderr)
    category_counts = plot_detailed_histogram(df, unique_channels, args.output)
    
    # Generate original format if requested
    if args.original_format:
        print("[INFO] Generating original 4-panel visualization...", file=sys.stderr)
        original_output = args.output.replace('.png', '_original.png')
        plot_base_fee_distribution_original(df, unique_channels, original_output)
    
    # Save statistics to CSV
    csv_file = args.output.replace('.png', '_stats.csv')
    stats_df = pd.DataFrame([stats])
    stats_df.to_csv(csv_file, index=False)
    print(f"✅ Saved statistics: {csv_file}")
    
    # Save category distribution
    category_file = args.output.replace('.png', '_categories.csv')
    category_counts.to_csv(category_file, header=['count'])
    print(f"✅ Saved category distribution: {category_file}")
    
    # Save raw data (sampled if too large)
    data_file = args.output.replace('.png', '_data.csv')
    if len(df) > 100000:
        df_sample = df.sample(n=100000, random_state=42)
        df_sample.to_csv(data_file, index=False)
        print(f"✅ Saved sampled raw data (100k rows): {data_file}")
    else:
        df.to_csv(data_file, index=False)
        print(f"✅ Saved raw data: {data_file}")
    
    print("\n[INFO] Analysis complete!")

if __name__ == "__main__":
    main()
