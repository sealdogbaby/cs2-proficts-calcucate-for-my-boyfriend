from __future__ import annotations

import sys
import threading
import webbrowser

from flask import Flask, render_template_string

from config import ConfigError, load_settings
from database import initialize_database, latest_opportunities
from logging_utils import configure_logging

HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="{{ refresh_seconds }}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CS2 Steam × BUFF 价差雷达</title>
<style>
  /*
     重要：不要给 table-wrap 设置 overflow-x:auto。
     有横向 overflow 的父元素会让 Chrome/Edge 把 sticky 表头限制在容器里，
     页面整体往下滚动时表头会消失。
     这里让页面本身承担横向滚动，表头就能稳定吸附在浏览器顶部。
  */
  body { font-family: "Microsoft YaHei", Arial, sans-serif; margin: 24px; background: #f5f7fb; color: #1f2937; }
  h1 { margin-bottom: 6px; }
  .note { color: #4b5563; margin-bottom: 18px; line-height: 1.55; }
  .cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
  .card { background: white; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.10); min-width: 150px; }
  .card .label { color: #6b7280; font-size: 13px; }
  .card .value { font-size: 20px; font-weight: 700; margin-top: 5px; }

  .table-wrap { overflow: visible; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.10); }
  table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 1380px; }
  th, td { border-bottom: 1px solid #e5e7eb; padding: 10px 8px; text-align: right; white-space: nowrap; }
  thead th {
    position: sticky;
    top: 0;
    z-index: 20;
    background: #f9fafb;
    font-size: 13px;
    color: #374151;
    box-shadow: 0 2px 0 #d1d5db;
  }
  th:nth-child(2), td:nth-child(2) { text-align: left; white-space: normal; min-width: 210px; }
  tr:hover { background: #f9fafb; }
  .positive { color: #047857; font-weight: 700; }
  .button { display: inline-block; padding: 6px 10px; border-radius: 5px; text-decoration: none; color: #fff; background: #2563eb; font-size: 13px; }
  .button.buff { background: #059669; }
  .empty { background: white; border-radius: 8px; padding: 28px; box-shadow: 0 1px 3px rgba(0,0,0,.10); }
  .warning { color: #92400e; }
  footer { color: #6b7280; margin-top: 16px; font-size: 13px; }
</style>
</head>
<body>
<h1>CS2 Steam × BUFF 价差雷达 V1</h1>
<p class="note">仅展示净利润率严格大于 {{ min_profit_percent }}% 的记录。价格来自 CSQAQ API，仅供参考；最终以 Steam 与 BUFF 页面实际价格、商品属性和人工判断为准。</p>

{% if run %}
<div class="cards">
  <div class="card"><div class="label">最近完成扫描</div><div class="value">{{ run['finished_at'] }}</div></div>
  <div class="card"><div class="label">扫描状态</div><div class="value">{{ run['status'] }}</div></div>
  <div class="card"><div class="label">成功 / 跳过 / 错误</div><div class="value">{{ run['success_count'] }} / {{ run['skipped_count'] }} / {{ run['error_count'] }}</div></div>
  <div class="card"><div class="label">符合利润条件</div><div class="value">{{ rows|length }} 件</div></div>
</div>
{% endif %}

{% if rows %}
<div class="table-wrap">
<table>
<thead>
<tr>
  <th>排名</th><th>饰品名称</th><th>Steam 求购价</th><th>Steam 在售价</th><th>BUFF 求购价</th><th>BUFF 在售价</th>
  <th>Steam 实际成本</th><th>BUFF 预估到账</th><th>净利润</th><th>净利润率</th><th>Steam</th><th>BUFF</th><th>数据更新时间</th>
</tr>
</thead>
<tbody>
{% for row in rows %}
<tr>
  <td>{{ loop.index }}</td>
  <td>{{ row['name_cn'] }}</td>
  <td>¥{{ '%.2f'|format(row['steam_buy_price']) }}</td>
  <td>¥{{ '%.2f'|format(row['steam_sell_price']) }}</td>
  <td>¥{{ '%.2f'|format(row['buff_buy_price']) }}</td>
  <td>¥{{ '%.2f'|format(row['buff_sell_price']) }}</td>
  <td>¥{{ '%.2f'|format(row['steam_actual_cost']) }}</td>
  <td>¥{{ '%.2f'|format(row['buff_net_proceeds']) }}</td>
  <td class="positive">¥{{ '%.2f'|format(row['net_profit']) }}</td>
  <td class="positive">{{ '%.2f'|format(row['net_profit_rate'] * 100) }}%</td>
  <td><a class="button" href="{{ row['steam_url'] }}" target="_blank" rel="noopener">打开 Steam</a></td>
  <td><a class="button buff" href="{{ row['buff_url'] }}" target="_blank" rel="noopener">打开 BUFF</a></td>
  <td>{{ row['source_updated_at'] or '-' }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
{% else %}
<div class="empty">
  {% if run %}
    <strong>最近一轮扫描已完成，但没有净利润率严格大于 {{ min_profit_percent }}% 的饰品。</strong>
  {% else %}
    <strong>暂时没有成功扫描结果。</strong>
    <p class="warning">请先依次运行 init_catalog.bat 和 run_once.bat；然后刷新本页。</p>
  {% endif %}
</div>
{% endif %}
<footer>本页每 {{ refresh_seconds }} 秒自动刷新。网页只读取本机 SQLite，不会在浏览器中重复请求 CSQAQ API。</footer>
</body>
</html>"""


def create_app(settings):
    app = Flask(__name__)

    @app.get("/")
    def index():
        run, rows = latest_opportunities()
        return render_template_string(
            HTML,
            run=run,
            rows=rows,
            refresh_seconds=settings.dashboard_refresh_seconds,
            min_profit_percent=f"{settings.min_net_profit_rate * 100:g}",
        )

    return app


def main() -> int:
    logger = configure_logging()
    try:
        settings = load_settings(require_token=False)
    except ConfigError as exc:
        logger.error(str(exc))
        return 2

    initialize_database()
    app = create_app(settings)
    url = f"http://{settings.dashboard_host}:{settings.dashboard_port}"
    logger.info("本地监控网页地址：%s", url)
    logger.info("网页只绑定本机，不会开放到局域网或公网。")

    if settings.dashboard_open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=settings.dashboard_host, port=settings.dashboard_port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
