"""
base_fee_msat = 0 のチャネルに限定した fee_rate_ppm の分布を可視化する。

帯別: 0〜2000 ppm を 50 ppm 幅の帯に分けた棒グラフに加え、
0〜50 ppm の細かいヒストグラムと ECDF を出力する（fee_rate 分析と同じビン設定）。
"""

from __future__ import annotations

import argparse

import numpy as np

from src.analysis.run_helpers import fetch_fee_pair_values, log_numeric_summary
from src.analysis.time_range_cli import add_query_time_arguments, time_range_from_namespace
from src.db.fee_snapshot_query import QueryTimeRange
from src.paths import PROJECT_ROOT
from src.visualization.charts import (
    plot_fee_distribution,
    plot_fee_ecdf,
    plot_ppm_band_bar_chart,
)

OUTPUT_PATH_BANDS = (
    PROJECT_ROOT / "output" / "fee_rate_ppm_when_base_fee_0_bands.png"
)
OUTPUT_PATH_LOW = (
    PROJECT_ROOT / "output" / "fee_rate_ppm_when_base_fee_0_0_50.png"
)
OUTPUT_PATH_CDF = (
    PROJECT_ROOT / "output" / "fee_rate_ppm_when_base_fee_0_cdf.png"
)

# fee_rate.py と同じレンジ・ビン（ppm）
FEE_RATE_BAND_WIDTH_PPM = 50.0
FEE_RATE_DISPLAY_MAX_PPM = 2000.0
FEE_RATE_LOW_BIN_WIDTH_PPM = 1.0
FEE_RATE_LOW_DISPLAY_MAX_PPM = 50.0
FEE_RATE_LOW_X_MAJOR_TICK_PPM = 5.0
FEE_RATE_CDF_X_MAJOR_TICK_PPM = 100.0


def _fee_rates_with_base_fee_zero(
    pairs: list[tuple[object, object]],
) -> tuple[list[float], int]:
    """
    (base_fee_msat, fee_rate_ppm) の組から、base_fee が 0 の行の fee_rate だけを返す。

    base_fee は DB 上ミリサトシ整数想定だが、浮動小数の 0 も許容する。
    """
    out: list[float] = []
    n_zero_base = 0
    for b_raw, r_raw in pairs:
        try:
            b = float(b_raw)
            r = float(r_raw)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(b) or not np.isfinite(r):
            continue
        if b != 0.0:
            continue
        n_zero_base += 1
        out.append(r)
    return out, n_zero_base


def run(time_range: QueryTimeRange = None) -> None:
    """base_fee_msat = 0 に限定した fee_rate_ppm の帯別棒グラフ・低レンジ・ECDF を保存する。"""
    pairs = fetch_fee_pair_values(
        "fee_rate_ppm | base_fee_msat=0",
        ("DB_COLUMN_BASE_FEE_MSAT", "LN_COLUMN_BASE_FEE_MSAT"),
        "base_fee_msat",
        ("DB_COLUMN_FEE_RATE_PPM", "LN_COLUMN_FEE_RATE_PPM"),
        "fee_rate_ppm",
        time_range=time_range,
    )
    values, n_zero = _fee_rates_with_base_fee_zero(pairs)
    print(
        f"[fee_rate_ppm | base_fee_msat=0] base_fee=0 の行: {n_zero} 件 "
        f"（全ペア {len(pairs)} 件）",
        flush=True,
    )
    log_numeric_summary("fee_rate_ppm (base_fee_msat=0 のみ)", values, show_mode=False)

    print(
        "[fee_rate_ppm | base_fee_msat=0] 帯別棒グラフ（0〜2000 ppm、50 ppm 帯・縦軸 log）…",
        flush=True,
    )
    plot_ppm_band_bar_chart(
        values=values,
        title=(
            "Fee Rate (ppm) by band: channels with Base Fee = 0 msat "
            f"(0–{FEE_RATE_DISPLAY_MAX_PPM:g} ppm, {FEE_RATE_BAND_WIDTH_PPM:g} ppm bands, log Y)"
        ),
        xlabel="Fee rate band (ppm)",
        output_path=OUTPUT_PATH_BANDS,
        band_width_ppm=FEE_RATE_BAND_WIDTH_PPM,
        display_max_ppm=FEE_RATE_DISPLAY_MAX_PPM,
        y_log_scale=True,
    )

    print(
        "[fee_rate_ppm | base_fee_msat=0] 低レンジヒストグラム（0〜50 ppm、1 ppm ビン）…",
        flush=True,
    )
    plot_fee_distribution(
        values=values,
        title=(
            "Fee Rate (ppm): Base Fee = 0 msat only, 0–50, 1 ppm bins"
        ),
        xlabel="Fee Rate (ppm)",
        output_path=OUTPUT_PATH_LOW,
        bin_width_msat=FEE_RATE_LOW_BIN_WIDTH_PPM,
        display_max_msat=FEE_RATE_LOW_DISPLAY_MAX_PPM,
        x_major_tick_step_msat=FEE_RATE_LOW_X_MAJOR_TICK_PPM,
        axis_unit_label="ppm",
    )

    print("[fee_rate_ppm | base_fee_msat=0] ECDF（0〜2000 ppm）…", flush=True)
    plot_fee_ecdf(
        values=values,
        title=(
            "Fee Rate (ppm): empirical CDF, Base Fee = 0 msat, "
            f"0–{FEE_RATE_DISPLAY_MAX_PPM:g} ppm"
        ),
        xlabel="Fee Rate (ppm)",
        output_path=OUTPUT_PATH_CDF,
        x_max_msat=FEE_RATE_DISPLAY_MAX_PPM,
        x_major_tick_step_msat=FEE_RATE_CDF_X_MAJOR_TICK_PPM,
    )


def main() -> None:
    """コマンドラインから ``run`` を起動する。"""
    parser = argparse.ArgumentParser(
        description="base_fee=0 のチャネルに限った比例手数料率（ppm）の分布を出力する。"
    )
    add_query_time_arguments(parser)
    args = parser.parse_args()
    run(time_range=time_range_from_namespace(args))


if __name__ == "__main__":
    main()
