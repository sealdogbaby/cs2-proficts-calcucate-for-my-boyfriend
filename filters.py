from __future__ import annotations

from config import Settings


def excluded_reason(name_cn: str | None, market_hash_name: str | None, settings: Settings) -> str | None:
    cn = (name_cn or "").lower()
    en = (market_hash_name or "").lower()

    for keyword in settings.excluded_keywords_cn:
        if keyword and keyword in cn:
            return f"命中中文过滤关键词：{keyword}"
    for keyword in settings.excluded_keywords_en:
        if keyword and keyword in en:
            return f"命中英文过滤关键词：{keyword}"
    return None
