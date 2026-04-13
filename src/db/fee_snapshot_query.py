"""手数料など1列を SELECT する SQL を組み立てる（クエリ方式は環境変数で切替）。"""

from __future__ import annotations

from datetime import datetime

from psycopg2 import sql

from src.db.channels_relation import _validate_ident, channels_qualified
from src.db.connection import _first_nonempty_env

# クエリにバインドする期間の両端（含む）。None のときは従来どおり「全体の最新」のみ。
QueryTimeRange = tuple[datetime, datetime] | None


def _time_range_bind_values(bounds: tuple[datetime, datetime]) -> tuple[object, object]:
    """
    期間指定のプレースホルダに渡す値を、DB 列の型に合わせて変換する。

    LN_QUERY_TIME_STORAGE / DB_QUERY_TIME_STORAGE（既定: timestamptz 相当）で指定する。

    - timestamptz: ``datetime`` をそのまま渡す（PostgreSQL が timestamp with time zone 等へ解釈）
    - unix_sec: UTC 基準の Unix 秒（整数）
    - unix_ms: UTC 基準の Unix ミリ秒（整数）

    naive な ``datetime`` を epoch に変換するときは、Python の ``timestamp()`` どおり
    「ローカル時刻として解釈」される点に注意。
    """
    raw = (
        _first_nonempty_env("DB_QUERY_TIME_STORAGE", "LN_QUERY_TIME_STORAGE")
        or "timestamptz"
    ).strip().lower()
    aliases: dict[str, str] = {
        "timestamptz": "timestamptz",
        "timestamp": "timestamptz",
        "datetime": "timestamptz",
        "unix_sec": "unix_sec",
        "epoch_sec": "unix_sec",
        "epoch_seconds": "unix_sec",
        "seconds": "unix_sec",
        "int_sec": "unix_sec",
        "unix_ms": "unix_ms",
        "epoch_ms": "unix_ms",
        "epoch_millis": "unix_ms",
        "milliseconds": "unix_ms",
        "int_ms": "unix_ms",
    }
    mode = aliases.get(raw, raw)
    t0, t1 = bounds
    if mode == "timestamptz":
        return (t0, t1)
    if mode == "unix_sec":
        return (int(t0.timestamp()), int(t1.timestamp()))
    if mode == "unix_ms":
        return (int(t0.timestamp() * 1000), int(t1.timestamp() * 1000))
    raise RuntimeError(
        f"不明な LN_QUERY_TIME_STORAGE / DB_QUERY_TIME_STORAGE: {raw!r}。"
        " timestamptz / unix_sec / unix_ms のいずれかを指定してください。"
    )


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


def describe_time_filter_clause(time_range: QueryTimeRange, mode: str) -> str:
    """ログ用: 期間指定が有効なときの説明文を返す。"""
    if time_range is None:
        return ""
    t0, t1 = time_range
    span = f"[{t0.isoformat()}, {t1.isoformat()}]（両端含む）"
    if mode == "snapshot_batch":
        return f" + 期間指定: スナップショット列が {span} に入る行だけを対象に、その中の最大スナップショット時刻のバッチ"
    if mode == "latest_per_channel":
        return f" + 期間指定: ORDER 時刻列が {span} の行に限定してからチャネルごと最新1行"
    return f" + 期間指定: {span}"


def latest_snapshot_select_sql(
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
    *,
    time_range: QueryTimeRange = None,
) -> tuple[sql.Composed, tuple[object, ...]]:
    """
    スナップショットバッチ想定::

        WHERE <snap> = (SELECT MAX(<snap>) FROM <rel>)

    全行が同じスナップショット時刻を共有するテーブル向け。

    time_range を指定した場合は、サブクエリ側を
    ``MAX(<snap>) WHERE <snap> BETWEEN パラメータ`` にし、期間内で最も新しいバッチのみを採用する。
    """
    rel = channels_qualified()
    snap_raw = _first_nonempty_env("DB_COLUMN_SNAPSHOT", "LN_COLUMN_SNAPSHOT") or "snapshot_time"
    snap = _validate_ident(snap_raw.strip(), "DB_COLUMN_SNAPSHOT / LN_COLUMN_SNAPSHOT")

    val_raw = _first_nonempty_env(*value_column_env_keys) or default_value_column
    val = _validate_ident(val_raw.strip(), " / ".join(value_column_env_keys))

    if time_range is None:
        composed = sql.SQL(
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
        return composed, ()

    composed = sql.SQL(
        """
SELECT {}
FROM {}
WHERE {} = (
    SELECT MAX({}) FROM {} WHERE {} >= {} AND {} <= {}
  )
  AND {} IS NOT NULL
"""
    ).format(
        sql.Identifier(val),
        rel,
        sql.Identifier(snap),
        sql.Identifier(snap),
        rel,
        sql.Identifier(snap),
        sql.Placeholder(),
        sql.Identifier(snap),
        sql.Placeholder(),
        sql.Identifier(val),
    )
    return composed, _time_range_bind_values(time_range)


def latest_per_channel_select_sql(
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
    *,
    time_range: QueryTimeRange = None,
) -> tuple[sql.Composed, tuple[object, ...]]:
    """
    チャネル識別子ごとに、時刻が最新の1行だけを採用（PostgreSQL DISTINCT ON）::

        SELECT DISTINCT ON (<chan>) <val> FROM <rel>
        WHERE <val> IS NOT NULL
        ORDER BY <chan>, <order_col> DESC

    channel_update のように行ごとに timestamp が異なる場合に適する。
    タイブレーク列: DB_COLUMN_ORDER_TIEBREAK / LN_COLUMN_ORDER_TIEBREAK（既定 id）。

    time_range を指定した場合は、ORDER 時刻列がその範囲に入る行に限定してから DISTINCT ON する。
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

    if time_range is None:
        composed = sql.SQL(
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
        return composed, ()

    composed = sql.SQL(
        """
SELECT DISTINCT ON ({})
    {}
FROM {}
WHERE {} IS NOT NULL
  AND {} >= {} AND {} <= {}
ORDER BY {}, {} DESC NULLS LAST, {} DESC NULLS LAST
"""
    ).format(
        sql.Identifier(chan),
        sql.Identifier(val),
        rel,
        sql.Identifier(val),
        sql.Identifier(order_col),
        sql.Placeholder(),
        sql.Identifier(order_col),
        sql.Placeholder(),
        sql.Identifier(chan),
        sql.Identifier(order_col),
        sql.Identifier(tie_col),
    )
    return composed, _time_range_bind_values(time_range)


def fee_distribution_select_sql(
    value_column_env_keys: tuple[str, ...],
    default_value_column: str,
    *,
    time_range: QueryTimeRange = None,
) -> tuple[sql.Composed, tuple[object, ...], str]:
    """
    FEE_QUERY_MODE / LN_FEE_QUERY_MODE で方式を選ぶ。

    - snapshot_batch（既定）: 全行が同じスナップショット列のバッチを共有する前提
    - latest_per_channel: チャネルごとに最新行だけ（DISTINCT ON）

    戻り値: (SQL, バインドパラメータのタプル, 人間向けモード説明)
    """
    mode_raw = _first_nonempty_env("FEE_QUERY_MODE", "LN_FEE_QUERY_MODE") or "snapshot_batch"
    mode = _normalize_fee_query_mode(mode_raw)

    if mode == "snapshot_batch":
        q, params = latest_snapshot_select_sql(
            value_column_env_keys,
            default_value_column,
            time_range=time_range,
        )
        desc = (
            "snapshot_batch（スナップショット列 = 全体の MAX。バッチ同期型テーブル向け）"
            + describe_time_filter_clause(time_range, mode)
        )
        return q, params, desc
    if mode == "latest_per_channel":
        q, params = latest_per_channel_select_sql(
            value_column_env_keys,
            default_value_column,
            time_range=time_range,
        )
        desc = (
            "latest_per_channel（チャネルIDごとに ORDER 列が最新の1行。channel_update 向け）"
            + describe_time_filter_clause(time_range, mode)
        )
        return q, params, desc

    raise RuntimeError(
        f"不明な FEE_QUERY_MODE: {mode_raw!r}。"
        f" snapshot_batch または latest_per_channel を指定してください。"
    )


def latest_snapshot_select_sql_pair(
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
    *,
    time_range: QueryTimeRange = None,
) -> tuple[sql.Composed, tuple[object, ...]]:
    """
    スナップショットバッチ想定で、2列を同一行から取得する。

    両列とも IS NOT NULL の行のみ返す。

    time_range の意味は ``latest_snapshot_select_sql`` と同じ。
    """
    rel = channels_qualified()
    snap_raw = _first_nonempty_env("DB_COLUMN_SNAPSHOT", "LN_COLUMN_SNAPSHOT") or "snapshot_time"
    snap = _validate_ident(snap_raw.strip(), "DB_COLUMN_SNAPSHOT / LN_COLUMN_SNAPSHOT")

    val_a_raw = _first_nonempty_env(*value_column_env_keys_a) or default_value_column_a
    val_a = _validate_ident(val_a_raw.strip(), " / ".join(value_column_env_keys_a))

    val_b_raw = _first_nonempty_env(*value_column_env_keys_b) or default_value_column_b
    val_b = _validate_ident(val_b_raw.strip(), " / ".join(value_column_env_keys_b))

    if time_range is None:
        composed = sql.SQL(
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
        return composed, ()

    composed = sql.SQL(
        """
SELECT {}, {}
FROM {}
WHERE {} = (
    SELECT MAX({}) FROM {} WHERE {} >= {} AND {} <= {}
  )
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
        sql.Identifier(snap),
        sql.Placeholder(),
        sql.Identifier(snap),
        sql.Placeholder(),
        sql.Identifier(val_a),
        sql.Identifier(val_b),
    )
    return composed, _time_range_bind_values(time_range)


def latest_per_channel_select_sql_pair(
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
    *,
    time_range: QueryTimeRange = None,
) -> tuple[sql.Composed, tuple[object, ...]]:
    """
    チャネル識別子ごとに最新行の2列を取得（DISTINCT ON）。

    両列とも IS NOT NULL の行のみ返す。

    time_range の意味は ``latest_per_channel_select_sql`` と同じ。
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

    if time_range is None:
        composed = sql.SQL(
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
        return composed, ()

    composed = sql.SQL(
        """
SELECT DISTINCT ON ({})
    {}, {}
FROM {}
WHERE {} IS NOT NULL
  AND {} IS NOT NULL
  AND {} >= {} AND {} <= {}
ORDER BY {}, {} DESC NULLS LAST, {} DESC NULLS LAST
"""
    ).format(
        sql.Identifier(chan),
        sql.Identifier(val_a),
        sql.Identifier(val_b),
        rel,
        sql.Identifier(val_a),
        sql.Identifier(val_b),
        sql.Identifier(order_col),
        sql.Placeholder(),
        sql.Identifier(order_col),
        sql.Placeholder(),
        sql.Identifier(chan),
        sql.Identifier(order_col),
        sql.Identifier(tie_col),
    )
    return composed, _time_range_bind_values(time_range)


def fee_pair_distribution_select_sql(
    value_column_env_keys_a: tuple[str, ...],
    default_value_column_a: str,
    value_column_env_keys_b: tuple[str, ...],
    default_value_column_b: str,
    *,
    time_range: QueryTimeRange = None,
) -> tuple[sql.Composed, tuple[object, ...], str]:
    """
    base_fee と fee_rate など、2列を同じ FEE_QUERY_MODE で取得する。

    戻り値: (SQL, バインドパラメータのタプル, 人間向けモード説明)
    """
    mode_raw = _first_nonempty_env("FEE_QUERY_MODE", "LN_FEE_QUERY_MODE") or "snapshot_batch"
    mode = _normalize_fee_query_mode(mode_raw)

    if mode == "snapshot_batch":
        q, params = latest_snapshot_select_sql_pair(
            value_column_env_keys_a,
            default_value_column_a,
            value_column_env_keys_b,
            default_value_column_b,
            time_range=time_range,
        )
        desc = (
            "snapshot_batch（スナップショット列 = 全体の MAX。バッチ同期型テーブル向け）"
            + describe_time_filter_clause(time_range, mode)
        )
        return q, params, desc
    if mode == "latest_per_channel":
        q, params = latest_per_channel_select_sql_pair(
            value_column_env_keys_a,
            default_value_column_a,
            value_column_env_keys_b,
            default_value_column_b,
            time_range=time_range,
        )
        desc = (
            "latest_per_channel（チャネルIDごとに ORDER 列が最新の1行。channel_update 向け）"
            + describe_time_filter_clause(time_range, mode)
        )
        return q, params, desc

    raise RuntimeError(
        f"不明な FEE_QUERY_MODE: {mode_raw!r}。"
        f" snapshot_batch または latest_per_channel を指定してください。"
    )
