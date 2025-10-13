#!/bin/bash
# Run all Lightning Network fee analysis scripts (Fixed version)
# 
# Usage:
#   ./run_all_analyses_fixed.sh HOST PORT DB USER PASS
#
# Example:
#   ./run_all_analyses_fixed.sh localhost 5432 lndb readonly secret

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
echo "Lightning Network Fee Analysis Suite (Fixed)"
echo "=========================================="
echo "Database: ${USER}@${HOST}:${PORT}/${DB}"
echo "Start time: $(date)"
echo ""

# Test database connection first
echo "[TEST] Testing database connection..."
if ! python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='${HOST}',
        port=${PORT},
        dbname='${DB}',
        user='${USER}',
        password='${PASS}',
        connect_timeout=10
    )
    conn.close()
    print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"; then
    echo "[ERROR] Cannot connect to database. Please check your credentials."
    exit 1
fi
echo ""

# Create output directory
OUTPUT_DIR="results_fixed_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Function to run analysis with error handling
run_analysis() {
    local script=$1
    local name=$2
    local output=$3
    
    echo "[${name}] Running ${script}..."
    
    if python3 "${script}" \
        --pg-host "${HOST}" \
        --pg-port "${PORT}" \
        --pg-db "${DB}" \
        --pg-user "${USER}" \
        --pg-pass "${PASS}" \
        --output "${OUTPUT_DIR}/${output}" 2>&1 | tee "${OUTPUT_DIR}/${name}_log.txt"; then
        echo "✓ ${name} complete"
        return 0
    else
        echo "✗ ${name} failed (see ${OUTPUT_DIR}/${name}_log.txt for details)"
        return 1
    fi
}

# Track success/failure
TOTAL=4
SUCCESS=0
FAILED=0

# 1. Base Fee Analysis (Fixed)
if [ -f "1_base_fee_analysis_fixed.py" ]; then
    if run_analysis "1_base_fee_analysis_fixed.py" "1-Base-Fee" "1_base_fee_distribution_fixed.png"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
    echo ""
else
    echo "[WARN] 1_base_fee_analysis_fixed.py not found, skipping..."
    echo ""
fi

# 2. Proportional Fee Rate Analysis (Fixed)
if [ -f "2_fee_rate_analysis_fixed.py" ]; then
    if run_analysis "2_fee_rate_analysis_fixed.py" "2-Fee-Rate" "2_fee_rate_distribution_fixed.png"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
    echo ""
else
    echo "[WARN] 2_fee_rate_analysis_fixed.py not found, skipping..."
    echo ""
fi

# 3. Inbound Base Fee Analysis (Original - if fixed version doesn't exist)
if [ -f "3_inbound_base_fee_analysis.py" ]; then
    if run_analysis "3_inbound_base_fee_analysis.py" "3-Inbound-Base-Fee" "3_inbound_base_fee_distribution.png"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
    echo ""
else
    echo "[WARN] 3_inbound_base_fee_analysis.py not found, skipping..."
    echo ""
fi

# 4. Inbound Proportional Fee Rate Analysis (Original - if fixed version doesn't exist)
if [ -f "4_inbound_feerate_analysis.py" ]; then
    if run_analysis "4_inbound_feerate_analysis.py" "4-Inbound-Fee-Rate" "4_inbound_feerate_distribution.png"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
    echo ""
else
    echo "[WARN] 4_inbound_feerate_analysis.py not found, skipping..."
    echo ""
fi

echo "=========================================="
echo "Analysis Summary"
echo "=========================================="
echo "Successful: ${SUCCESS}/${TOTAL}"
echo "Failed:     ${FAILED}/${TOTAL}"
echo "Results saved to: ${OUTPUT_DIR}"
echo "End time: $(date)"
echo "=========================================="

# List output files
if [ "$(ls -A ${OUTPUT_DIR})" ]; then
    echo ""
    echo "Generated files:"
    ls -lh "${OUTPUT_DIR}" | grep -v "^total" | grep -v "_log.txt$"
    echo ""
    echo "Log files:"
    ls -lh "${OUTPUT_DIR}"/*_log.txt 2>/dev/null || echo "No log files"
fi

# Exit with error if any analysis failed
if [ ${FAILED} -gt 0 ]; then
    echo ""
    echo "[WARNING] Some analyses failed. Check log files for details."
    exit 1
fi

exit 0
