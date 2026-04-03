from src.analysis.run_helpers import fetch_fee_column_values
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_fee_distribution, plot_fee_ecdf

OUTPUT_PATH = PROJECT_ROOT / "output" / "inbound_base_fee.png"
OUTPUT_PATH_CDF = PROJECT_ROOT / "output" / "inbound_base_fee_cdf.png"

# 横軸: −1000〜500 msat を 50 msat ビン、主目盛 100 msat、縦軸は対数
INBOUND_BASE_FEE_BIN_WIDTH_MSAT = 50.0
INBOUND_BASE_FEE_DISPLAY_MIN_MSAT = -1000.0
INBOUND_BASE_FEE_DISPLAY_MAX_MSAT = 500.0
INBOUND_BASE_FEE_X_MAJOR_TICK_MSAT = 100.0


def run() -> None:
    """最新スナップショットの inbound_base_fee 分布をグラフ化する。"""
    values = fetch_fee_column_values(
        "inbound_base_fee",
        ("DB_COLUMN_INBOUND_BASE_FEE", "LN_COLUMN_INBOUND_BASE_FEE"),
        "inbound_base_fee",
    )

    print(
        "[inbound_base_fee] ヒストグラム（−1000〜500 msat・50 msat ビン・主目盛 100 msat・log Y）…",
        flush=True,
    )
    plot_fee_distribution(
        values=values,
        title="Inbound Base Fee: −1000–500 msat, 50 msat bins, log Y",
        xlabel="Inbound Base Fee (msat)",
        output_path=OUTPUT_PATH,
        bin_width_msat=INBOUND_BASE_FEE_BIN_WIDTH_MSAT,
        display_min_msat=INBOUND_BASE_FEE_DISPLAY_MIN_MSAT,
        display_max_msat=INBOUND_BASE_FEE_DISPLAY_MAX_MSAT,
        y_log_scale=True,
        x_major_tick_step_msat=INBOUND_BASE_FEE_X_MAJOR_TICK_MSAT,
    )

    print("[inbound_base_fee] 累積分布（ECDF）を描画しています…", flush=True)
    plot_fee_ecdf(
        values=values,
        title="Inbound Base Fee (msat): empirical CDF, −1000–500 msat",
        xlabel="Inbound Base Fee (msat)",
        output_path=OUTPUT_PATH_CDF,
        x_min_msat=INBOUND_BASE_FEE_DISPLAY_MIN_MSAT,
        x_max_msat=INBOUND_BASE_FEE_DISPLAY_MAX_MSAT,
        x_major_tick_step_msat=INBOUND_BASE_FEE_X_MAJOR_TICK_MSAT,
    )
