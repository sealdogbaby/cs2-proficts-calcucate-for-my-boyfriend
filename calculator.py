from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from config import Settings

CENTS = Decimal("0.01")


def _money(value: object, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} 不是有效数字：{value!r}") from exc
    if amount <= 0:
        raise ValueError(f"{field_name} 必须大于 0，当前值：{amount}")
    return amount


def calculate_profit(steam_buy_price: object, buff_sell_price: object, settings: Settings) -> dict[str, Decimal]:
    steam_buy = _money(steam_buy_price, "Steam 最高求购价")
    buff_sell = _money(buff_sell_price, "BUFF 最低在售价")

    steam_cost = (steam_buy + Decimal(str(settings.steam_bid_increment_cny))) * Decimal(
        str(settings.steam_wallet_discount)
    )
    buff_net = buff_sell * (Decimal("1") - Decimal(str(settings.buff_fee_rate)))
    net_profit = buff_net - steam_cost
    net_profit_rate = net_profit / steam_cost

    return {
        "steam_actual_cost": steam_cost.quantize(CENTS, rounding=ROUND_HALF_UP),
        "buff_net_proceeds": buff_net.quantize(CENTS, rounding=ROUND_HALF_UP),
        "net_profit": net_profit.quantize(CENTS, rounding=ROUND_HALF_UP),
        "net_profit_rate": net_profit_rate,
    }
