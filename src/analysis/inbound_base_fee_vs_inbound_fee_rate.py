"""
Inbound base fee（msat）と inbound fee rate（ppm）を、同一行の組で散布図にする。

表示範囲は横・縦とも −1000〜500。主目盛 100、副目盛 50（グリッド用）。
"""

import argparse

from src.analysis.run_helpers import fetch_fee_pair_values
from src.analysis.time_range_cli import add_query_time_arguments, time_range_from_namespace
from src.db.fee_snapshot_query import QueryTimeRange
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_fee_pair_scatter_rect

OUTPUT_PATH = (
    PROJECT_ROOT / "output" / "inbound_base_fee_vs_inbound_fee_rate_scatter.png"
)

# 表示矩形（msat × ppm）。範囲外の組はプロットしない。
SCATTER_MIN = -1000.0
SCATTER_MAX = 500.0
# 主目盛（ラベル）間隔、副目盛（50 刻みの補助線）
SCATTER_MAJOR_TICK = 100.0
SCATTER_MINOR_TICK = 50.0


def run(time_range: QueryTimeRange = None) -> None:
    """inbound_base_fee を横軸、inbound_fee_rate を縦軸とした散布図を保存する。"""
    pairs = fetch_fee_pair_values(
        "inbound_base_fee vs inbound_fee_rate",
        ("DB_COLUMN_INBOUND_BASE_FEE", "LN_COLUMN_INBOUND_BASE_FEE"),
        "inbound_base_fee",
        ("DB_COLUMN_INBOUND_FEE_RATE", "LN_COLUMN_INBOUND_FEE_RATE"),
        "inbound_fee_rate",
        time_range=time_range,
    )
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    print(
        "[inbound_base_fee vs inbound_fee_rate] 散布図を描画しています"
        f"（{SCATTER_MIN:g}〜{SCATTER_MAX:g} msat × {SCATTER_MIN:g}〜{SCATTER_MAX:g} ppm、"
        f"主目盛 {SCATTER_MAJOR_TICK:g}、副目盛 {SCATTER_MINOR_TICK:g}）…",
        flush=True,
    )
    plot_fee_pair_scatter_rect(
        x_values=xs,
        y_values=ys,
        title=(
            "Inbound Base Fee (msat) vs Inbound Fee Rate (ppm): scatter, "
            f"{SCATTER_MIN:g}–{SCATTER_MAX:g} × {SCATTER_MIN:g}–{SCATTER_MAX:g}"
        ),
        xlabel="Inbound Base Fee (msat)",
        ylabel="Inbound Fee Rate (ppm)",
        output_path=OUTPUT_PATH,
        x_min=SCATTER_MIN,
        x_max=SCATTER_MAX,
        y_min=SCATTER_MIN,
        y_max=SCATTER_MAX,
        major_tick=SCATTER_MAJOR_TICK,
        minor_tick=SCATTER_MINOR_TICK,
    )


def main() -> None:
    """コマンドラインから ``run`` を起動する。"""
    parser = argparse.ArgumentParser(
        description="インバウンドベース手数料とインバウンド比例手数料率の散布図を出力する。"
    )
    add_query_time_arguments(parser)
    args = parser.parse_args()
    run(time_range=time_range_from_namespace(args))


if __name__ == "__main__":
    main()
