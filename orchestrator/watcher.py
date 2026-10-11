import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class RolloutWatcher:
    """Stream Rollout events and emit named gate triggers."""

    def __init__(self, api, namespace, gate_step_index=1, dedupe_window_seconds=300):
        self.api = api
        self.namespace = namespace
        self.gate_step_index = gate_step_index
        self.dedupe_window_seconds = dedupe_window_seconds
        self._last_triggered = {}

    async def watch(self):
        backoff_seconds = 1
        while True:
            try:
                stream = self.api.watch_namespaced_custom_object(
                    group="argoproj.io",
                    version="v1alpha1",
                    plural="rollouts",
                    namespace=self.namespace,
                )
                async for event in stream:
                    obj = event.get("object") if isinstance(event, dict) else None
                    if obj is None:
                        continue
                    status = obj.get("status", {})
                    phase = status.get("phase")
                    current_step = status.get("currentStepIndex")
                    if phase == "Paused" and current_step == self.gate_step_index:
                        rollout_name = obj.get("metadata", {}).get("name")
                        if not rollout_name:
                            continue
                        now = time.time()
                        last_seen = self._last_triggered.get(rollout_name)
                        if last_seen and (now - last_seen) < self.dedupe_window_seconds:
                            logger.warning("Dropping duplicate gate trigger for rollout %s", rollout_name)
                            continue
                        self._last_triggered[rollout_name] = now
                        yield obj
                backoff_seconds = 1
            except Exception as exc:  # pragma: no cover - exercised in integration env
                logger.warning("Rollout watch failed (%s). Reconnecting in %ss", exc, backoff_seconds)
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 60)
