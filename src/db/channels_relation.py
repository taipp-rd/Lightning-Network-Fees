"""channels 相当テーブルの qualified 名（スキーマ・テーブルは環境変数で上書き可）。"""

import re

from psycopg2 import sql

from src.db.connection import _first_nonempty_env


def _validate_ident(name: str, label: str) -> str:
    """PostgreSQL の単純識別子として安全な名前のみ許可する。"""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise RuntimeError(
            f"{label} は英数字とアンダースコアのみ（先頭は英字または_）としてください: {name!r}"
        )
    return name


def channels_qualified() -> sql.Composed:
    """
    FROM / サブクエリ用の schema.table を返す。

    環境変数（いずれか先勝ち）:
    - DB_SCHEMA / LN_DB_SCHEMA … 既定 public
    - CHANNELS_TABLE / LN_CHANNELS_TABLE … 既定 channels
    """
    schema_raw = _first_nonempty_env("DB_SCHEMA", "LN_DB_SCHEMA") or "public"
    table_raw = _first_nonempty_env("CHANNELS_TABLE", "LN_CHANNELS_TABLE") or "channels"
    schema = _validate_ident(schema_raw.strip(), "DB_SCHEMA / LN_DB_SCHEMA")
    table = _validate_ident(table_raw.strip(), "CHANNELS_TABLE / LN_CHANNELS_TABLE")
    return sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(table))
