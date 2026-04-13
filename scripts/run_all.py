import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis import (
    base_fee,
    base_fee_vs_fee_rate,
    fee_rate,
    fee_rate_when_base_fee_zero,
    inbound_base_fee,
    inbound_base_fee_vs_inbound_fee_rate,
    inbound_fee_rate,
)
from src.analysis.time_range_cli import add_query_time_arguments, time_range_from_namespace


def main() -> None:
    parser = argparse.ArgumentParser(
        description="全分析スクリプトを順に実行する（個別モジュールと同じ時刻窓オプション）。"
    )
    add_query_time_arguments(parser)
    args = parser.parse_args()
    time_range = time_range_from_namespace(args)

    print("=== Lightning Network Fee Distribution Analysis ===\n", flush=True)

    print("[1/7] base_fee_msat — 開始", flush=True)
    base_fee.run(time_range=time_range)
    print("[1/7] base_fee_msat — 完了\n", flush=True)

    print("[2/7] fee_rate_ppm — 開始", flush=True)
    fee_rate.run(time_range=time_range)
    print("[2/7] fee_rate_ppm — 完了\n", flush=True)

    print("[3/7] fee_rate_ppm (base_fee_msat=0) — 開始", flush=True)
    fee_rate_when_base_fee_zero.run(time_range=time_range)
    print("[3/7] fee_rate_ppm (base_fee_msat=0) — 完了\n", flush=True)

    print("[4/7] inbound_base_fee — 開始", flush=True)
    inbound_base_fee.run(time_range=time_range)
    print("[4/7] inbound_base_fee — 完了\n", flush=True)

    print("[5/7] inbound_fee_rate — 開始", flush=True)
    inbound_fee_rate.run(time_range=time_range)
    print("[5/7] inbound_fee_rate — 完了\n", flush=True)

    print("[6/7] base_fee_msat vs fee_rate_ppm scatter — 開始", flush=True)
    base_fee_vs_fee_rate.run(time_range=time_range)
    print("[6/7] base_fee_msat vs fee_rate_ppm scatter — 完了\n", flush=True)

    print("[7/7] inbound_base_fee vs inbound_fee_rate scatter — 開始", flush=True)
    inbound_base_fee_vs_inbound_fee_rate.run(time_range=time_range)
    print("[7/7] inbound_base_fee vs inbound_fee_rate scatter — 完了\n", flush=True)

    print("All graphs saved to output/", flush=True)


if __name__ == "__main__":
    main()
