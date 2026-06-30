from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from config import CSV_PATH, DB_PATH, ensure_runtime_dirs


@contextmanager
def connect():
    ensure_runtime_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    with connect() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS catalog_items (
                good_id INTEGER PRIMARY KEY,
                name_cn TEXT NOT NULL,
                market_hash_name TEXT,
                buff_id TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                discovered_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scan_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                total_items INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                opportunity_count INTEGER NOT NULL DEFAULT 0,
                message TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                good_id INTEGER NOT NULL,
                name_cn TEXT NOT NULL,
                market_hash_name TEXT NOT NULL,
                buff_id TEXT NOT NULL,
                steam_buy_price REAL NOT NULL,
                steam_sell_price REAL NOT NULL,
                steam_buy_num INTEGER,
                steam_sell_num INTEGER,
                buff_buy_price REAL NOT NULL,
                buff_sell_price REAL NOT NULL,
                buff_buy_num INTEGER,
                buff_sell_num INTEGER,
                steam_actual_cost REAL NOT NULL,
                buff_net_proceeds REAL NOT NULL,
                net_profit REAL NOT NULL,
                net_profit_rate REAL NOT NULL,
                steam_url TEXT NOT NULL,
                buff_url TEXT NOT NULL,
                source_updated_at TEXT,
                is_opportunity INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES scan_runs(run_id)
            );

            CREATE INDEX IF NOT EXISTS idx_scan_results_run_id ON scan_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_scan_results_opportunity ON scan_results(run_id, is_opportunity);
            """
        )


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def active_catalog_count() -> int:
    with connect() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM catalog_items WHERE active = 1").fetchone()[0])


def reset_catalog_and_results() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM scan_results")
        conn.execute("DELETE FROM scan_runs")
        conn.execute("DELETE FROM catalog_items")


def insert_catalog_items(items: Iterable[dict[str, Any]]) -> int:
    timestamp = now_text()
    rows = [
        (
            int(item["good_id"]),
            str(item["name_cn"]),
            item.get("market_hash_name"),
            str(item["buff_id"]) if item.get("buff_id") is not None else None,
            timestamp,
            timestamp,
        )
        for item in items
    ]
    if not rows:
        return 0
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO catalog_items (good_id, name_cn, market_hash_name, buff_id, active, discovered_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(good_id) DO UPDATE SET
                name_cn = excluded.name_cn,
                market_hash_name = COALESCE(excluded.market_hash_name, catalog_items.market_hash_name),
                buff_id = COALESCE(excluded.buff_id, catalog_items.buff_id),
                active = 1,
                updated_at = excluded.updated_at
            """,
            rows,
        )
    return len(rows)


def get_active_catalog_items() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT good_id, name_cn, market_hash_name, buff_id FROM catalog_items WHERE active = 1 ORDER BY good_id"
        ).fetchall()


def update_catalog_details(good_id: int, market_hash_name: str | None, buff_id: int | str | None) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE catalog_items
            SET market_hash_name = COALESCE(?, market_hash_name),
                buff_id = COALESCE(?, buff_id),
                updated_at = ?
            WHERE good_id = ?
            """,
            (market_hash_name, str(buff_id) if buff_id is not None else None, now_text(), good_id),
        )


def create_scan_run(total_items: int) -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO scan_runs (started_at, status, total_items) VALUES (?, 'running', ?)",
            (now_text(), total_items),
        )
        return int(cursor.lastrowid)


def finish_scan_run(
    run_id: int,
    *,
    status: str,
    success_count: int,
    skipped_count: int,
    error_count: int,
    opportunity_count: int,
    message: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE scan_runs
            SET finished_at = ?, status = ?, success_count = ?, skipped_count = ?, error_count = ?,
                opportunity_count = ?, message = ?
            WHERE run_id = ?
            """,
            (
                now_text(),
                status,
                success_count,
                skipped_count,
                error_count,
                opportunity_count,
                message,
                run_id,
            ),
        )


def insert_scan_results(run_id: int, rows: Iterable[dict[str, Any]]) -> int:
    data = list(rows)
    if not data:
        return 0
    created_at = now_text()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO scan_results (
                run_id, good_id, name_cn, market_hash_name, buff_id,
                steam_buy_price, steam_sell_price, steam_buy_num, steam_sell_num,
                buff_buy_price, buff_sell_price, buff_buy_num, buff_sell_num,
                steam_actual_cost, buff_net_proceeds, net_profit, net_profit_rate,
                steam_url, buff_url, source_updated_at, is_opportunity, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    row["good_id"],
                    row["name_cn"],
                    row["market_hash_name"],
                    str(row["buff_id"]),
                    row["steam_buy_price"],
                    row["steam_sell_price"],
                    row.get("steam_buy_num"),
                    row.get("steam_sell_num"),
                    row["buff_buy_price"],
                    row["buff_sell_price"],
                    row.get("buff_buy_num"),
                    row.get("buff_sell_num"),
                    row["steam_actual_cost"],
                    row["buff_net_proceeds"],
                    row["net_profit"],
                    row["net_profit_rate"],
                    row["steam_url"],
                    row["buff_url"],
                    row.get("source_updated_at"),
                    1 if row["is_opportunity"] else 0,
                    created_at,
                )
                for row in data
            ],
        )
    return len(data)


def latest_usable_run() -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM scan_runs
            WHERE status IN ('success', 'partial') AND success_count > 0
            ORDER BY run_id DESC
            LIMIT 1
            """
        ).fetchone()


def latest_opportunities() -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    run = latest_usable_run()
    if run is None:
        return None, []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM scan_results
            WHERE run_id = ? AND is_opportunity = 1
            ORDER BY net_profit_rate DESC, net_profit DESC
            """,
            (run["run_id"],),
        ).fetchall()
    return run, rows


def export_latest_opportunities_csv() -> int:
    run, rows = latest_opportunities()
    ensure_runtime_dirs()
    headers = [
        "rank",
        "name_cn",
        "steam_buy_price",
        "steam_sell_price",
        "buff_buy_price",
        "buff_sell_price",
        "steam_actual_cost",
        "buff_net_proceeds",
        "net_profit",
        "net_profit_rate_percent",
        "steam_url",
        "buff_url",
        "source_updated_at",
        "scan_finished_at",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "rank": index,
                    "name_cn": row["name_cn"],
                    "steam_buy_price": row["steam_buy_price"],
                    "steam_sell_price": row["steam_sell_price"],
                    "buff_buy_price": row["buff_buy_price"],
                    "buff_sell_price": row["buff_sell_price"],
                    "steam_actual_cost": row["steam_actual_cost"],
                    "buff_net_proceeds": row["buff_net_proceeds"],
                    "net_profit": row["net_profit"],
                    "net_profit_rate_percent": round(row["net_profit_rate"] * 100, 4),
                    "steam_url": row["steam_url"],
                    "buff_url": row["buff_url"],
                    "source_updated_at": row["source_updated_at"],
                    "scan_finished_at": run["finished_at"] if run else "",
                }
            )
    return len(rows)
