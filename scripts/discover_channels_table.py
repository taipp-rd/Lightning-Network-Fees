"""
接続先 DB で base_fee_msat / snapshot_time を持つテーブルを検索し、
.env に設定する LN_DB_SCHEMA / LN_CHANNELS_TABLE の候補を表示する。
"""

from __future__ import annotations

import os
import sys
from typing import Any

# プロジェクトルートを import パスに追加（scripts/ から実行される想定）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_connection  # noqa: E402


def _print_fallback_hints() -> None:
    """snapshot_time または fee 系列を持つテーブルを表示する。"""
    sql_snap = """
        SELECT DISTINCT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'snapshot_time'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 1, 2
        LIMIT 30;
    """
    # psycopg2 は文字列中の % をプレースホルダと誤解するため、正規表現でフィルタする
    sql_fee = """
        SELECT DISTINCT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE column_name ~* 'fee'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 1, 2, 3
        LIMIT 40;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            snap_rows = _fetch_all(cur, sql_snap)
            fee_rows = _fetch_all(cur, sql_fee)

    print("--- snapshot_time 列を持つテーブル（最大30件）---")
    if not snap_rows:
        print("  （なし）")
    else:
        for s, t in snap_rows:
            print(f"  {s}.{t}")

    print("\n--- 列名に fee を含む列（最大40行）---")
    if not fee_rows:
        print("  （なし）")
    else:
        for s, t, c in fee_rows:
            print(f"  {s}.{t}  …  {c}")


def _fetch_all(cur: Any, query: str, params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
    """カーソルでクエリを実行し、全行を返す。"""
    cur.execute(query, params or ())
    return list(cur.fetchall())


def main() -> None:
    """base_fee_msat と snapshot_time の両方を持つテーブルを列挙する。"""
    sql_match = """
        SELECT t.table_schema, t.table_name
        FROM information_schema.tables t
        WHERE t.table_type = 'BASE TABLE'
          AND t.table_schema NOT IN ('pg_catalog', 'information_schema')
          AND EXISTS (
            SELECT 1 FROM information_schema.columns c1
            WHERE c1.table_schema = t.table_schema
              AND c1.table_name = t.table_name
              AND c1.column_name = 'base_fee_msat'
          )
          AND EXISTS (
            SELECT 1 FROM information_schema.columns c2
            WHERE c2.table_schema = t.table_schema
              AND c2.table_name = t.table_name
              AND c2.column_name = 'snapshot_time'
          )
        ORDER BY t.table_schema, t.table_name;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            rows = _fetch_all(cur, sql_match)

    if not rows:
        print(
            "base_fee_msat と snapshot_time の両方を持つテーブルが見つかりませんでした。\n"
            "列名が異なる可能性があります。参考として関連列を持つテーブルを列挙します。\n"
        )
        _print_fallback_hints()
        return

    print("次のテーブルがこのプロジェクトのクエリと互換です（schema.table）:\n")
    for schema, name in rows:
        print(f"  {schema}.{name}")

    schema, name = rows[0]
    print("\n.env に例（1件目を採用する場合）:\n")
    print(f"  LN_DB_SCHEMA={schema}")
    print(f"  LN_CHANNELS_TABLE={name}")
    if len(rows) > 1:
        print("\n複数ある場合は、目的の Lightning チャネル用テーブルを選んでください。")


if __name__ == "__main__":
    main()
