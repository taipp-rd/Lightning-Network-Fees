#!/bin/bash
# Run all Lightning Network fee analysis scripts
# 
# Usage:
#   ./run_all_analyses.sh HOST PORT DB USER PASS
#
# Example:
#   ./run_all_analyses.sh localhost 5432 lndb readonly secret

set -e  # Exit on error

# Check arguments
if [ $# -ne 5 ]; then
    echo "Usage: $0 HOST PORT DB USER PASS"
    echo "Example: $0 localhost 5432 lndb readonly secret"
    exit 1
fi

HOST=$1
PORT=$2
DB=$3
USER=$4
PASS=$5

echo "=========================================="
echo "Lightning Network Fee Analysis Suite"
echo "=========================================="
echo "Database: ${USER}@${HOST}:${PORT}/${DB}"
echo "Start time: $(date)"
echo ""

# Create output directory
OUTPUT_DIR="results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# 1. Base Fee Analysis
echo "[1/4] Running Base Fee Analysis..."
python 1_base_fee_analysis.py \
    --pg-host "${HOST}" \
    --pg-port "${PORT}" \
    --pg-db "${DB}" \
    --pg-user "${USER}" \
    --pg-pass "${PASS}" \
    --output "${OUTPUT_DIR}/1_base_fee_distribution.png"
echo "✓ Base fee analysis complete"
echo ""

# 2. Proportional Fee Rate Analysis
echo "[2/4] Running Proportional Fee Rate Analysis..."
python 2_fee_rate_analysis.py \
    --pg-host "${HOST}" \
    --pg-port "${PORT}" \
    --pg-db "${DB}" \
    --pg-user "${USER}" \
    --pg-pass "${PASS}" \
    --output "${OUTPUT_DIR}/2_fee_rate_distribution.png"
echo "✓ Proportional fee rate analysis complete"
echo ""

# 3. Inbound Base Fee Analysis
echo "[3/4] Running Inbound Base Fee Analysis..."
python 3_inbound_base_fee_analysis.py \
    --pg-host "${HOST}" \
    --pg-port "${PORT}" \
    --pg-db "${DB}" \
    --pg-user "${USER}" \
    --pg-pass "${PASS}" \
    --output "${OUTPUT_DIR}/3_inbound_base_fee_distribution.png"
echo "✓ Inbound base fee analysis complete"
echo ""

# 4. Inbound Proportional Fee Rate Analysis
echo "[4/4] Running Inbound Proportional Fee Rate Analysis..."
python 4_inbound_feerate_analysis.py \
    --pg-host "${HOST}" \
    --pg-port "${PORT}" \
    --pg-db "${DB}" \
    --pg-user "${USER}" \
    --pg-pass "${PASS}" \
    --output "${OUTPUT_DIR}/4_inbound_feerate_distribution.png"
echo "✓ Inbound proportional fee rate analysis complete"
echo ""

echo "=========================================="
echo "All analyses completed successfully!"
echo "Results saved to: ${OUTPUT_DIR}"
echo "End time: $(date)"
echo "=========================================="

# List output files
echo ""
echo "Generated files:"
ls -lh "${OUTPUT_DIR}"
