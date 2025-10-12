# Lightning Network Fee Distribution Analysis

Comprehensive analysis of fee structures in the Lightning Network, including base fees, proportional fees, and inbound fees.

## Overview

This repository contains four analysis scripts that examine different aspects of Lightning Network routing fees:

1. **Base Fee Analysis** (`1_base_fee_analysis.py`) - Distribution of fixed fees per payment
2. **Proportional Fee Analysis** (`2_fee_rate_analysis.py`) - Distribution of percentage-based fees
3. **Inbound Base Fee Analysis** (`3_inbound_base_fee_analysis.py`) - Fixed fees for receiving payments
4. **Inbound Proportional Fee Analysis** (`4_inbound_feerate_analysis.py`) - Percentage fees for receiving payments

## Theoretical Background

Lightning Network routing fees consist of two components:

### Outbound Fees (Traditional)
- **Base Fee (rp_base_fee_msat)**: Fixed fee charged per payment, regardless of amount
- **Proportional Fee (rp_feerate_ppm)**: Fee proportional to payment amount (in parts-per-million)

### Inbound Fees (Advanced)
- **Inbound Base Fee (rp_inbound_base_fee_msat)**: Fixed fee for receiving payments
- **Inbound Proportional Fee (rp_inbound_feerate_ppm)**: Percentage fee for receiving payments

Inbound fees address the **liquidity imbalance problem** in payment channels, allowing nodes to:
- Charge for incoming liquidity
- Dynamically adjust pricing based on channel balance
- Incentivize balanced channel states

## Academic References

- **Pickhardt & Richter (2021)**: "Optimally Reliable & Cheap Payment Flows on the Lightning Network" - https://arxiv.org/abs/2107.05322
- **Rohrer et al. (2019)**: "Discharged Payment Channels: Quantifying the Lightning Network's Resilience" - https://arxiv.org/abs/1904.10253
- **Pickhardt & Richter (2022)**: "A Mathematical Theory of Payment Channel Networks"
- **Nisslmueller et al. (2023)**: "Towards Fee Estimation in Lightning Network"
- **Tikhomirov et al. (2020)**: "Quantifying Blockchain Extractable Value"

## Requirements

```bash
pip install -r requirements.txt
```

## Database Setup

These scripts connect to a PostgreSQL database containing Lightning Network graph data with the following tables:

- `channel_update`: Channel routing policies and fees
- `closed_channel`: Historical channel closures
- `node_announcement`: Node metadata and aliases

### Table Structure

#### channel_update
- `chan_id`: Channel identifier
- `advertising_nodeid`: Node announcing the policy
- `connecting_nodeid`: Peer node
- `rp_base_fee_msat`: Outbound base fee (millisatoshi)
- `rp_feerate_ppm`: Outbound proportional fee (parts per million)
- `rp_inbound_base_fee_msat`: Inbound base fee
- `rp_inbound_feerate_ppm`: Inbound proportional fee
- `rp_disabled`: Whether the channel is disabled
- `rp_last_update`: Last policy update timestamp
- `timestamp`: Record creation timestamp

## Usage

### 1. Base Fee Analysis

```bash
python 1_base_fee_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**Output:**
- `1_base_fee_distribution.png`: Multi-panel visualization
- `1_base_fee_distribution_stats.csv`: Statistical summary
- `1_base_fee_distribution_data.csv`: Raw fee data

**Visualizations:**
- Linear histogram: Overall distribution
- Log-scale histogram: Tail behavior
- CDF: Cumulative probability
- Box plot: Outlier detection

### 2. Proportional Fee Rate Analysis

```bash
python 2_fee_rate_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**Output:**
- `2_fee_rate_distribution.png`: Multi-panel visualization
- `2_fee_rate_distribution_stats.csv`: Statistical summary
- `2_fee_rate_distribution_data.csv`: Raw fee rate data

**Visualizations:**
- Linear histogram: Distribution of fee rates
- Log-scale histogram: High fee channels
- CDF: Fee percentiles
- Violin plot: Density estimation

### 3. Inbound Base Fee Analysis

```bash
python 3_inbound_base_fee_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**Output:**
- `3_inbound_base_fee_distribution.png`: Multi-panel visualization
- `3_inbound_base_fee_distribution_stats.csv`: Statistical summary
- `3_inbound_base_fee_distribution_data.csv`: Raw inbound fee data

**Visualizations:**
- Linear histogram: Inbound fee distribution
- Log-scale histogram: Positive fees
- CDF: Cumulative distribution
- Scatter plot: Inbound vs outbound comparison

### 4. Inbound Proportional Fee Analysis

```bash
python 4_inbound_feerate_analysis.py \
    --pg-host localhost \
    --pg-port 5432 \
    --pg-db lndb \
    --pg-user readonly \
    --pg-pass secret
```

**Output:**
- `4_inbound_feerate_distribution.png`: Multi-panel visualization
- `4_inbound_feerate_distribution_stats.csv`: Statistical summary
- `4_inbound_feerate_distribution_data.csv`: Raw inbound fee rate data

**Visualizations:**
- Linear histogram: Distribution
- Log-scale histogram: Positive fees
- CDF: Percentile analysis
- Scatter plot: Inbound vs outbound
- Heatmap: Fee pattern analysis

## Data Selection Strategy

All scripts implement the following data filtering approach:

1. **Latest Records Only**: Uses `DISTINCT ON (chan_id, advertising_nodeid)` with `ORDER BY timestamp DESC` to get the most recent routing policy for each channel direction

2. **Open Channels Only**: Excludes closed channels by LEFT JOIN with `closed_channel` table

3. **Enabled Channels Only**: Filters out disabled channels (`rp_disabled = false`)

4. **Valid Fees**: Excludes invalid or NULL fee values

This ensures analysis reflects the **current state** of the Lightning Network (approximately 40,000-50,000 active channels).

## Key Statistics Computed

Each script computes comprehensive statistics:

- **Central Tendency**: Mean, Median
- **Dispersion**: Standard Deviation, Min, Max
- **Percentiles**: Q25, Q75, Q90, Q95, Q99
- **Fee Categories**: 
  - Zero fee channels (%)
  - Low fee channels (≤100 ppm or base equivalent)
  - Medium fee channels (100-1000 ppm)
  - High fee channels (>1000 ppm)
  - Positive vs Negative fees (for inbound fees)

## Interpretation Guidelines

### Base Fees
- **Zero base fees**: Many nodes use zero base fees to encourage routing
- **High base fees**: May discourage small payments (micropayments)
- **Distribution shape**: Typically right-skewed with long tail

### Proportional Fees
- **Typical range**: 0-5000 ppm (0-0.5%)
- **Zero fees**: Altruistic routing or loss-leader strategy
- **High fees**: Capital opportunity cost or premium routing
- **Comparison to traditional finance**: Lightning fees are orders of magnitude lower

### Inbound Fees
- **Adoption rate**: Still relatively new, adoption varies
- **Negative fees**: Paying others to send you payments (liquidity incentive)
- **Positive fees**: Charging for receiving (liquidity preservation)
- **Balance management**: Key tool for channel equilibrium

## Technical Notes

### PostgreSQL Query Optimization

The SQL queries use:
- `DISTINCT ON` for efficient deduplication
- `COALESCE` for NULL handling
- `LEFT JOIN` for exclusion logic
- Proper indexing on `chan_id`, `advertising_nodeid`, and `timestamp` is recommended

### Visualization Techniques

1. **Histograms**: Show frequency distribution
2. **Log Scale**: Reveal tail behavior for skewed distributions
3. **CDF**: Answer "What % of channels have fee ≤ X?"
4. **Box Plots**: Identify outliers statistically
5. **Violin Plots**: Combine box plot with kernel density estimation
6. **Scatter Plots**: Correlation between inbound and outbound fees
7. **Heatmaps**: 2D density for pattern recognition

### Statistical Methods

- **Percentiles**: Non-parametric, robust to outliers
- **Box Plot**: Uses IQR method for outlier detection
- **Kernel Density**: Smooth probability density estimation
- **Cumulative Distribution**: Monotonic, interpretable probability

## Research Applications

These analysis tools can support research in:

1. **Routing Economics**: Understanding fee structures and incentives
2. **Network Topology**: How fees relate to network position
3. **Liquidity Management**: Inbound fee adoption and effectiveness
4. **Payment Feasibility**: Impact of fees on different payment sizes
5. **Node Strategy**: Optimal fee setting for routing nodes
6. **Market Dynamics**: Fee competition and evolution over time

## Future Extensions

Potential additions:

- Time-series analysis: Fee evolution over time
- Geographical analysis: Fee differences by region
- Capacity correlation: How fees relate to channel size
- Node centrality: Fee strategies of hub nodes
- Path finding: Impact of fees on optimal routes
- Predictive modeling: Fee forecasting

## Contributing

Contributions are welcome! Areas for improvement:

- Additional visualization types
- Statistical tests (e.g., distribution fitting)
- Comparative analysis tools
- Time-series components
- Machine learning models

## License

MIT License - See LICENSE file for details

## Citation

If you use this code in academic research, please cite:

```bibtex
@software{lightning_fee_analysis,
  title = {Lightning Network Fee Distribution Analysis},
  author = {taipp-rd},
  year = {2025},
  url = {https://github.com/taipp-rd/Lightning-Network-Fees}
}
```

## Contact

For questions or collaboration:
- GitHub Issues: https://github.com/taipp-rd/Lightning-Network-Fees/issues

## Acknowledgments

This work builds on research from:
- Pickhardt & Richter: Optimal payment flow theory
- Rohrer et al.: Network resilience analysis
- The Lightning Network developer community

---

**Note**: Always ensure you have proper authorization before accessing and analyzing Lightning Network data. Respect node operator privacy and follow responsible disclosure practices.