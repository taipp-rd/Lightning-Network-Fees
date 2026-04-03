import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import connection as PGConnection

# カレントディレクトリに依存せず、リポジトリ直下の .env を読む（python -c 等でも有効）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


def _first_nonempty_env(*keys: str) -> str | None:
    """与えたキーのうち、最初に非空の値を持つものを返す。"""
    for key in keys:
        value = os.getenv(key)
        if value is not None and value.strip() != "":
            return value
    return None


def _require_any(*keys: str) -> str:
    """複数候補のうちいずれかひとつが必須（例: DB_HOST または LN_DB_HOST）。"""
    value = _first_nonempty_env(*keys)
    if value is None:
        listed = " / ".join(keys)
        raise RuntimeError(
            f"DB接続用の環境変数が未設定です。.env に次のいずれかを入れてください: {listed}"
        )
    return value


def get_connection() -> PGConnection:
    """PostgreSQL への接続を返す。呼び出し側で with または close を行うこと。"""
    port_raw = _first_nonempty_env("DB_PORT", "LN_DB_PORT")
    if port_raw is None:
        port = 5432
    else:
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise RuntimeError(
                f"DB_PORT / LN_DB_PORT は整数である必要があります: {port_raw!r}"
            ) from exc

    return psycopg2.connect(
        host=_require_any("DB_HOST", "LN_DB_HOST"),
        port=port,
        dbname=_require_any("DB_NAME", "LN_DB_NAME"),
        user=_require_any("DB_USER", "LN_DB_USER"),
        password=_require_any("DB_PASSWORD", "LN_DB_PASSWORD"),
    )
