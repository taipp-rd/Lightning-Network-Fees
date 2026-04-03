from src.analysis.run_helpers import fetch_fee_column_values
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_fee_distribution, plot_fee_ecdf

OUTPUT_PATH = PROJECT_ROOT / "output" / "fee_rate_ppm.png"
OUTPUT_PATH_CDF = PROJECT_ROOT / "output" / "fee_rate_ppm_cdf.png"

# 0〜2000 ppm を 50 ppm ビン（横軸主目盛は 100 ppm 間隔）
FEE_RATE_BIN_WIDTH_PPM = 50.0
FEE_RATE_DISPLAY_MAX_PPM = 2000.0
FEE_RATE_X_MAJOR_TICK_PPM = 100.0


def run() -> None:
    """最新スナップショットの fee_rate_ppm をヒストグラムと経験累積分布（ECDF）で可視化する。"""
    values = fetch_fee_column_values(
        "fee_rate_ppm",
        ("DB_COLUMN_FEE_RATE_PPM", "LN_COLUMN_FEE_RATE_PPM"),
        "fee_rate_ppm",
    )

    print(
        "[fee_rate_ppm] ヒストグラムを描画しています（0〜2000 ppm、50 ppm ビン、縦軸 linear）…",
        flush=True,
    )
    plot_fee_distribution(
        values=values,
        title="Fee Rate Distribution (ppm): 0–2000, 50 ppm bins",
        xlabel="Fee Rate (ppm)",
        output_path=OUTPUT_PATH,
        bin_width_msat=FEE_RATE_BIN_WIDTH_PPM,
        display_max_msat=FEE_RATE_DISPLAY_MAX_PPM,
        x_major_tick_step_msat=FEE_RATE_X_MAJOR_TICK_PPM,
        axis_unit_label="ppm",
    )

    print("[fee_rate_ppm] 累積分布（ECDF）を描画しています…", flush=True)
    plot_fee_ecdf(
        values=values,
        title="Fee Rate (ppm): empirical CDF, 0–2000 ppm",
        xlabel="Fee Rate (ppm)",
        output_path=OUTPUT_PATH_CDF,
        x_max_msat=FEE_RATE_DISPLAY_MAX_PPM,
        x_major_tick_step_msat=FEE_RATE_X_MAJOR_TICK_PPM,
    )
