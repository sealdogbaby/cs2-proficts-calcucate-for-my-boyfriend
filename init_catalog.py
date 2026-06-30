from __future__ import annotations

import argparse
import sys

from api_client import CsqaqApiError, CsqaqClient
from config import ConfigError, load_settings
from database import active_catalog_count, initialize_database, insert_catalog_items, reset_catalog_and_results
from filters import excluded_reason
from logging_utils import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 CS2 价差雷达测试饰品目录")
    parser.add_argument("--reset", action="store_true", help="清空旧目录与扫描结果后重建")
    args = parser.parse_args()

    logger = configure_logging()
    try:
        settings = load_settings(require_token=True)
    except ConfigError as exc:
        logger.error(str(exc))
        return 2

    initialize_database()
    existing = active_catalog_count()
    if existing > 0 and not args.reset:
        logger.info("本地目录已存在 %s 件饰品；为避免覆盖，未重新初始化。", existing)
        logger.info("如确实需要按当前 .env 重新建立目录，请双击 rebuild_catalog.bat。")
        return 0

    if args.reset:
        logger.warning("正在清空旧目录与旧扫描结果，然后重建测试目录。")
        reset_catalog_and_results()

    client = CsqaqClient(settings, logger)
    selected: list[dict[str, object]] = []
    page_index = 1
    page_size = min(100, max(50, settings.initial_sample_size * 2))

    logger.info(
        "开始建立测试目录：目标 %s 件；按 CSQAQ 默认目录顺序读取，过滤明确排除的特殊款式。",
        settings.initial_sample_size,
    )

    try:
        while len(selected) < settings.initial_sample_size:
            rows = client.get_page_list(page_index=page_index, page_size=page_size)
            if not rows:
                break

            for row in rows:
                good_id = row.get("id")
                name_cn = row.get("name")
                if good_id is None or not name_cn:
                    logger.warning("目录记录缺少 id 或中文名，跳过：%s", row)
                    continue

                reason = excluded_reason(str(name_cn), None, settings)
                if reason:
                    logger.info("初始化过滤：%s；饰品=%s", reason, name_cn)
                    continue

                selected.append({"good_id": int(good_id), "name_cn": str(name_cn)})
                if len(selected) >= settings.initial_sample_size:
                    break

            logger.info("已读取目录第 %s 页；当前选中 %s/%s 件。", page_index, len(selected), settings.initial_sample_size)
            page_index += 1

        if not selected:
            logger.error("未找到任何可用饰品。请检查 API Token/IP 白名单和 EXCLUDED_KEYWORDS 配置。")
            return 3

        saved = insert_catalog_items(selected)
        logger.info("测试目录建立完成：已保存 %s 件饰品到 data\\radar.sqlite。", saved)
        if saved < settings.initial_sample_size:
            logger.warning("只找到 %s 件，少于目标 %s 件。", saved, settings.initial_sample_size)
        logger.info("下一步请双击 run_once.bat 进行首次价格扫描。")
        return 0
    except CsqaqApiError as exc:
        logger.error("初始化失败：%s", exc)
        return 4
    except KeyboardInterrupt:
        logger.warning("用户中断了初始化。")
        return 130


if __name__ == "__main__":
    sys.exit(main())
