#!/usr/bin/env python3
"""
Lightning Network: Base Fee Distribution Analysis

This script analyzes the distribution of base fees (rp_base_fee_msat) across
Lightning Network channels. The base fee is a fixed fee charged per payment
regardless of payment amount.

Theory & Background:
- Lightning Network routing fees consist of two components:
  1. Base fee (fixed per payment)
  2. Proportional fee (percentage of payment amount)
- Base fees affect micropayment viability and routing economics
- Analysis based on: Pickhardt & Richter (2021) "Optimally Reliable & Cheap 
  Payment Flows on the Lightning Network" - https://arxiv.org/abs/2107.05322

Visualization:
1. Histogram: Distribution of base fees across channels
2. Log-scale histogram: Better visibility of tail distribution
3. CDF (Cumulative Distribution Function): What percentage of channels 
   have base fee <= X?
4. Box plot: Statistical summary with outlier detection

Usage:
    python 1_base_fee_analysis.py \
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
plt.rcParams['figure.figsize'] = (15, 10)
plt.rcParams['font.size'] = 10

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
# SQL Query: Latest base fee data
# --------------------------------------
BASE_FEE_SQL = r"""
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
SELECT base_fee_msat
FROM open_channel
WHERE base_fee_msat >= 0;  -- Valid fees only
"""

# --------------------------------------
# Helper Functions
# --------------------------------------

def fetch_dataframe(conf: DBConf, sql: str) -> pd.DataFrame:
    """Fetch data from PostgreSQL database."""
    conn = psycopg2.connect(
        host=conf.host, 
        port=conf.port, 
        dbname=conf.db,
        user=conf.user, 
        password=conf.password
    )
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df

def compute_statistics(data: pd.Series) -> Dict:
    """Compute comprehensive statistics for fee distribution."""
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
        'zero_fee_pct': (data == 0).sum() / len(data) * 100
    }

def plot_base_fee_distribution(df: pd.DataFrame, output_file: str = "1_base_fee_distribution.png"):
    """
    Create comprehensive visualization of base fee distribution.
    
    Includes:
    1. Histogram (linear scale)
    2. Histogram (log scale) 
    3. Cumulative Distribution Function (CDF)
    4. Box plot with outlier detection
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    fees = df['base_fee_msat'].values
    stats = compute_statistics(df['base_fee_msat'])
    
    # 1. Linear histogram
    ax1 = axes[0, 0]
    ax1.hist(fees, bins=100, edgecolor='black', alpha=0.7, color='steelblue')
    ax1.axvline(stats['median'], color='red', linestyle='--', linewidth=2, label=f"Median: {stats['median']:.0f} msat")
    ax1.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, label=f"Mean: {stats['mean']:.0f} msat")
    ax1.set_xlabel('Base Fee (msat)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
    ax1.set_title('Base Fee Distribution (Linear Scale)', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. Log-scale histogram
    ax2 = axes[0, 1]
    # Add 1 to avoid log(0)
    fees_log = fees[fees > 0]
    if len(fees_log) > 0:
        ax2.hist(fees_log, bins=100, edgecolor='black', alpha=0.7, color='forestgreen')
        ax2.set_xscale('log')
        ax2.axvline(stats['median'], color='red', linestyle='--', linewidth=2, label=f"Median: {stats['median']:.0f} msat")
        ax2.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, label=f"Mean: {stats['mean']:.0f} msat")
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
    Channels: {stats['count']:,}
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
        description="Lightning Network Base Fee Distribution Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python 1_base_fee_analysis.py \
      --pg-host localhost --pg-port 5432 \
      --pg-db lndb --pg-user readonly --pg-pass secret

Theory:
  Base fees are fixed costs per payment in the Lightning Network.
  They affect routing economics and micropayment feasibility.
  
  Reference: Pickhardt & Richter (2021)
  "Optimally Reliable & Cheap Payment Flows on the Lightning Network"
  https://arxiv.org/abs/2107.05322
        """
    )
    
    parser.add_argument("--pg-host", required=True, help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-db", required=True, help="PostgreSQL database name")
    parser.add_argument("--pg-user", required=True, help="PostgreSQL username")
    parser.add_argument("--pg-pass", required=True, help="PostgreSQL password")
    parser.add_argument("--output", default="1_base_fee_distribution.png", 
                       help="Output file name (default: 1_base_fee_distribution.png)")
    
    args = parser.parse_args()
    
    conf = DBConf(
        host=args.pg_host,
        port=args.pg_port,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_pass
    )
    
    # Fetch data
    print("[INFO] Fetching base fee data from database...", file=sys.stderr)
    df = fetch_dataframe(conf, BASE_FEE_SQL)
    print(f"[INFO] Fetched {len(df):,} channel records", file=sys.stderr)
    
    if len(df) == 0:
        print("[ERROR] No data retrieved. Check database connection and query.", file=sys.stderr)
        sys.exit(1)
    
    # Compute and display statistics
    stats = compute_statistics(df['base_fee_msat'])
    print("\n" + "="*50)
    print("  BASE FEE STATISTICS")
    print("="*50)
    print(f"Total Channels: {stats['count']:,}")
    print(f"Mean:           {stats['mean']:.2f} msat")
    print(f"Median:         {stats['median']:.2f} msat")
    print(f"Std Dev:        {stats['std']:.2f} msat")
    print(f"Min:            {stats['min']:.2f} msat")
    print(f"Max:            {stats['max']:.2f} msat")
    print(f"25th percentile: {stats['q25']:.2f} msat")
    print(f"75th percentile: {stats['q75']:.2f} msat")
    print(f"90th percentile: {stats['q90']:.2f} msat")
    print(f"95th percentile: {stats['q95']:.2f} msat")
    print(f"99th percentile: {stats['q99']:.2f} msat")
    print(f"Zero fee channels: {stats['zero_fee_pct']:.2f}%")
    print("="*50 + "\n")
    
    # Generate visualizations
    print("[INFO] Generating visualizations...", file=sys.stderr)
    plot_base_fee_distribution(df, args.output)
    
    # Save statistics to CSV
    csv_file = args.output.replace('.png', '_stats.csv')
    stats_df = pd.DataFrame([stats])
    stats_df.to_csv(csv_file, index=False)
    print(f"✅ Saved statistics: {csv_file}")
    
    # Save raw data
    data_file = args.output.replace('.png', '_data.csv')
    df.to_csv(data_file, index=False)
    print(f"✅ Saved raw data: {data_file}")
    
    print("\n[INFO] Analysis complete!")

if __name__ == "__main__":
    main()
