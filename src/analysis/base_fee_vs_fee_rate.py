"""
ベース手数料（msat）と比例手数料率（ppm）の関係を、同一チャネル行の組で散布図にする。

横軸 0〜2000 msat、縦軸 0〜2000 ppm に固定し、範囲内の点のみ描画する。
"""

import argparse

from src.analysis.run_helpers import fetch_fee_pair_values
from src.analysis.time_range_cli import add_query_time_arguments, time_range_from_namespace
from src.db.fee_snapshot_query import QueryTimeRange
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_fee_pair_scatter

OUTPUT_PATH = PROJECT_ROOT / "output" / "base_fee_msat_vs_fee_rate_ppm_scatter.png"

# 表示範囲（軸の上限）。範囲外の組はプロットしない（件数はログに出る）。
SCATTER_X_MAX_MSAT = 2000.0
SCATTER_Y_MAX_PPM = 2000.0
# 主目盛間隔
SCATTER_X_MAJOR_TICK_MSAT = 200.0
SCATTER_Y_MAJOR_TICK_PPM = 200.0


def run(time_range: QueryTimeRange = None) -> None:
    """base_fee_msat を横軸、fee_rate_ppm を縦軸とした散布図を保存する。"""
    pairs = fetch_fee_pair_values(
        "base_fee_msat vs fee_rate_ppm",
        ("DB_COLUMN_BASE_FEE_MSAT", "LN_COLUMN_BASE_FEE_MSAT"),
        "base_fee_msat",
        ("DB_COLUMN_FEE_RATE_PPM", "LN_COLUMN_FEE_RATE_PPM"),
        "fee_rate_ppm",
        time_range=time_range,
    )
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    print(
        "[base_fee_msat vs fee_rate_ppm] 散布図を描画しています"
        f"（0〜{SCATTER_X_MAX_MSAT:g} msat × 0〜{SCATTER_Y_MAX_PPM:g} ppm）…",
        flush=True,
    )
    plot_fee_pair_scatter(
        x_values=xs,
        y_values=ys,
        title=(
            "Base Fee (msat) vs Fee Rate (ppm): scatter, "
            f"0–{SCATTER_X_MAX_MSAT:g} × 0–{SCATTER_Y_MAX_PPM:g}"
        ),
        xlabel="Base Fee (msat)",
        ylabel="Fee Rate (ppm)",
        output_path=OUTPUT_PATH,
        x_max=SCATTER_X_MAX_MSAT,
        y_max=SCATTER_Y_MAX_PPM,
        x_major_tick=SCATTER_X_MAJOR_TICK_MSAT,
        y_major_tick=SCATTER_Y_MAJOR_TICK_PPM,
    )


def main() -> None:
    """コマンドラインから ``run`` を起動する。"""
    parser = argparse.ArgumentParser(
        description="ベース手数料と比例手数料率の散布図を出力する。"
    )
    add_query_time_arguments(parser)
    args = parser.parse_args()
    run(time_range=time_range_from_namespace(args))


if __name__ == "__main__":
    main()
