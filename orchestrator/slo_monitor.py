import asyncio
import json
import logging
from typing import Tuple

import requests

logger = logging.getLogger(__name__)


class SLOMonitor:
    def __init__(self, prometheus_url, threshold, service_name=None):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.threshold = float(threshold)
        self.service_name = service_name

    async def _query(self, url: str, params: dict | None = None):
        if params is None:
            params = {"query": url}
            url = f"{self.prometheus_url}/api/v1/query"
        response = await asyncio.to_thread(requests.get, url, params=params, timeout=5)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"data": {"result": []}}

    def _extract_burn(self, result):
        if hasattr(result, "json"):
            try:
                result = result.json()
            except ValueError:
                result = None
        elif hasattr(result, "text"):
            try:
                result = json.loads(result.text)
            except (TypeError, ValueError):
                result = None

        if isinstance(result, dict):
            payload = result.get("data", {}).get("result") or []
            if not payload:
                logger.warning("Prometheus query returned no SLO data; treating as 0.0")
                return 0.0
            highest = 0.0
            for item in payload:
                value = item.get("value", [None, "0"])[1]
                try:
                    highest = max(highest, float(value))
                except (TypeError, ValueError):
                    continue
            return highest
        return 0.0

    async def monitor(self, duration_seconds: int, poll_interval_seconds: int) -> Tuple[bool, float]:
        max_burn_seen = 0.0
        deadline = asyncio.get_running_loop().time() + duration_seconds
        while True:
            try:
                query = (
                    f'slo:sli_error:ratio_rate5m{{sloth_service="{self.service_name}"}}'
                    if self.service_name
                    else "slo:sli_error:ratio_rate5m"
                )
                result = await self._query(f"{self.prometheus_url}/api/v1/query", {"query": query})
                burn = self._extract_burn(result)
                max_burn_seen = max(max_burn_seen, burn)
                if burn > self.threshold:
                    return False, max_burn_seen
            except Exception as exc:  # pragma: no cover - integration guard
                logger.warning("Prometheus unreachable or query failed: %s", exc)
            now = asyncio.get_running_loop().time()
            if now >= deadline:
                return True, max_burn_seen
            await asyncio.sleep(min(poll_interval_seconds, max(0, deadline - now)))
