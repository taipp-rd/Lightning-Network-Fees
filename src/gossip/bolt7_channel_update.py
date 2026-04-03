"""
BOLT #7 `channel_update` ゴシップメッセージと、典型的な `channel_update` テーブル列の対応。

ゴシップで交換される主な情報（手数料まわり）::

    - chain_hash, short_channel_id … チャネルの識別（DB では `chan_id` 等に格納されることが多い）
    - timestamp … メッセージの時刻（Unix 秒。DB の `timestamp` / `rp_last_update` のどちらがソースかはスキーマ依存）
    - fee_base_msat … ベース手数料（ミリサトシ）。DB では `rp_base_fee_msat` など
    - fee_proportional_millionths … ppm。DB では `rp_feerate_ppm` など
    - インバウンド系の手数料 … 実装により `rp_inbound_*` 列に入る

**型**: PostgreSQL では多く `bigint` / `integer`。アプリ側では `int` として扱い、ヒストグラムでは `float` にキャストしてビン分割する。

**「最新のゴシップだけ使う」**: 同一 `chan_id` に複数行あるとき、
`ORDER BY chan_id, <時刻列> DESC, <単調増加の列 e.g. id> DESC` として
`DISTINCT ON (chan_id)` するのが、行ごとに時刻が異なるテーブルでは一般的。
"""
