"""
ORDER 時刻が属する暦月ごとに「その月内でチャネル最新の1行」を取り、
base_fee / fee_rate の経験累積分布（ECDF）を月別に色分けして同一グラフに重ねる。

開始月は DB の ORDER 時刻列の最小値が属する暦月、終了月は **実行日の暦月**（ローカル日付）。
"""

from __future__ import annotations

import argparse
import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterator

from src.analysis.run_helpers import fetch_fee_column_values
from src.db.fee_snapshot_query import QueryTimeRange, fetch_order_time_column_min
from src.paths import PROJECT_ROOT
from src.visualization.charts import plot_ecdf_monthly_overlay

OUTPUT_BASE_FEE = PROJECT_ROOT / "output" / "base_fee_msat_ecdf_by_month.png"
OUTPUT_FEE_RATE = PROJECT_ROOT / "output" / "fee_rate_ppm_ecdf_by_month.png"

BASE_FEE_X_MAX = 10000.0
BASE_FEE_TICK = 500.0
FEE_RATE_X_MAX = 2000.0
FEE_RATE_TICK = 100.0


def _year_month_from_min_value(raw: object) -> tuple[int, int]:
    """DB の ORDER 最小型を UTC 暦の (年, 月) に正規化する。"""
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.year, dt.month
    if isinstance(raw, (int, float)):
        dt = datetime.fromtimestamp(int(raw), tz=timezone.utc)
        return dt.year, dt.month
    if isinstance(raw, Decimal):
        dt = datetime.fromtimestamp(int(raw), tz=timezone.utc)
        return dt.year, dt.month
    raise TypeError(f"ORDER 時刻列の MIN が未対応型です: {type(raw)!r}")


def _iter_year_months_inclusive(
    start: tuple[int, int], end: tuple[int, int]
) -> Iterator[tuple[int, int]]:
    y, m = start
    ye, me = end
    while (y, m) <= (ye, me):
        yield (y, m)
        m += 1
        if m > 12:
            m = 1
            y += 1


def _utc_month_range(y: int, month: int) -> QueryTimeRange:
    """暦月の両端（UTC・秒境界は既存の range 指定と同じく日末 23:59:59）。"""
    last = calendar.monthrange(y, month)[1]
    t0 = datetime(y, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(y, month, last, 23, 59, 59, tzinfo=timezone.utc)
    return (t0, t1)


def run() -> None:
    """DB を読み、月次 ECDF の PNG を2枚保存する。"""
    print(
        "[monthly_ecdf] ORDER 時刻列の最小値を取得しています…"
        "（テーブルが大きいと数十秒〜かかることがあります）",
        flush=True,
    )
    raw_min = fetch_order_time_column_min()
    if raw_min is None:
        print("[monthly_ecdf] ORDER 時刻列にデータがありません。", flush=True)
        return

    try:
        first_ym = _year_month_from_min_value(raw_min)
    except TypeError as exc:
        print(f"[monthly_ecdf] {exc}", flush=True)
        return

    print(f"[monthly_ecdf] ORDER 時刻の最小値: {raw_min!r} → 開始暦月 {first_ym[0]:04d}-{first_ym[1]:02d}", flush=True)

    today = date.today()
    end_ym = (today.year, today.month)
    if first_ym > end_ym:
        print(
            f"[monthly_ecdf] データ開始月 {first_ym} が終了月 {end_ym} より後です。",
            flush=True,
        )
        return

    months = list(_iter_year_months_inclusive(first_ym, end_ym))
    n_months = len(months)
    print(
        f"[monthly_ecdf] 対象暦月: {first_ym[0]:04d}-{first_ym[1]:02d} ～ "
        f"{end_ym[0]:04d}-{end_ym[1]:02d}（全 {n_months} ヶ月・各月は当該月内チャネル最新1行）",
        flush=True,
    )

    series_base: list[tuple[str, list[Any]]] = []
    series_fee: list[tuple[str, list[Any]]] = []

    for i, (y, m) in enumerate(months, start=1):
        label = f"{y:04d}-{m:02d}"
        tr = _utc_month_range(y, m)
        print(
            f"[monthly_ecdf] [{i}/{n_months}] {label} — base_fee 列を取得中…",
            flush=True,
        )
        vals_b = fetch_fee_column_values(
            f"monthly base_fee {label}",
            ("DB_COLUMN_BASE_FEE_MSAT", "LN_COLUMN_BASE_FEE_MSAT"),
            "base_fee_msat",
            time_range=tr,
            silent=True,
        )
        print(
            f"[monthly_ecdf] [{i}/{n_months}] {label} — fee_rate 列を取得中…",
            flush=True,
        )
        vals_f = fetch_fee_column_values(
            f"monthly fee_rate {label}",
            ("DB_COLUMN_FEE_RATE_PPM", "LN_COLUMN_FEE_RATE_PPM"),
            "fee_rate_ppm",
            time_range=tr,
            silent=True,
        )
        nb, nf = len(vals_b), len(vals_f)
        if nb > 0:
            series_base.append((label, vals_b))
        if nf > 0:
            series_fee.append((label, vals_f))
        if nb == 0 and nf == 0:
            print(f"[monthly_ecdf] [{i}/{n_months}] {label}: 両列 0 件のためスキップ", flush=True)
        else:
            print(
                f"[monthly_ecdf] [{i}/{n_months}] {label}: 完了 "
                f"(base_fee {nb} 件, fee_rate {nf} 件)",
                flush=True,
            )

    print("[monthly_ecdf] 累積分布グラフを描画・保存しています…", flush=True)
    plot_ecdf_monthly_overlay(
        series_base,
        title=(
            "Base Fee (msat): empirical CDF by month "
            "(latest per channel within each calendar month)"
        ),
        xlabel="Base Fee (msat)",
        output_path=OUTPUT_BASE_FEE,
        x_min=0.0,
        x_max=BASE_FEE_X_MAX,
        x_major_tick_step=BASE_FEE_TICK,
    )
    plot_ecdf_monthly_overlay(
        series_fee,
        title=(
            "Fee Rate (ppm): empirical CDF by month "
            "(latest per channel within each calendar month)"
        ),
        xlabel="Fee Rate (ppm)",
        output_path=OUTPUT_FEE_RATE,
        x_min=0.0,
        x_max=FEE_RATE_X_MAX,
        x_major_tick_step=FEE_RATE_TICK,
    )
    print("[monthly_ecdf] すべて完了しました。", flush=True)


def main() -> None:
    """コマンドラインから ``run`` を起動する。"""
    parser = argparse.ArgumentParser(
        description=(
            "ORDER 時刻の属する暦月ごとにチャネル最新1行を取り、"
            "base_fee / fee_rate の ECDF を月別に重ね描きする。"
        )
    )
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
