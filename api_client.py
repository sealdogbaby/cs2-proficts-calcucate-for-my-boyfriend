from __future__ import annotations

import time
from typing import Any

import requests

from config import Settings


class CsqaqApiError(RuntimeError):
    """Raised when CSQAQ does not return a successful business response."""


class CsqaqClient:
    def __init__(self, settings: Settings, logger) -> None:
        self.settings = settings
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "ApiToken": settings.api_token,
                "Accept": "application/json",
                "User-Agent": "CS2-Spread-Radar-V1/1.0",
            }
        )
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_seconds = self.settings.request_interval_seconds - elapsed
        if wait_seconds > 0:
            time.sleep(wait_seconds)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self._throttle()
        url = f"{self.settings.api_base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=25, **kwargs)
        except requests.RequestException as exc:
            self._last_request_at = time.monotonic()
            raise CsqaqApiError(f"网络请求失败：{exc}") from exc
        finally:
            self._last_request_at = time.monotonic()

        try:
            payload = response.json()
        except ValueError as exc:
            excerpt = response.text[:300].replace("\n", " ")
            raise CsqaqApiError(
                f"CSQAQ 返回了无法解析的响应（HTTP {response.status_code}）：{excerpt}"
            ) from exc

        code = payload.get("code")
        if response.status_code >= 400 or (code is not None and not 200 <= int(code) < 300):
            message = payload.get("msg") or payload.get("detail") or str(payload)[:300]
            raise CsqaqApiError(f"CSQAQ 请求失败（HTTP {response.status_code}, code={code}）：{message}")
        return payload

    def get_page_list(self, page_index: int, page_size: int) -> list[dict[str, Any]]:
        payload = self._request(
            "POST",
            "/info/get_page_list",
            json={"page_index": page_index, "page_size": page_size, "search": "", "filter": {}},
        )
        data = payload.get("data") or {}
        rows = data.get("data") or []
        if not isinstance(rows, list):
            raise CsqaqApiError("CSQAQ 饰品列表返回格式异常：data.data 不是列表。")
        return rows

    def get_good(self, good_id: int) -> dict[str, Any]:
        payload = self._request("GET", "/info/good", params={"id": good_id})
        data = payload.get("data") or {}
        goods_info = data.get("goods_info")
        if not isinstance(goods_info, dict):
            raise CsqaqApiError("CSQAQ 单件详情返回格式异常：缺少 data.goods_info。")
        return goods_info
