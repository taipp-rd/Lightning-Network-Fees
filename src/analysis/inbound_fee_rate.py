from src.analysis.run_helpers import fetch_fee_column_values
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_fee_distribution, plot_fee_ecdf

OUTPUT_PATH = PROJECT_ROOT / "output" / "inbound_fee_rate.png"
OUTPUT_PATH_CDF = PROJECT_ROOT / "output" / "inbound_fee_rate_cdf.png"

# 横軸: −1000〜500 ppm を 50 ppm ビン、主目盛 100 ppm、縦軸は対数
INBOUND_FEE_RATE_BIN_WIDTH_PPM = 50.0
INBOUND_FEE_RATE_DISPLAY_MIN_PPM = -1000.0
INBOUND_FEE_RATE_DISPLAY_MAX_PPM = 500.0
INBOUND_FEE_RATE_X_MAJOR_TICK_PPM = 100.0


def run() -> None:
    """最新スナップショットの inbound_fee_rate 分布をグラフ化する。"""
    values = fetch_fee_column_values(
        "inbound_fee_rate",
        ("DB_COLUMN_INBOUND_FEE_RATE", "LN_COLUMN_INBOUND_FEE_RATE"),
        "inbound_fee_rate",
    )

    print(
        "[inbound_fee_rate] ヒストグラム（−1000〜500 ppm・50 ppm ビン・主目盛 100 ppm・log Y）…",
        flush=True,
    )
    plot_fee_distribution(
        values=values,
        title="Inbound Fee Rate: −1000–500 ppm, 50 ppm bins, log Y",
        xlabel="Inbound Fee Rate (ppm)",
        output_path=OUTPUT_PATH,
        bin_width_msat=INBOUND_FEE_RATE_BIN_WIDTH_PPM,
        display_min_msat=INBOUND_FEE_RATE_DISPLAY_MIN_PPM,
        display_max_msat=INBOUND_FEE_RATE_DISPLAY_MAX_PPM,
        y_log_scale=True,
        x_major_tick_step_msat=INBOUND_FEE_RATE_X_MAJOR_TICK_PPM,
        axis_unit_label="ppm",
    )

    print("[inbound_fee_rate] 累積分布（ECDF）を描画しています…", flush=True)
    plot_fee_ecdf(
        values=values,
        title="Inbound Fee Rate (ppm): empirical CDF, −1000–500 ppm",
        xlabel="Inbound Fee Rate (ppm)",
        output_path=OUTPUT_PATH_CDF,
        x_min_msat=INBOUND_FEE_RATE_DISPLAY_MIN_PPM,
        x_max_msat=INBOUND_FEE_RATE_DISPLAY_MAX_PPM,
        x_major_tick_step_msat=INBOUND_FEE_RATE_X_MAJOR_TICK_PPM,
    )


if __name__ == "__main__":
    run()
