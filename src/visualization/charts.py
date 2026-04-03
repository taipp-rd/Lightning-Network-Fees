from decimal import Decimal
from pathlib import Path
from typing import Sequence, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator, MaxNLocator, MultipleLocator

Numeric = Union[int, float, Decimal]


def _histogram_bin_edges_msat(
    values: Sequence[Numeric],
    bin_width_msat: float,
    max_bins: int = 5000,
) -> np.ndarray:
    """
    横軸を固定幅（msat）で区切るためのビン境界を返す。
    左端は 0 未満にならないようクランプする。
    異常値でビン数が膨らみすぎないよう、幅ベースで max_bins を超えたら上端を切り詰める。
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return np.array([0.0, float(bin_width_msat)])

    lo = float(np.min(arr))
    hi = float(np.max(arr))
    w = float(bin_width_msat)
    if w <= 0:
        raise ValueError("bin_width_msat は正の数である必要があります。")

    left = max(0.0, np.floor(lo / w) * w)
    right = max(left + w, np.ceil(hi / w) * w)
    span = right - left
    if span / w > max_bins:
        right = left + w * max_bins
        print(
            f"[charts] ビン数が {max_bins} を超えるため、X 軸上端を {right:g} msat に切り詰めました。",
            flush=True,
        )

    edges = np.arange(left, right + w, w, dtype=np.float64)
    if edges.size < 2:
        edges = np.array([left, left + w], dtype=np.float64)
    return edges


def plot_fee_distribution(
    values: Sequence[Numeric],
    title: str,
    xlabel: str,
    output_path: Union[str, Path],
    bins: int = 100,
    bin_width_msat: float | None = None,
    display_min_msat: float | None = None,
    display_max_msat: float | None = None,
    y_log_scale: bool = False,
    x_major_tick_step_msat: float | None = None,
    axis_unit_label: str = "msat",
) -> None:
    """
    手数料の分布図を作成する。

    X軸: 手数料の値、Y軸: チャネル数（行数）。
    bin_width_msat と display_max_msat を指定したときは等幅（msat）ビン。
    display_min_msat を省略すると横軸は 0〜display_max。
    display_min_msat を指定すると横軸は display_min〜display_max（負の下限も可）。
    y_log_scale が True のとき縦軸を対数（件数が 0 のビンは表示されない）。
    x_major_tick_step_msat を指定すると横軸の主目盛をその間隔（表示単位）にする。
    axis_unit_label はログ出力用（横軸の単位名。ppm など）。
    未指定時は bins（個数）で matplotlib に自動分割させる。
    """
    if not values:
        print("データが0件のためグラフは保存しません。")
        return

    output_path = Path(output_path)
    arr = np.asarray(values, dtype=np.float64)

    fig, ax = plt.subplots(figsize=(14, 6))
    apply_log_y = False

    if bin_width_msat is not None and display_max_msat is not None:
        w = float(bin_width_msat)
        xmax = float(display_max_msat)
        xmin = 0.0 if display_min_msat is None else float(display_min_msat)
        if w <= 0:
            raise ValueError("bin_width_msat は正の数である必要があります。")
        if display_min_msat is None:
            if xmax <= 0:
                raise ValueError(
                    "display_min_msat を省略したときは display_max_msat は正の数である必要があります。"
                )
        elif xmin >= xmax:
            raise ValueError("display_min_msat は display_max_msat より小さくしてください。")

        edges = np.arange(xmin, xmax + w, w, dtype=np.float64)
        mask = (arr >= xmin) & (arr <= xmax)
        n_in = int(np.sum(mask))
        n_below = int(np.sum(arr < xmin))
        n_above = int(np.sum(arr > xmax))
        apply_log_y = y_log_scale
        ax.hist(
            arr[mask],
            bins=edges,
            color="steelblue",
            edgecolor="0.25",
            linewidth=0.5,
            alpha=0.88,
            rwidth=0.92,
            log=apply_log_y,
        )
        ax.set_xlim(xmin, xmax)
        if x_major_tick_step_msat is not None:
            ax.xaxis.set_major_locator(MultipleLocator(float(x_major_tick_step_msat)))
        u = axis_unit_label
        range_desc = f"0〜{xmax:g}" if display_min_msat is None else f"{xmin:g}〜{xmax:g}"
        print(
            f"[charts] ヒストグラム: {range_desc} {u} を {w:g} {u} 刻み、"
            f"縦軸={'log' if apply_log_y else 'linear'}、"
            f"プロット対象 {n_in} 件、除外 {n_below + n_above} 件"
            f"（{xmin:g} 未満 {n_below}、{xmax:g} {u} 超 {n_above}）",
            flush=True,
        )
    elif bin_width_msat is not None:
        edges = _histogram_bin_edges_msat(values, bin_width_msat)
        ax.hist(values, bins=edges, edgecolor="black", alpha=0.7)
    else:
        ax.hist(values, bins=bins, edgecolor="black", alpha=0.7)

    ax.set_title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel(
        "Channel Count (log scale)" if apply_log_y else "Channel Count",
        fontsize=13,
    )
    if not apply_log_y:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    if apply_log_y:
        # データの最小件数が大きいと既定の ylim が 10^3 付近からになり、10^0〜が消える。
        # 下限を 1 (=10^0) に固定して桁の目盛りを揃える。
        _, ymax = ax.get_ylim()
        ax.set_ylim(bottom=1.0, top=max(float(ymax), 1.0))
        ax.yaxis.set_major_locator(LogLocator(base=10))
        ax.grid(axis="y", alpha=0.45, which="both")
    else:
        ax.grid(axis="y", alpha=0.5, which="major")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")


def plot_fee_ecdf(
    values: Sequence[Numeric],
    title: str,
    xlabel: str,
    output_path: Union[str, Path],
    x_max_msat: float | None = None,
    x_min_msat: float | None = None,
    x_major_tick_step_msat: float | None = None,
) -> None:
    """
    手数料の経験累積分布（ECDF）を描く。

    縦軸は F(x) = P(X ≤ x)（標本における累積割合）。
    x_max_msat を指定すると [x_min, x_max] に入る値だけを使い、横軸をその範囲に固定する。
    x_min_msat を省略したときは下限 0（従来どおり 0〜x_max）。
    """
    arr = np.asarray(values, dtype=np.float64)
    if x_max_msat is not None:
        xmax = float(x_max_msat)
        xmin = 0.0 if x_min_msat is None else float(x_min_msat)
        if xmin >= xmax:
            raise ValueError("x_min_msat は x_max_msat より小さくしてください。")
        arr = arr[(arr >= xmin) & (arr <= xmax)]
    else:
        arr = arr[np.isfinite(arr)]

    if arr.size == 0:
        print(f"[charts] ECDF: データ0件のため保存しません ({output_path})", flush=True)
        return

    x_sorted = np.sort(arr)
    n = int(x_sorted.size)
    y = np.arange(1, n + 1, dtype=np.float64) / n

    output_path = Path(output_path)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x_sorted, y, drawstyle="steps-post", color="steelblue", lw=1.8)
    ax.set_ylim(0.0, 1.0)
    ax.set_title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel("Cumulative probability F(x)", fontsize=13)
    ax.grid(True, alpha=0.45)
    if x_max_msat is not None:
        xmax = float(x_max_msat)
        xmin = 0.0 if x_min_msat is None else float(x_min_msat)
        ax.set_xlim(xmin, xmax)
    if x_major_tick_step_msat is not None:
        ax.xaxis.set_major_locator(MultipleLocator(float(x_major_tick_step_msat)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved (ECDF): {output_path}", flush=True)


def plot_fee_pair_scatter(
    x_values: Sequence[Numeric],
    y_values: Sequence[Numeric],
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Union[str, Path],
    x_max: float,
    y_max: float,
    *,
    x_major_tick: float | None = None,
    y_major_tick: float | None = None,
    point_size: float = 4.0,
    alpha: float = 0.22,
) -> None:
    """
    (x, y) の散布図を描く。表示範囲は 0〜x_max（横）・0〜y_max（縦）に固定する。

    両座標がそれぞれ [0, x_max]、[0, y_max] に入る点だけをプロットする。
    範囲外の組は件数ログに含める（高密度時は alpha・point_size で調整）。
    """
    if len(x_values) != len(y_values):
        raise ValueError("x_values と y_values の長さが一致しません。")

    output_path = Path(output_path)
    x_arr = np.asarray(x_values, dtype=np.float64)
    y_arr = np.asarray(y_values, dtype=np.float64)
    n_total = int(x_arr.size)
    if n_total == 0:
        print("[charts] 散布図: データ0件のため保存しません。", flush=True)
        return

    xm = float(x_max)
    ym = float(y_max)
    if xm <= 0 or ym <= 0:
        raise ValueError("x_max と y_max は正の数である必要があります。")

    inside = (
        np.isfinite(x_arr)
        & np.isfinite(y_arr)
        & (x_arr >= 0.0)
        & (x_arr <= xm)
        & (y_arr >= 0.0)
        & (y_arr <= ym)
    )
    n_in = int(np.sum(inside))
    n_out = n_total - n_in
    print(
        f"[charts] 散布図: 全 {n_total} 組、表示範囲内 {n_in} 組、範囲外 {n_out} 組",
        flush=True,
    )

    if n_in == 0:
        print("[charts] 散布図: 表示範囲内に点がないため保存しません。", flush=True)
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(
        x_arr[inside],
        y_arr[inside],
        s=point_size,
        c="steelblue",
        alpha=alpha,
        edgecolors="none",
    )
    ax.set_xlim(0.0, xm)
    ax.set_ylim(0.0, ym)
    ax.set_title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel(ylabel, fontsize=13)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.4)
    if x_major_tick is not None:
        ax.xaxis.set_major_locator(MultipleLocator(float(x_major_tick)))
    if y_major_tick is not None:
        ax.yaxis.set_major_locator(MultipleLocator(float(y_major_tick)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved (scatter): {output_path}", flush=True)


def plot_fee_pair_scatter_rect(
    x_values: Sequence[Numeric],
    y_values: Sequence[Numeric],
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Union[str, Path],
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    *,
    major_tick: float,
    minor_tick: float | None = None,
    point_size: float = 4.0,
    alpha: float = 0.22,
) -> None:
    """
    (x, y) の散布図を、指定した矩形 [x_min, x_max] × [y_min, y_max] に収まる点だけ描く。

    major_tick は主目盛（ラベル）間隔、minor_tick を指定すると副目盛を置き細いグリッドを描く。
    横・縦の表示範囲が同じ幅なら等方スケール（aspect equal）にする。
    """
    if len(x_values) != len(y_values):
        raise ValueError("x_values と y_values の長さが一致しません。")

    x_lo, x_hi = float(x_min), float(x_max)
    y_lo, y_hi = float(y_min), float(y_max)
    if x_lo >= x_hi or y_lo >= y_hi:
        raise ValueError("x_min < x_max かつ y_min < y_max である必要があります。")
    if major_tick <= 0:
        raise ValueError("major_tick は正の数である必要があります。")
    if minor_tick is not None and minor_tick <= 0:
        raise ValueError("minor_tick は正の数である必要があります。")

    output_path = Path(output_path)
    x_arr = np.asarray(x_values, dtype=np.float64)
    y_arr = np.asarray(y_values, dtype=np.float64)
    n_total = int(x_arr.size)
    if n_total == 0:
        print("[charts] 散布図（矩形）: データ0件のため保存しません。", flush=True)
        return

    inside = (
        np.isfinite(x_arr)
        & np.isfinite(y_arr)
        & (x_arr >= x_lo)
        & (x_arr <= x_hi)
        & (y_arr >= y_lo)
        & (y_arr <= y_hi)
    )
    n_in = int(np.sum(inside))
    n_out = n_total - n_in
    print(
        f"[charts] 散布図（矩形）: 全 {n_total} 組、表示範囲内 {n_in} 組、範囲外 {n_out} 組",
        flush=True,
    )

    if n_in == 0:
        print("[charts] 散布図（矩形）: 表示範囲内に点がないため保存しません。", flush=True)
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(
        x_arr[inside],
        y_arr[inside],
        s=point_size,
        c="steelblue",
        alpha=alpha,
        edgecolors="none",
    )
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.set_title(title, fontsize=16)
    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel(ylabel, fontsize=13)
    span_x = x_hi - x_lo
    span_y = y_hi - y_lo
    if span_x > 0 and span_y > 0 and np.isclose(span_x, span_y):
        ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_locator(MultipleLocator(float(major_tick)))
    ax.yaxis.set_major_locator(MultipleLocator(float(major_tick)))
    if minor_tick is not None:
        ax.xaxis.set_minor_locator(MultipleLocator(float(minor_tick)))
        ax.yaxis.set_minor_locator(MultipleLocator(float(minor_tick)))
    ax.grid(True, which="major", alpha=0.45)
    if minor_tick is not None:
        ax.grid(True, which="minor", alpha=0.22)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved (scatter rect): {output_path}", flush=True)
