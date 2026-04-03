"""
手数料関連列の型と、全行 vs チャネルごと最新1行の統計を表示する（調査用）。

使い方: プロジェクトルートで  python scripts/inspect_channel_update_types.py
"""

from __future__ import annotations

import os
import sys
from typing import Any

from psycopg2 import sql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.channels_relation import _validate_ident  # noqa: E402
from src.db.connection import _first_nonempty_env, get_connection  # noqa: E402


def _q(cur: Any, query: sql.Composed | str, params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
    cur.execute(query, params or ())
    return list(cur.fetchall())


def main() -> None:
    """information_schema と集計クエリで列型・件数を表示する。"""
    schema = _validate_ident(
        (_first_nonempty_env("LN_DB_SCHEMA", "DB_SCHEMA") or "public").strip(),
        "LN_DB_SCHEMA",
    )
    table = _validate_ident(
        (_first_nonempty_env("LN_CHANNELS_TABLE", "CHANNELS_TABLE") or "channel_update").strip(),
        "LN_CHANNELS_TABLE",
    )
    chan_k = _validate_ident(
        (_first_nonempty_env("LN_COLUMN_CHANNEL_KEY", "DB_COLUMN_CHANNEL_KEY") or "chan_id").strip(),
        "channel key",
    )
    order_t = _validate_ident(
        (
            _first_nonempty_env("LN_COLUMN_ORDER_TIME", "DB_COLUMN_ORDER_TIME")
            or _first_nonempty_env("LN_COLUMN_SNAPSHOT", "DB_COLUMN_SNAPSHOT")
            or "timestamp"
        ).strip(),
        "order time",
    )
    tie = _validate_ident(
        (_first_nonempty_env("LN_COLUMN_ORDER_TIEBREAK", "DB_COLUMN_ORDER_TIEBREAK") or "id").strip(),
        "tiebreak",
    )
    base_fee = _validate_ident(
        (_first_nonempty_env("LN_COLUMN_BASE_FEE_MSAT", "DB_COLUMN_BASE_FEE_MSAT") or "rp_base_fee_msat").strip(),
        "base fee col",
    )

    rel = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(table))

    with get_connection() as conn:
        with conn.cursor() as cur:
            rows = _q(
                cur,
                """
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (schema, table),
            )

    print(f"=== {schema}.{table} 列（型）===\n")
    for name, dt, udt in rows:
        print(f"  {name:32} {dt} ({udt})")

    with get_connection() as conn:
        with conn.cursor() as cur:
            print("\n=== 行数・ユニーク chan_id（全行・履歴混在）===\n")
            q1 = sql.SQL(
                "SELECT COUNT(*)::bigint, COUNT(DISTINCT {})::bigint FROM {}"
            ).format(sql.Identifier(chan_k), rel)
            r = _q(cur, q1)[0]
            print(f"  全行数: {r[0]}, ユニーク {chan_k}: {r[1]}")

            fee_cols = [
                base_fee,
                "rp_feerate_ppm",
                "rp_inbound_base_fee_msat",
                "rp_inbound_feerate_ppm",
                order_t,
                "rp_last_update",
            ]
            print("\n=== 手数料・時刻列 min/max/avg（全行、NULL 除外）===\n")
            for c in fee_cols:
                col = _validate_ident(c, "col")
                qm = sql.SQL(
                    "SELECT MIN({c}), MAX({c}), AVG({c})::float8 FROM {rel} WHERE {c} IS NOT NULL"
                ).format(c=sql.Identifier(col), rel=rel)
                r2 = _q(cur, qm)[0]
                print(f"  {col}: min={r2[0]} max={r2[1]} avg={r2[2]}")

            print(
                f"\n=== チャネルごと最新1行のみ（DISTINCT ON {chan_k}, {order_t} desc, {tie} desc）"
                f" — {base_fee} ===\n"
            )
            q_latest = sql.SQL(
                """
                SELECT MIN(t.v), MAX(t.v), AVG(t.v)::float8, COUNT(*)::bigint
                FROM (
                  SELECT DISTINCT ON ({chan})
                    {bf} AS v
                  FROM {rel}
                  WHERE {bf} IS NOT NULL
                  ORDER BY {chan}, {ot} DESC NULLS LAST, {tb} DESC NULLS LAST
                ) AS t
                """
            ).format(
                chan=sql.Identifier(chan_k),
                bf=sql.Identifier(base_fee),
                rel=rel,
                ot=sql.Identifier(order_t),
                tb=sql.Identifier(tie),
            )
            r3 = _q(cur, q_latest)[0]
            print(f"  最新のみ: min={r3[0]} max={r3[1]} avg={r3[2]} n={r3[3]}")


if __name__ == "__main__":
    main()
