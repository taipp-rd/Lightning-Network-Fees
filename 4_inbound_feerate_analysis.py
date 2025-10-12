#!/usr/bin/env python3
"""
Lightning Network: Inbound Proportional Fee Rate Distribution Analysis

This script analyzes the distribution of inbound proportional fees (rp_inbound_feerate_ppm)
across Lightning Network channels. Inbound proportional fees scale with payment amount.

Theory & Background:
- Inbound proportional fees address liquidity management in Lightning Network
- They allow nodes to dynamically adjust pricing based on channel balance
- Important for maintaining balanced channels and network stability
- Analysis based on:
  * Pickhardt & Richter (2022) "Mathematical Theory of Payment Channel Networks"
  * Nisslmueller et al. (2023) "Towards Fee Estimation in Lightning Network"
  * Gregaard et al. (2023) "Payment Channel Rebalancing Strategies"

Visualization:
1. Histogram: Distribution of inbound proportional fees
2. Log-scale histogram: Tail behavior
3. CDF: Cumulative probability distribution
4. Comparison with outbound proportional fees
5. Heat map: Inbound vs Outbound fee patterns

Usage:
    python 4_inbound_feerate_analysis.py \
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
plt.rcParams['figure.figsize'] = (16, 12)
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
# SQL Query: Latest inbound fee rate data
# --------------------------------------
INBOUND_FEE_RATE_SQL = r"""
WITH latest_channel AS (
  -- Get latest update for each channel direction
  SELECT DISTINCT ON (cu.chan_id, cu.advertising_nodeid)
         cu.chan_id,
         cu.advertising_nodeid,
         cu.connecting_nodeid,
         COALESCE(cu.rp_feerate_ppm, 0) AS outbound_feerate_ppm,
         COALESCE(cu.rp_inbound_feerate_ppm, 0) AS inbound_feerate_ppm,
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
SELECT inbound_feerate_ppm, outbound_feerate_ppm
FROM open_channel;
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
    """Compute comprehensive statistics for inbound fee rate distribution."""
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
        'positive_fee_pct': (data > 0).sum() / len(data) * 100,
        'negative_fee_pct': (data < 0).sum() / len(data) * 100,
        'low_fee_pct': ((data > 0) & (data <= 100)).sum() / len(data) * 100,
        'medium_fee_pct': ((data > 100) & (data <= 1000)).sum() / len(data) * 100,
        'high_fee_pct': (data > 1000).sum() / len(data) * 100
    }

def plot_inbound_feerate_distribution(df: pd.DataFrame, output_file: str = "4_inbound_feerate_distribution.png"):
    """
    Create comprehensive visualization of inbound proportional fee rate distribution.
    
    Includes:
    1. Histogram (linear scale)
    2. Histogram (log scale for positive fees)
    3. Cumulative Distribution Function (CDF)
    4. Scatter plot: Inbound vs Outbound fee rates
    5. 2D Histogram (heatmap): Fee pattern analysis
    """
    fig = plt.figure(figsize=(18, 14))
    
    # Create grid for subplots
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    inbound_fees = df['inbound_feerate_ppm'].values
    outbound_fees = df['outbound_feerate_ppm'].values
    stats = compute_statistics(df['inbound_feerate_ppm'])
    
    # 1. Linear histogram
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(inbound_fees, bins=100, edgecolor='black', alpha=0.7, color='steelblue')
    ax1.axvline(stats['median'], color='red', linestyle='--', linewidth=2, 
                label=f"Median: {stats['median']:.0f} ppm")
    ax1.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, 
                label=f"Mean: {stats['mean']:.0f} ppm")
    ax1.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax1.set_xlabel('Inbound Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
    ax1.set_title('Inbound Fee Rate Distribution (Linear Scale)', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 2. Log-scale histogram (positive fees only)
    ax2 = fig.add_subplot(gs[0, 1])
    positive_fees = inbound_fees[inbound_fees > 0]
    if len(positive_fees) > 0:
        ax2.hist(positive_fees, bins=100, edgecolor='black', alpha=0.7, color='forestgreen')
        ax2.set_xscale('log')
        median_pos = np.median(positive_fees)
        mean_pos = np.mean(positive_fees)
        ax2.axvline(median_pos, color='red', linestyle='--', linewidth=2, 
                    label=f"Median (pos): {median_pos:.0f} ppm")
        ax2.axvline(mean_pos, color='orange', linestyle='--', linewidth=2, 
                    label=f"Mean (pos): {mean_pos:.0f} ppm")
        ax2.set_xlabel('Inbound Fee Rate (ppm, log scale)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Number of Channels', fontsize=12, fontweight='bold')
        ax2.set_title('Inbound Fee Rate Distribution (Log Scale, Positive Only)', 
                     fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
    else:
        ax2.text(0.5, 0.5, 'No positive inbound fees', 
                ha='center', va='center', transform=ax2.transAxes, fontsize=14)
        ax2.set_title('Inbound Fee Rate Distribution (Log Scale)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 3. Cumulative Distribution Function (CDF)
    ax3 = fig.add_subplot(gs[1, 0])
    sorted_fees = np.sort(inbound_fees)
    cumulative = np.arange(1, len(sorted_fees) + 1) / len(sorted_fees) * 100
    ax3.plot(sorted_fees, cumulative, linewidth=2, color='purple')
    ax3.axhline(50, color='red', linestyle='--', linewidth=1, alpha=0.7, label='50th percentile')
    ax3.axhline(90, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='90th percentile')
    ax3.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5, label='Zero fee')
    ax3.axvline(100, color='green', linestyle=':', linewidth=1, alpha=0.7, label='100 ppm')
    ax3.axvline(1000, color='blue', linestyle=':', linewidth=1, alpha=0.7, label='1000 ppm')
    ax3.set_xlabel('Inbound Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Cumulative Percentage (%)', fontsize=12, fontweight='bold')
    ax3.set_title('Cumulative Distribution Function (CDF)', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # 4. Scatter plot: Inbound vs Outbound fee rates
    ax4 = fig.add_subplot(gs[1, 1])
    # Sample for visualization if too many points
    if len(df) > 10000:
        sample_idx = np.random.choice(len(df), 10000, replace=False)
        in_sample = inbound_fees[sample_idx]
        out_sample = outbound_fees[sample_idx]
    else:
        in_sample = inbound_fees
        out_sample = outbound_fees
    
    ax4.scatter(out_sample, in_sample, alpha=0.3, s=10, color='darkblue')
    ax4.axhline(0, color='red', linestyle='--', linewidth=1, alpha=0.7, label='Zero inbound fee')
    ax4.axvline(0, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='Zero outbound fee')
    
    # Add diagonal line for reference (inbound = outbound)
    max_val = max(np.max(out_sample), np.max(in_sample))
    ax4.plot([0, max_val], [0, max_val], 'g--', linewidth=1, alpha=0.5, label='Inbound = Outbound')
    
    ax4.set_xlabel('Outbound Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Inbound Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax4.set_title('Inbound vs Outbound Fee Rates', fontsize=14, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    # 5. 2D Histogram (Heatmap): Fee pattern analysis
    ax5 = fig.add_subplot(gs[2, :])
    
    # Filter extreme outliers for better visualization
    in_clip = np.clip(inbound_fees, 0, np.percentile(inbound_fees, 99))
    out_clip = np.clip(outbound_fees, 0, np.percentile(outbound_fees, 99))
    
    # Create 2D histogram
    h, xedges, yedges = np.histogram2d(out_clip, in_clip, bins=50)
    
    # Plot heatmap
    im = ax5.imshow(h.T, origin='lower', aspect='auto', cmap='YlOrRd',
                    extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
                    interpolation='bilinear')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax5)
    cbar.set_label('Number of Channels', fontsize=11, fontweight='bold')
    
    # Add reference lines
    ax5.plot([0, max(xedges[-1], yedges[-1])], [0, max(xedges[-1], yedges[-1])], 
             'w--', linewidth=2, alpha=0.7, label='Inbound = Outbound')
    
    ax5.set_xlabel('Outbound Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Inbound Fee Rate (ppm)', fontsize=12, fontweight='bold')
    ax5.set_title('Fee Pattern Heatmap: Inbound vs Outbound (99th percentile clipped)', 
                 fontsize=14, fontweight='bold')
    ax5.legend(fontsize=10)
    ax5.grid(True, alpha=0.3, color='white', linewidth=0.5)
    
    # Add statistics text box
    stats_text = f"""
    Statistics Summary:
    ──────────────────────────
    Channels: {stats['count']:,}
    Mean: {stats['mean']:.0f} ppm
    Median: {stats['median']:.0f} ppm
    Std Dev: {stats['std']:.0f} ppm
    ──────────────────────────
    Percentiles:
    Q25: {stats['q25']:.0f} ppm
    Q75: {stats['q75']:.0f} ppm
    Q90: {stats['q90']:.0f} ppm
    Q95: {stats['q95']:.0f} ppm
    Q99: {stats['q99']:.0f} ppm
    ──────────────────────────
    Fee Categories:
    Zero: {stats['zero_fee_pct']:.2f}%
    Positive: {stats['positive_fee_pct']:.2f}%
    Negative: {stats['negative_fee_pct']:.2f}%
    Low (≤100): {stats['low_fee_pct']:.2f}%
    Med (100-1000): {stats['medium_fee_pct']:.2f}%
    High (>1000): {stats['high_fee_pct']:.2f}%
    """
    
    fig.text(0.98, 0.5, stats_text, 
             fontsize=9, 
             family='monospace',
             verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('Lightning Network: Inbound Proportional Fee Rate Distribution Analysis', 
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
        description="Lightning Network Inbound Proportional Fee Rate Distribution Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python 4_inbound_feerate_analysis.py \
      --pg-host localhost --pg-port 5432 \
      --pg-db lndb --pg-user readonly --pg-pass secret

Theory:
  Inbound proportional fees enable dynamic liquidity management in Lightning Network.
  They allow nodes to adjust pricing based on channel balance and demand.
  
  References:
  - Pickhardt & Richter (2022) "Mathematical Theory of Payment Channel Networks"
  - Nisslmueller et al. (2023) "Towards Fee Estimation in Lightning Network"
  - Gregaard et al. (2023) "Payment Channel Rebalancing Strategies"
        """
    )
    
    parser.add_argument("--pg-host", required=True, help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-db", required=True, help="PostgreSQL database name")
    parser.add_argument("--pg-user", required=True, help="PostgreSQL username")
    parser.add_argument("--pg-pass", required=True, help="PostgreSQL password")
    parser.add_argument("--output", default="4_inbound_feerate_distribution.png", 
                       help="Output file name (default: 4_inbound_feerate_distribution.png)")
    
    args = parser.parse_args()
    
    conf = DBConf(
        host=args.pg_host,
        port=args.pg_port,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_pass
    )
    
    # Fetch data
    print("[INFO] Fetching inbound proportional fee rate data from database...", file=sys.stderr)
    df = fetch_dataframe(conf, INBOUND_FEE_RATE_SQL)
    print(f"[INFO] Fetched {len(df):,} channel records", file=sys.stderr)
    
    if len(df) == 0:
        print("[ERROR] No data retrieved. Check database connection and query.", file=sys.stderr)
        sys.exit(1)
    
    # Compute and display statistics
    stats = compute_statistics(df['inbound_feerate_ppm'])
    print("\n" + "="*50)
    print("  INBOUND PROPORTIONAL FEE RATE STATISTICS")
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
    print("\nFee Distribution:")
    print(f"  Zero fee:     {stats['zero_fee_pct']:.2f}%")
    print(f"  Positive fee: {stats['positive_fee_pct']:.2f}%")
    print(f"  Negative fee: {stats['negative_fee_pct']:.2f}%")
    print("\nFee Categories (Positive):")
    print(f"  Low (≤100):   {stats['low_fee_pct']:.2f}%")
    print(f"  Medium (100-1000): {stats['medium_fee_pct']:.2f}%")
    print(f"  High (>1000): {stats['high_fee_pct']:.2f}%")
    print("="*50 + "\n")
    
    # Generate visualizations
    print("[INFO] Generating visualizations...", file=sys.stderr)
    plot_inbound_feerate_distribution(df, args.output)
    
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
