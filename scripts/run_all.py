import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis import (
    base_fee,
    base_fee_vs_fee_rate,
    fee_rate,
    inbound_base_fee,
    inbound_base_fee_vs_inbound_fee_rate,
    inbound_fee_rate,
)

if __name__ == "__main__":
    print("=== Lightning Network Fee Distribution Analysis ===\n", flush=True)

    print("[1/6] base_fee_msat — 開始", flush=True)
    base_fee.run()
    print("[1/6] base_fee_msat — 完了\n", flush=True)

    print("[2/6] fee_rate_ppm — 開始", flush=True)
    fee_rate.run()
    print("[2/6] fee_rate_ppm — 完了\n", flush=True)

    print("[3/6] inbound_base_fee — 開始", flush=True)
    inbound_base_fee.run()
    print("[3/6] inbound_base_fee — 完了\n", flush=True)

    print("[4/6] inbound_fee_rate — 開始", flush=True)
    inbound_fee_rate.run()
    print("[4/6] inbound_fee_rate — 完了\n", flush=True)

    print("[5/6] base_fee_msat vs fee_rate_ppm scatter — 開始", flush=True)
    base_fee_vs_fee_rate.run()
    print("[5/6] base_fee_msat vs fee_rate_ppm scatter — 完了\n", flush=True)

    print("[6/6] inbound_base_fee vs inbound_fee_rate scatter — 開始", flush=True)
    inbound_base_fee_vs_inbound_fee_rate.run()
    print("[6/6] inbound_base_fee vs inbound_fee_rate scatter — 完了\n", flush=True)

    print("All graphs saved to output/", flush=True)
