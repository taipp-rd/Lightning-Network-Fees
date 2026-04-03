"""分析スクリプト共通: DB から値列を取り出し、進捗を標準出力へ出す。"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.db.connection import get_connection
from src.db.fee_snapshot_query import (
    fee_distribution_select_sql,
    fee_pair_distribution_select_sql,
)


def fetch_fee_column_values(
    log_label: str,
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
) -> list[Any]:
    """
    手数料（または ppm）の1列を全行取得する。

    進捗は [log_label] プレフィックス付きで stdout に出す。
    """
    query, mode_desc = fee_distribution_select_sql(
        value_column_env_keys,
        default_value_column,
    )
    print(f"[{log_label}] クエリ方式: {mode_desc}", flush=True)

    print(f"[{log_label}] DB に接続しています…", flush=True)
    with get_connection() as conn:
        with conn.cursor() as cur:
            print(
                f"[{log_label}] SELECT を実行しています（件数が多いと時間がかかります）…",
                flush=True,
            )
            cur.execute(query)
            print(f"[{log_label}] サーバから結果を受信中…", flush=True)
            rows = cur.fetchall()

    print(f"[{log_label}] 取得完了: {len(rows)} 行（分布に使う値の数）", flush=True)
    return [row[0] for row in rows]


def fetch_fee_pair_values(
    log_label: str,
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
) -> list[tuple[Any, Any]]:
    """
    手数料（または ppm）の2列を、同一行・同一クエリモードで全行取得する。

    進捗は [log_label] プレフィックス付きで stdout に出す。
    """
    query, mode_desc = fee_pair_distribution_select_sql(
        value_column_env_keys_a,
        default_value_column_a,
        value_column_env_keys_b,
        default_value_column_b,
    )
    print(f"[{log_label}] クエリ方式: {mode_desc}", flush=True)

    print(f"[{log_label}] DB に接続しています…", flush=True)
    with get_connection() as conn:
        with conn.cursor() as cur:
            print(
                f"[{log_label}] SELECT を実行しています（件数が多いと時間がかかります）…",
                flush=True,
            )
            cur.execute(query)
            print(f"[{log_label}] サーバから結果を受信中…", flush=True)
            rows = cur.fetchall()

    print(f"[{log_label}] 取得完了: {len(rows)} 行（散布図に使う (列A, 列B) の組数）", flush=True)
    return [(row[0], row[1]) for row in rows]


def _mode_from_rounded_msat(arr: np.ndarray) -> tuple[float, int] | None:
    """ミリサトシを整数に丸めたうえでの最頻値とその件数。"""
    if arr.size == 0:
        return None
    rounded = np.rint(arr).astype(np.int64)
    vals, counts = np.unique(rounded, return_counts=True)
    i = int(np.argmax(counts))
    return float(vals[i]), int(counts[i])


def log_numeric_summary(
    log_label: str,
    values: list[Any],
    *,
    show_mode: bool = False,
    mode_display_range_msat: tuple[float, float] | None = None,
) -> None:
    """
    取得した数値列の要約を標準出力へ出す。

    show_mode が True のとき、整数 msat に丸めた最頻値を表示する。
    mode_display_range_msat が (lo, hi) のとき、その範囲に入る値だけで再計算した最頻値も出す。
    """
    arr = np.asarray(values, dtype=np.float64)
    n = int(arr.size)
    if n == 0:
        print(f"[{log_label}] 要約: 0 件", flush=True)
        return
    n_zero = int(np.sum(arr == 0))
    n_pos = int(np.sum(arr > 0))
    print(
        f"[{log_label}] 要約: n={n}, min={arr.min():.6g}, max={arr.max():.6g}, "
        f"mean（参考・外れ値の影響あり）={arr.mean():.6g}, ==0 が {n_zero} 件, >0 が {n_pos} 件",
        flush=True,
    )

    if not show_mode:
        return

    m = _mode_from_rounded_msat(arr)
    if m is not None:
        print(
            f"[{log_label}] 最頻値（全体・msat 整数化）: {m[0]:.0f} msat（{m[1]} チャネル）",
            flush=True,
        )

    if mode_display_range_msat is not None:
        lo, hi = mode_display_range_msat
        sub = arr[(arr >= lo) & (arr <= hi)]
        m2 = _mode_from_rounded_msat(sub)
        if m2 is None:
            print(
                f"[{log_label}] 最頻値（{lo:g}〜{hi:g} msat）: 該当データなし",
                flush=True,
            )
        else:
            print(
                f"[{log_label}] 最頻値（{lo:g}〜{hi:g} msat のみ）: {m2[0]:.0f} msat（{m2[1]} チャネル）",
                flush=True,
            )
