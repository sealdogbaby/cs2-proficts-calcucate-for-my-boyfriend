from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from decimal import Decimal

from api_client import CsqaqApiError, CsqaqClient
from calculator import calculate_profit
from config import ConfigError, load_settings
from database import (
    create_scan_run,
    export_latest_opportunities_csv,
    finish_scan_run,
    get_active_catalog_items,
    initialize_database,
    insert_scan_results,
    update_catalog_details,
)
from filters import excluded_reason
from link_builder import build_buff_url, build_steam_url
from logging_utils import configure_logging


def _number(value: object, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 缺失或不是数字：{value!r}") from exc
    if number <= 0:
        raise ValueError(f"{field_name} 必须大于 0，当前值：{number}")
    return number


def _optional_int(value: object) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def scan_once(settings, logger) -> int:
    initialize_database()
    catalog = get_active_catalog_items()
    if not catalog:
        logger.error("本地测试目录为空。请先双击 init_catalog.bat。")
        return 2

    client = CsqaqClient(settings, logger)
    run_id = create_scan_run(len(catalog))
    logger.info("开始扫描 run_id=%s，饰品数量=%s。", run_id, len(catalog))

    success_count = 0
    skipped_count = 0
    error_count = 0
    opportunities = 0
    result_rows: list[dict[str, object]] = []

    for index, item in enumerate(catalog, start=1):
        good_id = int(item["good_id"])
        catalog_name = item["name_cn"]
        try:
            details = client.get_good(good_id)
            name_cn = str(details.get("name") or catalog_name)
            market_hash_name = str(details.get("market_hash_name") or "").strip()
            buff_id = details.get("buff_id")

            reason = excluded_reason(name_cn, market_hash_name, settings)
            if reason:
                skipped_count += 1
                logger.info("[%s/%s] 跳过 %s：%s", index, len(catalog), name_cn, reason)
                continue

            if not market_hash_name:
                raise ValueError("market_hash_name 为空")
            if buff_id is None or str(buff_id).strip() in {"", "0"}:
                raise ValueError("buff_id 为空")

            steam_buy_price = _number(details.get("steam_buy_price"), "Steam 最高求购价")
            steam_sell_price = _number(details.get("steam_sell_price"), "Steam 最低在售价")
            buff_buy_price = _number(details.get("buff_buy_price"), "BUFF 最高求购价")
            buff_sell_price = _number(details.get("buff_sell_price"), "BUFF 最低在售价")

            profit = calculate_profit(steam_buy_price, buff_sell_price, settings)
            steam_url = build_steam_url(market_hash_name, settings)
            buff_url = build_buff_url(buff_id, settings)
            is_opportunity = profit["net_profit_rate"] > Decimal(str(settings.min_net_profit_rate))

            row = {
                "good_id": good_id,
                "name_cn": name_cn,
                "market_hash_name": market_hash_name,
                "buff_id": buff_id,
                "steam_buy_price": steam_buy_price,
                "steam_sell_price": steam_sell_price,
                "steam_buy_num": _optional_int(details.get("steam_buy_num")),
                "steam_sell_num": _optional_int(details.get("steam_sell_num")),
                "buff_buy_price": buff_buy_price,
                "buff_sell_price": buff_sell_price,
                "buff_buy_num": _optional_int(details.get("buff_buy_num")),
                "buff_sell_num": _optional_int(details.get("buff_sell_num")),
                "steam_actual_cost": float(profit["steam_actual_cost"]),
                "buff_net_proceeds": float(profit["buff_net_proceeds"]),
                "net_profit": float(profit["net_profit"]),
                "net_profit_rate": float(profit["net_profit_rate"]),
                "steam_url": steam_url,
                "buff_url": buff_url,
                "source_updated_at": details.get("updated_at"),
                "is_opportunity": bool(is_opportunity),
            }
            result_rows.append(row)
            update_catalog_details(good_id, market_hash_name, buff_id)
            success_count += 1
            if is_opportunity:
                opportunities += 1
                logger.info(
                    "[%s/%s] 机会：%s，净利润率=%.2f%%。",
                    index,
                    len(catalog),
                    name_cn,
                    float(profit["net_profit_rate"]) * 100,
                )
            else:
                logger.info(
                    "[%s/%s] 完成：%s，净利润率=%.2f%%（未达门槛）。",
                    index,
                    len(catalog),
                    name_cn,
                    float(profit["net_profit_rate"]) * 100,
                )
        except CsqaqApiError as exc:
            error_count += 1
            logger.warning("[%s/%s] API 失败：%s；原因：%s", index, len(catalog), catalog_name, exc)
        except (ValueError, KeyError) as exc:
            skipped_count += 1
            logger.warning("[%s/%s] 数据跳过：%s；原因：%s", index, len(catalog), catalog_name, exc)
        except Exception as exc:  # Keep one bad row from stopping the full scan.
            error_count += 1
            logger.exception("[%s/%s] 未预期错误：%s；原因：%s", index, len(catalog), catalog_name, exc)

    if success_count == 0:
        status = "failed"
        message = "本轮没有任何有效成功数据；保留上一轮成功结果。"
        finish_scan_run(
            run_id,
            status=status,
            success_count=success_count,
            skipped_count=skipped_count,
            error_count=error_count,
            opportunity_count=opportunities,
            message=message,
        )
        logger.error("扫描失败：%s", message)
        return 3

    status = "success" if error_count == 0 else "partial"
    insert_scan_results(run_id, result_rows)
    finish_scan_run(
        run_id,
        status=status,
        success_count=success_count,
        skipped_count=skipped_count,
        error_count=error_count,
        opportunity_count=opportunities,
        message=None,
    )
    csv_count = export_latest_opportunities_csv()
    logger.info(
        "扫描结束：状态=%s，成功=%s，跳过=%s，错误=%s，利润>门槛=%s，已导出 %s 条到 data\\latest_results.csv。",
        status,
        success_count,
        skipped_count,
        error_count,
        opportunities,
        csv_count,
    )
    return 0


def run_loop(settings, logger) -> int:
    logger.info("循环扫描已启动；扫描周期=%s 秒。按 Ctrl+C 可安全停止。", settings.scan_interval_seconds)
    while True:
        started = time.monotonic()
        result = scan_once(settings, logger)
        elapsed = time.monotonic() - started
        wait_seconds = max(0, settings.scan_interval_seconds - elapsed)
        next_time = datetime.now().timestamp() + wait_seconds
        logger.info(
            "本轮返回码=%s；耗时=%.1f 秒；下一轮将在 %s 秒后开始（约 %s）。",
            result,
            elapsed,
            int(wait_seconds),
            datetime.fromtimestamp(next_time).strftime("%Y-%m-%d %H:%M:%S"),
        )
        time.sleep(wait_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="CS2 Steam × BUFF 价差雷达扫描器")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="只扫描一次")
    group.add_argument("--loop", action="store_true", help="按 .env 周期持续扫描")
    args = parser.parse_args()

    logger = configure_logging()
    try:
        settings = load_settings(require_token=True)
        if args.once:
            return scan_once(settings, logger)
        return run_loop(settings, logger)
    except ConfigError as exc:
        logger.error(str(exc))
        return 2
    except KeyboardInterrupt:
        logger.warning("扫描器已由用户停止。")
        return 130


if __name__ == "__main__":
    sys.exit(main())
