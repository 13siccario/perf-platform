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

    def _query(self, metric_name: str):
        params = {"query": metric_name}
        response = requests.get(f"{self.prometheus_url}/api/v1/query", params=params, timeout=5)
        response.raise_for_status()
        return response.json()

    async def monitor(self, duration_seconds: int, poll_interval_seconds: int) -> Tuple[bool, float]:
        max_burn_seen = 0.0
        deadline = asyncio.get_running_loop().time() + duration_seconds
        while True:
            try:
                result = self._query(
                    f'slo:sli_error:ratio_rate5m{{sloth_service="{self.service_name}"}}'
                    if self.service_name
                    else "slo:sli_error:ratio_rate5m"
                )
                payload = result.get("data", {}).get("result") or []
                if payload:
                    for item in payload:
                        value = item.get("value", [None, "0"])[1]
                        try:
                            burn = float(value)
                        except (TypeError, ValueError):
                            burn = 0.0
                        max_burn_seen = max(max_burn_seen, burn)
                        if burn > self.threshold:
                            return False, max_burn_seen
                else:
                    logger.warning("Prometheus query returned no SLO data; treating as 0.0")
            except Exception as exc:  # pragma: no cover - integration guard
                logger.warning("Prometheus unreachable or query failed: %s", exc)
            now = asyncio.get_running_loop().time()
            if now >= deadline:
                return True, max_burn_seen
            await asyncio.sleep(min(poll_interval_seconds, max(0, deadline - now)))
