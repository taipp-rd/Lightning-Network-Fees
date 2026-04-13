"""分析スクリプト共通: クエリ対象期間を argparse で受け取る。"""

from __future__ import annotations

import argparse
from datetime import datetime

from src.db.fee_snapshot_query import QueryTimeRange


def parse_iso_datetime(raw: str) -> datetime:
    """
    ISO 8601 形式の文字列を ``datetime`` に変換する。

    ``2024-03-01T12:00:00`` や ``2024-03-01``（深夜 0 時扱い）、
    タイムゾーン付き ``...Z`` / ``...+00:00`` を想定する。
    """
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"時刻として解釈できません（ISO 8601 を想定）: {raw!r}"
        ) from exc


def add_query_time_arguments(parser: argparse.ArgumentParser) -> None:
    """DB クエリの対象時刻窓を指定するオプションを付与する。"""
    group = parser.add_argument_group("クエリ対象時刻（省略時は従来どおり「全体の最新」）")
    group.add_argument(
        "--time-mode",
        choices=("latest", "range"),
        default="latest",
        help="latest: 期間指定なし（MAX スナップショットまたはチャネルごと全体最新）。"
        " range: --time-start / --time-end で両端を含む範囲を指定。",
    )
    group.add_argument(
        "--time-start",
        type=parse_iso_datetime,
        default=None,
        metavar="ISO8601",
        help="期間の開始（--time-mode range のとき必須）",
    )
    group.add_argument(
        "--time-end",
        type=parse_iso_datetime,
        default=None,
        metavar="ISO8601",
        help="期間の終了（--time-mode range のとき必須）",
    )


def time_range_from_namespace(args: argparse.Namespace) -> QueryTimeRange:
    """
    パース済み引数から ``QueryTimeRange`` を返す。

    ``time-mode=latest`` のときは None。
    """
    if args.time_mode == "latest":
        if args.time_start is not None or args.time_end is not None:
            raise SystemExit(
                "エラー: --time-mode latest のときは --time-start / --time-end を付けないでください。"
            )
        return None

    if args.time_start is None or args.time_end is None:
        raise SystemExit(
            "エラー: --time-mode range では --time-start と --time-end の両方が必要です。"
        )
    if args.time_start > args.time_end:
        raise SystemExit(
            "エラー: --time-start は --time-end 以下である必要があります。"
        )
    return (args.time_start, args.time_end)
