"""
ベース手数料（BOLT7 channel_update の fee_base_msat 相当、DB では多く rp_base_fee_msat）。

チャネルごとに **1行だけ**（ゴシップ上の最新更新）を使うには `.env` で
`LN_FEE_QUERY_MODE=latest_per_channel` とし、時刻列・タイブレーク列を合わせる。
"""

import argparse

from src.analysis.run_helpers import fetch_fee_column_values, log_numeric_summary
from src.analysis.time_range_cli import add_query_time_arguments, time_range_from_namespace
from src.db.fee_snapshot_query import QueryTimeRange
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_fee_distribution, plot_fee_ecdf

OUTPUT_PATH = PROJECT_ROOT / "output" / "base_fee_msat.png"
OUTPUT_PATH_DETAIL = PROJECT_ROOT / "output" / "base_fee_msat_0_1000_50msat.png"
OUTPUT_PATH_CDF = PROJECT_ROOT / "output" / "base_fee_msat_cdf.png"

# 単一ヒストグラム: 0〜10000 msat を 100 msat 刻み（101 境界・100 ビン）
BASE_FEE_BIN_WIDTH_MSAT = 100.0
BASE_FEE_DISPLAY_MAX_MSAT = 10000.0
# 横軸の主目盛間隔（msat）
BASE_FEE_X_MAJOR_TICK_MSAT = 500.0

# 別図: 0〜1000 msat を 50 msat ビン、横主目盛 100 msat、縦軸は線形
BASE_FEE_DETAIL_BIN_WIDTH_MSAT = 50.0
BASE_FEE_DETAIL_DISPLAY_MAX_MSAT = 1000.0
BASE_FEE_DETAIL_X_MAJOR_TICK_MSAT = 100.0

# 最頻値ログ用: ヒストグラムと同じ 0〜10000 msat 範囲で集計
BASE_FEE_MODE_RANGE_MAX_MSAT = 10000.0


def run(time_range: QueryTimeRange = None) -> None:
    """チャネルごとの最新行について、ベース手数料の分布をヒストグラム化する。"""
    values = fetch_fee_column_values(
        "base_fee_msat",
        ("DB_COLUMN_BASE_FEE_MSAT", "LN_COLUMN_BASE_FEE_MSAT"),
        "base_fee_msat",
        time_range=time_range,
    )
    log_numeric_summary(
        "base_fee_msat",
        values,
        show_mode=True,
        mode_display_range_msat=(0.0, BASE_FEE_MODE_RANGE_MAX_MSAT),
    )

    print(
        "[base_fee_msat] ヒストグラムを描画しています（0〜10000 msat、100 msat ビン・1 枚）…",
        flush=True,
    )
    plot_fee_distribution(
        values=values,
        title="Base Fee Distribution (msat): 0–10000, 100 msat bins, log Y",
        xlabel="Base Fee (msat)",
        output_path=OUTPUT_PATH,
        bin_width_msat=BASE_FEE_BIN_WIDTH_MSAT,
        display_max_msat=BASE_FEE_DISPLAY_MAX_MSAT,
        y_log_scale=True,
        x_major_tick_step_msat=BASE_FEE_X_MAJOR_TICK_MSAT,
    )

    print(
        "[base_fee_msat] 別図: 0〜1000 msat・50 msat ビン・主目盛 100 msat・縦軸 linear …",
        flush=True,
    )
    plot_fee_distribution(
        values=values,
        title="Base Fee (msat): 0–1000, 50 msat bins, linear Y",
        xlabel="Base Fee (msat)",
        output_path=OUTPUT_PATH_DETAIL,
        bin_width_msat=BASE_FEE_DETAIL_BIN_WIDTH_MSAT,
        display_max_msat=BASE_FEE_DETAIL_DISPLAY_MAX_MSAT,
        y_log_scale=False,
        x_major_tick_step_msat=BASE_FEE_DETAIL_X_MAJOR_TICK_MSAT,
        axis_unit_label="msat",
    )

    print("[base_fee_msat] 累積分布（ECDF）を描画しています…", flush=True)
    plot_fee_ecdf(
        values=values,
        title="Base Fee (msat): empirical CDF, 0–10000 msat",
        xlabel="Base Fee (msat)",
        output_path=OUTPUT_PATH_CDF,
        x_max_msat=BASE_FEE_DISPLAY_MAX_MSAT,
        x_major_tick_step_msat=BASE_FEE_X_MAJOR_TICK_MSAT,
    )


def main() -> None:
    """コマンドラインから ``run`` を起動する。"""
    parser = argparse.ArgumentParser(
        description="ベース手数料（msat）の分布をヒストグラム・ECDF で出力する。"
    )
    add_query_time_arguments(parser)
    args = parser.parse_args()
    run(time_range=time_range_from_namespace(args))


if __name__ == "__main__":
    main()
