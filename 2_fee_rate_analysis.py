#!/usr/bin/env python3
"""
Lightning Network: Proportional Fee Rate Distribution Analysis

This script analyzes the distribution of proportional fees (rp_feerate_ppm)
across Lightning Network channels. The proportional fee is charged as parts-per-million
(ppm) of the payment amount.

Theory & Background:
- Proportional fees scale with payment size, affecting large payment economics
- Typical range: 0-5000 ppm (0-0.5%)
- Higher fees may indicate capital opportunity cost or routing profitability expectations
- Analysis based on:
  * Pickhardt & Richter (2021) "Optimally Reliable & Cheap Payment Flows"
  * Rohrer et al. (2019) "Discharged Payment Channels"
  * Tikhomirov et al. (2020) "Quantifying Blockchain Extractable Value"

Visualization:
1. Histogram: Distribution of fee rates (ppm)
2. Log-scale histogram: Tail distribution visibility
3. CDF: Cumulative probability distribution
4. Violin plot: Density estimation with quartiles

Usage:
    python 2_fee_rate_analysis.py \
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
# SQL Query: Latest fee rate data
# --------------------------------------
FEE_RATE_SQL = r"""
WITH latest_channel AS (
  -- Get latest update for each channel direction
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
  WHERE cc.chan_id IS NULL  -- Only open channels
    AND lc.rp_disabled = false  -- Only enabled channels
)
SELECT fee_rate_ppm
FROM open_channel
WHERE fee_rate_ppm >= 0;  -- Valid fees only
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
        'low_fee_pct': (data <= 100).sum() / len(data) * 100,  # <= 0.01%
        'medium_fee_pct': ((data > 100) & (data <= 1000)).sum() / len(data) * 100,  # 0.01-0.1%
        'high_fee_pct': (data > 1000).sum() / len(data) * 100  # > 0.1%
    }

def plot_fee_rate_distribution(df: pd.DataFrame, output_file: str = "2_fee_rate_distribution.png"):
    """
    Create comprehensive visualization of proportional fee rate distribution.
    
    Includes:
    1. Histogram (linear scale)
    2. Histogram (log scale)
    3. Cumulative Distribution Function (CDF)
    4. Violin plot with density estimation
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    fees = df['fee_rate_ppm'].values
    stats = compute_statistics(df['fee_rate_ppm'])
    
    # 1. Linear histogram
    ax1 = axes[0, 0]
    ax1.hist(fees, bins=100, edgecolor='black', alpha=0.7, color='steelblue')
    ax1.axvline(stats['median'], color='red', linestyle='--', linewidth=2, 
                label=f"Median: {stats['median']:.0f} ppm")
    ax1.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, 
                label=f"Mean: {stats['mean']:.0f} ppm")
    ax1.set_xlabel('Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
    ax1.set_title('Fee Rate Distribution (Linear Scale)', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. Log-scale histogram
    ax2 = axes[0, 1]
    fees_log = fees[fees > 0]
    if len(fees_log) > 0:
        ax2.hist(fees_log, bins=100, edgecolor='black', alpha=0.7, color='forestgreen')
        ax2.set_xscale('log')
        ax2.axvline(stats['median'], color='red', linestyle='--', linewidth=2, 
                    label=f"Median: {stats['median']:.0f} ppm")
        ax2.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, 
                    label=f"Mean: {stats['mean']:.0f} ppm")
    ax2.set_xlabel('Fee Rate (ppm, log scale)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
    ax2.set_title('Fee Rate Distribution (Log Scale)', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 3. Cumulative Distribution Function (CDF)
    ax3 = axes[1, 0]
    sorted_fees = np.sort(fees)
    cumulative = np.arange(1, len(sorted_fees) + 1) / len(sorted_fees) * 100
    ax3.plot(sorted_fees, cumulative, linewidth=2, color='purple')
    
    # Add reference lines for common thresholds
    ax3.axhline(50, color='red', linestyle='--', linewidth=1, alpha=0.7, label='50th percentile')
    ax3.axhline(90, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='90th percentile')
    ax3.axvline(100, color='green', linestyle=':', linewidth=1, alpha=0.7, label='100 ppm (0.01%)')
    ax3.axvline(1000, color='blue', linestyle=':', linewidth=1, alpha=0.7, label='1000 ppm (0.1%)')
    
    ax3.set_xlabel('Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Cumulative Percentage (%)', fontsize=12, fontweight='bold')
    ax3.set_title('Cumulative Distribution Function (CDF)', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=9, loc='lower right')
    ax3.grid(True, alpha=0.3)
    
    # 4. Violin plot
    ax4 = axes[1, 1]
    parts = ax4.violinplot([fees], vert=True, showmeans=True, showmedians=True, widths=0.7)
    
    # Customize violin plot
    for pc in parts['bodies']:
        pc.set_facecolor('lightcoral')
        pc.set_alpha(0.7)
    
    parts['cmeans'].set_color('orange')
    parts['cmeans'].set_linewidth(2)
    parts['cmedians'].set_color('darkred')
    parts['cmedians'].set_linewidth(2)
    
    ax4.set_ylabel('Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax4.set_title('Violin Plot (Density Estimation)', fontsize=14, fontweight='bold')
    ax4.set_xticks([1])
    ax4.set_xticklabels(['All Channels'])
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add statistics text box
    stats_text = f"""
    Statistics Summary:
    ───────────────────────
    Channels: {stats['count']:,}
    Mean: {stats['mean']:.0f} ppm
    Median: {stats['median']:.0f} ppm
    Std Dev: {stats['std']:.0f} ppm
    ───────────────────────
    Min: {stats['min']:.0f} ppm
    Q25: {stats['q25']:.0f} ppm
    Q75: {stats['q75']:.0f} ppm
    Q90: {stats['q90']:.0f} ppm
    Q95: {stats['q95']:.0f} ppm
    Q99: {stats['q99']:.0f} ppm
    Max: {stats['max']:.0f} ppm
    ───────────────────────
    Fee Categories:
    Zero: {stats['zero_fee_pct']:.2f}%
    Low (≤100): {stats['low_fee_pct']:.2f}%
    Med (100-1000): {stats['medium_fee_pct']:.2f}%
    High (>1000): {stats['high_fee_pct']:.2f}%
    """
    
    fig.text(0.98, 0.5, stats_text, 
             fontsize=10, 
             family='monospace',
             verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('Lightning Network: Proportional Fee Rate Distribution Analysis', 
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
        description="Lightning Network Proportional Fee Rate Distribution Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python 2_fee_rate_analysis.py \
      --pg-host localhost --pg-port 5432 \
      --pg-db lndb --pg-user readonly --pg-pass secret

Theory:
  Proportional fees (in ppm) scale with payment amount.
  They represent the opportunity cost of capital and routing profitability.
  
  References:
  - Pickhardt & Richter (2021) "Optimally Reliable & Cheap Payment Flows"
  - Rohrer et al. (2019) "Discharged Payment Channels"
  - Tikhomirov et al. (2020) "Quantifying Blockchain Extractable Value"
        """
    )
    
    parser.add_argument("--pg-host", required=True, help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-db", required=True, help="PostgreSQL database name")
    parser.add_argument("--pg-user", required=True, help="PostgreSQL username")
    parser.add_argument("--pg-pass", required=True, help="PostgreSQL password")
    parser.add_argument("--output", default="2_fee_rate_distribution.png", 
                       help="Output file name (default: 2_fee_rate_distribution.png)")
    
    args = parser.parse_args()
    
    conf = DBConf(
        host=args.pg_host,
        port=args.pg_port,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_pass
    )
    
    # Fetch data
    print("[INFO] Fetching proportional fee rate data from database...", file=sys.stderr)
    df = fetch_dataframe(conf, FEE_RATE_SQL)
    print(f"[INFO] Fetched {len(df):,} channel records", file=sys.stderr)
    
    if len(df) == 0:
        print("[ERROR] No data retrieved. Check database connection and query.", file=sys.stderr)
        sys.exit(1)
    
    # Compute and display statistics
    stats = compute_statistics(df['fee_rate_ppm'])
    print("\n" + "="*50)
    print("  PROPORTIONAL FEE RATE STATISTICS")
    print("="*50)
    print(f"Total Channels: {stats['count']:,}")
    print(f"Mean:           {stats['mean']:.2f} ppm ({stats['mean']/10000:.4f}%)")
    print(f"Median:         {stats['median']:.2f} ppm ({stats['median']/10000:.4f}%)")
    print(f"Std Dev:        {stats['std']:.2f} ppm")
    print(f"Min:            {stats['min']:.2f} ppm")
    print(f"Max:            {stats['max']:.2f} ppm")
    print(f"25th percentile: {stats['q25']:.2f} ppm")
    print(f"75th percentile: {stats['q75']:.2f} ppm")
    print(f"90th percentile: {stats['q90']:.2f} ppm")
    print(f"95th percentile: {stats['q95']:.2f} ppm")
    print(f"99th percentile: {stats['q99']:.2f} ppm")
    print("\nFee Categories:")
    print(f"  Zero fee:     {stats['zero_fee_pct']:.2f}%")
    print(f"  Low (≤100):   {stats['low_fee_pct']:.2f}%")
    print(f"  Medium (100-1000): {stats['medium_fee_pct']:.2f}%")
    print(f"  High (>1000): {stats['high_fee_pct']:.2f}%")
    print("="*50 + "\n")
    
    # Generate visualizations
    print("[INFO] Generating visualizations...", file=sys.stderr)
    plot_fee_rate_distribution(df, args.output)
    
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
