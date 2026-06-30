from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"
LOG_DIR = ROOT_DIR / "logs"
DB_PATH = DATA_DIR / "radar.sqlite"
CSV_PATH = DATA_DIR / "latest_results.csv"


class ConfigError(RuntimeError):
    """Raised when .env is absent, incomplete, or invalid."""


def _value(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ConfigError(f".env 缺少配置项：{name}")
    return value.strip()


def _float(name: str, default: str | None = None) -> float:
    raw = _value(name, default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f".env 配置项 {name} 必须是数字，当前值：{raw!r}") from exc


def _int(name: str, default: str | None = None) -> int:
    raw = _value(name, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f".env 配置项 {name} 必须是整数，当前值：{raw!r}") from exc


def _bool(name: str, default: str = "false") -> bool:
    raw = _value(name, default).lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _keywords(name: str) -> tuple[str, ...]:
    raw = _value(name, "")
    return tuple(part.strip().lower() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    api_token: str
    api_base_url: str
    steam_wallet_discount: float
    steam_bid_increment_cny: float
    buff_fee_rate: float
    min_net_profit_rate: float
    initial_sample_size: int
    request_interval_seconds: float
    scan_interval_seconds: int
    dashboard_refresh_seconds: int
    dashboard_host: str
    dashboard_port: int
    dashboard_open_browser: bool
    steam_listing_url_template: str
    buff_goods_url_template: str
    excluded_keywords_cn: tuple[str, ...]
    excluded_keywords_en: tuple[str, ...]


def load_settings(require_token: bool = True) -> Settings:
    if not ENV_PATH.exists():
        raise ConfigError("未找到 .env。请先双击 setup_windows.bat。")

    load_dotenv(ENV_PATH, override=True)
    api_token = _value("CSQAQ_API_TOKEN", "")
    if require_token and (not api_token or api_token.startswith("PASTE_")):
        raise ConfigError(
            "请打开 .env，把 CSQAQ_API_TOKEN= 后面的占位文字替换为 CSQAQ 官网的真实 ApiToken。"
        )

    settings = Settings(
        api_token=api_token,
        api_base_url=_value("CSQAQ_API_BASE_URL", "https://api.csqaq.com/api/v1").rstrip("/"),
        steam_wallet_discount=_float("STEAM_WALLET_DISCOUNT", "0.65"),
        steam_bid_increment_cny=_float("STEAM_BID_INCREMENT_CNY", "0.10"),
        buff_fee_rate=_float("BUFF_FEE_RATE", "0.015"),
        min_net_profit_rate=_float("MIN_NET_PROFIT_RATE", "0.10"),
        initial_sample_size=_int("INITIAL_SAMPLE_SIZE", "50"),
        request_interval_seconds=_float("REQUEST_INTERVAL_SECONDS", "1.05"),
        scan_interval_seconds=_int("SCAN_INTERVAL_SECONDS", "900"),
        dashboard_refresh_seconds=_int("DASHBOARD_REFRESH_SECONDS", "30"),
        dashboard_host=_value("DASHBOARD_HOST", "127.0.0.1"),
        dashboard_port=_int("DASHBOARD_PORT", "5000"),
        dashboard_open_browser=_bool("DASHBOARD_OPEN_BROWSER", "true"),
        steam_listing_url_template=_value(
            "STEAM_LISTING_URL_TEMPLATE",
            "https://steamcommunity.com/market/listings/730/{market_hash_name}",
        ),
        buff_goods_url_template=_value(
            "BUFF_GOODS_URL_TEMPLATE",
            "https://buff.163.com/goods/{buff_id}?from=market",
        ),
        excluded_keywords_cn=_keywords("EXCLUDED_KEYWORDS_CN"),
        excluded_keywords_en=_keywords("EXCLUDED_KEYWORDS_EN"),
    )
    _validate(settings)
    return settings


def _validate(settings: Settings) -> None:
    if not 0 < settings.steam_wallet_discount <= 1:
        raise ConfigError("STEAM_WALLET_DISCOUNT 必须大于 0 且不大于 1，例如 0.65。")
    if settings.steam_bid_increment_cny < 0:
        raise ConfigError("STEAM_BID_INCREMENT_CNY 不能小于 0。")
    if not 0 <= settings.buff_fee_rate < 1:
        raise ConfigError("BUFF_FEE_RATE 必须在 0 到 1 之间，例如 0.015。")
    if settings.min_net_profit_rate < 0:
        raise ConfigError("MIN_NET_PROFIT_RATE 不能小于 0。")
    if not 1 <= settings.initial_sample_size <= 500:
        raise ConfigError("INITIAL_SAMPLE_SIZE 必须在 1 到 500 之间。第一版建议 50。")
    if settings.request_interval_seconds < 1.0:
        raise ConfigError("REQUEST_INTERVAL_SECONDS 不得小于 1.0，以遵守 CSQAQ 单 IP 1 次/秒限制。")
    if settings.scan_interval_seconds < 60:
        raise ConfigError("SCAN_INTERVAL_SECONDS 不得小于 60 秒。")
    if not 1 <= settings.dashboard_port <= 65535:
        raise ConfigError("DASHBOARD_PORT 必须在 1 到 65535 之间。")


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
