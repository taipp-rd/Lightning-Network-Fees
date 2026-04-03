"""手数料など1列を SELECT する SQL を組み立てる（クエリ方式は環境変数で切替）。"""

from psycopg2 import sql

from src.db.channels_relation import _validate_ident, channels_qualified
from src.db.connection import _first_nonempty_env


def _normalize_fee_query_mode(raw: str) -> str:
    """FEE_QUERY_MODE の別名を正規化する。"""
    m = raw.strip().lower()
    aliases = {
        "snapshot": "snapshot_batch",
        "batch": "snapshot_batch",
        "global_max_timestamp": "snapshot_batch",
        "per_channel": "latest_per_channel",
        "distinct_chan": "latest_per_channel",
        "channel_update": "latest_per_channel",
    }
    return aliases.get(m, m)


def latest_snapshot_select_sql(
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
) -> sql.Composed:
    """
    スナップショットバッチ想定::

        WHERE <snap> = (SELECT MAX(<snap>) FROM <rel>)

    全行が同じスナップショット時刻を共有するテーブル向け。
    """
    rel = channels_qualified()
    snap_raw = _first_nonempty_env("DB_COLUMN_SNAPSHOT", "LN_COLUMN_SNAPSHOT") or "snapshot_time"
    snap = _validate_ident(snap_raw.strip(), "DB_COLUMN_SNAPSHOT / LN_COLUMN_SNAPSHOT")

    val_raw = _first_nonempty_env(*value_column_env_keys) or default_value_column
    val = _validate_ident(val_raw.strip(), " / ".join(value_column_env_keys))

    return sql.SQL(
        """
SELECT {}
FROM {}
WHERE {} = (SELECT MAX({}) FROM {})
  AND {} IS NOT NULL
"""
    ).format(
        sql.Identifier(val),
        rel,
        sql.Identifier(snap),
        sql.Identifier(snap),
        rel,
        sql.Identifier(val),
    )


def latest_per_channel_select_sql(
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
) -> sql.Composed:
    """
    チャネル識別子ごとに、時刻が最新の1行だけを採用（PostgreSQL DISTINCT ON）::

        SELECT DISTINCT ON (<chan>) <val> FROM <rel>
        WHERE <val> IS NOT NULL
        ORDER BY <chan>, <order_col> DESC

    channel_update のように行ごとに timestamp が異なる場合に適する。
    タイブレーク列: DB_COLUMN_ORDER_TIEBREAK / LN_COLUMN_ORDER_TIEBREAK（既定 id）。
    """
    rel = channels_qualified()
    chan_raw = _first_nonempty_env("DB_COLUMN_CHANNEL_KEY", "LN_COLUMN_CHANNEL_KEY") or "chan_id"
    chan = _validate_ident(chan_raw.strip(), "DB_COLUMN_CHANNEL_KEY / LN_COLUMN_CHANNEL_KEY")

    order_raw = (
        _first_nonempty_env("DB_COLUMN_ORDER_TIME", "LN_COLUMN_ORDER_TIME")
        or _first_nonempty_env("DB_COLUMN_SNAPSHOT", "LN_COLUMN_SNAPSHOT")
        or "timestamp"
    )
    order_col = _validate_ident(order_raw.strip(), "DB_COLUMN_ORDER_TIME / LN_COLUMN_SNAPSHOT")

    # 同一 chan_id・同一 timestamp のタイを避ける（例: 主キー id の大きい方を最新とみなす）
    tie_raw = _first_nonempty_env("DB_COLUMN_ORDER_TIEBREAK", "LN_COLUMN_ORDER_TIEBREAK") or "id"
    tie_col = _validate_ident(tie_raw.strip(), "DB_COLUMN_ORDER_TIEBREAK / LN_COLUMN_ORDER_TIEBREAK")

    val_raw = _first_nonempty_env(*value_column_env_keys) or default_value_column
    val = _validate_ident(val_raw.strip(), " / ".join(value_column_env_keys))

    return sql.SQL(
        """
SELECT DISTINCT ON ({})
    {}
FROM {}
WHERE {} IS NOT NULL
ORDER BY {}, {} DESC NULLS LAST, {} DESC NULLS LAST
"""
    ).format(
        sql.Identifier(chan),
        sql.Identifier(val),
        rel,
        sql.Identifier(val),
        sql.Identifier(chan),
        sql.Identifier(order_col),
        sql.Identifier(tie_col),
    )


def fee_distribution_select_sql(
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
) -> tuple[sql.Composed, str]:
    """
    FEE_QUERY_MODE / LN_FEE_QUERY_MODE で方式を選ぶ。

    - snapshot_batch（既定）: 全行が同じスナップショット列のバッチを共有する前提
    - latest_per_channel: チャネルごとに最新行だけ（DISTINCT ON）

    戻り値: (SQL, 人間向けモード説明)
    """
    mode_raw = _first_nonempty_env("FEE_QUERY_MODE", "LN_FEE_QUERY_MODE") or "snapshot_batch"
    mode = _normalize_fee_query_mode(mode_raw)

    if mode == "snapshot_batch":
        q = latest_snapshot_select_sql(value_column_env_keys, default_value_column)
        return (
            q,
            "snapshot_batch（スナップショット列 = 全体の MAX。バッチ同期型テーブル向け）",
        )
    if mode == "latest_per_channel":
        q = latest_per_channel_select_sql(value_column_env_keys, default_value_column)
        return (
            q,
            "latest_per_channel（チャネルIDごとに ORDER 列が最新の1行。channel_update 向け）",
        )

    raise RuntimeError(
        f"不明な FEE_QUERY_MODE: {mode_raw!r}。"
        f" snapshot_batch または latest_per_channel を指定してください。"
    )


def latest_snapshot_select_sql_pair(
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
) -> sql.Composed:
    """
    スナップショットバッチ想定で、2列を同一行から取得する。

    両列とも IS NOT NULL の行のみ返す。
    """
    rel = channels_qualified()
    snap_raw = _first_nonempty_env("DB_COLUMN_SNAPSHOT", "LN_COLUMN_SNAPSHOT") or "snapshot_time"
    snap = _validate_ident(snap_raw.strip(), "DB_COLUMN_SNAPSHOT / LN_COLUMN_SNAPSHOT")

    val_a_raw = _first_nonempty_env(*value_column_env_keys_a) or default_value_column_a
    val_a = _validate_ident(val_a_raw.strip(), " / ".join(value_column_env_keys_a))

    val_b_raw = _first_nonempty_env(*value_column_env_keys_b) or default_value_column_b
    val_b = _validate_ident(val_b_raw.strip(), " / ".join(value_column_env_keys_b))

    return sql.SQL(
        """
SELECT {}, {}
FROM {}
WHERE {} = (SELECT MAX({}) FROM {})
  AND {} IS NOT NULL
  AND {} IS NOT NULL
"""
    ).format(
        sql.Identifier(val_a),
        sql.Identifier(val_b),
        rel,
        sql.Identifier(snap),
        sql.Identifier(snap),
        rel,
        sql.Identifier(val_a),
        sql.Identifier(val_b),
    )


def latest_per_channel_select_sql_pair(
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
) -> sql.Composed:
    """
    チャネル識別子ごとに最新行の2列を取得（DISTINCT ON）。

    両列とも IS NOT NULL の行のみ返す。
    """
    rel = channels_qualified()
    chan_raw = _first_nonempty_env("DB_COLUMN_CHANNEL_KEY", "LN_COLUMN_CHANNEL_KEY") or "chan_id"
    chan = _validate_ident(chan_raw.strip(), "DB_COLUMN_CHANNEL_KEY / LN_COLUMN_CHANNEL_KEY")

    order_raw = (
        _first_nonempty_env("DB_COLUMN_ORDER_TIME", "LN_COLUMN_ORDER_TIME")
        or _first_nonempty_env("DB_COLUMN_SNAPSHOT", "LN_COLUMN_SNAPSHOT")
        or "timestamp"
    )
    order_col = _validate_ident(order_raw.strip(), "DB_COLUMN_ORDER_TIME / LN_COLUMN_SNAPSHOT")

    tie_raw = _first_nonempty_env("DB_COLUMN_ORDER_TIEBREAK", "LN_COLUMN_ORDER_TIEBREAK") or "id"
    tie_col = _validate_ident(tie_raw.strip(), "DB_COLUMN_ORDER_TIEBREAK / LN_COLUMN_ORDER_TIEBREAK")

    val_a_raw = _first_nonempty_env(*value_column_env_keys_a) or default_value_column_a
    val_a = _validate_ident(val_a_raw.strip(), " / ".join(value_column_env_keys_a))

    val_b_raw = _first_nonempty_env(*value_column_env_keys_b) or default_value_column_b
    val_b = _validate_ident(val_b_raw.strip(), " / ".join(value_column_env_keys_b))

    return sql.SQL(
        """
SELECT DISTINCT ON ({})
    {}, {}
FROM {}
WHERE {} IS NOT NULL
  AND {} IS NOT NULL
ORDER BY {}, {} DESC NULLS LAST, {} DESC NULLS LAST
"""
    ).format(
        sql.Identifier(chan),
        sql.Identifier(val_a),
        sql.Identifier(val_b),
        rel,
        sql.Identifier(val_a),
        sql.Identifier(val_b),
        sql.Identifier(chan),
        sql.Identifier(order_col),
        sql.Identifier(tie_col),
    )


def fee_pair_distribution_select_sql(
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
) -> tuple[sql.Composed, str]:
    """
    base_fee と fee_rate など、2列を同じ FEE_QUERY_MODE で取得する。

    戻り値: (SQL, 人間向けモード説明)
    """
    mode_raw = _first_nonempty_env("FEE_QUERY_MODE", "LN_FEE_QUERY_MODE") or "snapshot_batch"
    mode = _normalize_fee_query_mode(mode_raw)

    if mode == "snapshot_batch":
        q = latest_snapshot_select_sql_pair(
            value_column_env_keys_a,
            default_value_column_a,
            value_column_env_keys_b,
            default_value_column_b,
        )
        return (
            q,
            "snapshot_batch（スナップショット列 = 全体の MAX。バッチ同期型テーブル向け）",
        )
    if mode == "latest_per_channel":
        q = latest_per_channel_select_sql_pair(
            value_column_env_keys_a,
            default_value_column_a,
            value_column_env_keys_b,
            default_value_column_b,
        )
        return (
            q,
            "latest_per_channel（チャネルIDごとに ORDER 列が最新の1行。channel_update 向け）",
        )

    raise RuntimeError(
        f"不明な FEE_QUERY_MODE: {mode_raw!r}。"
        f" snapshot_batch または latest_per_channel を指定してください。"
    )
