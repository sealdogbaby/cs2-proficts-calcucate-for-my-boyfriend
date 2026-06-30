from __future__ import annotations

from urllib.parse import quote

from config import Settings


def build_steam_url(market_hash_name: str, settings: Settings) -> str:
    if not market_hash_name or not market_hash_name.strip():
        raise ValueError("market_hash_name 为空，无法生成 Steam 链接。")
    encoded = quote(market_hash_name.strip(), safe="")
    return settings.steam_listing_url_template.format(market_hash_name=encoded)


def build_buff_url(buff_id: int | str, settings: Settings) -> str:
    if buff_id is None or str(buff_id).strip() in {"", "0", "None"}:
        raise ValueError("buff_id 为空，无法生成 BUFF 链接。")
    return settings.buff_goods_url_template.format(buff_id=str(buff_id).strip())
