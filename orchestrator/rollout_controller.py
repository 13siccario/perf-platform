import logging
import time

logger = logging.getLogger(__name__)


class RolloutController:
    def __init__(self, api=None):
        self.api = api

    def promote(self, name, namespace="default"):
        if self.api is None:
            return False
        body = {
            "spec": {"paused": None},
            "status": {"pauseConditions": []},
        }
        return self._patch(name, namespace, body)

    def abort(self, name, namespace="default"):
        if self.api is None:
            return False
        body = {
            "spec": {"template": {"metadata": {"annotations": {"rollout.argoproj.io/abort": "true"}}}},
            "status": {"abort": True},
        }
        return self._patch(name, namespace, body)

    def _patch(self, name, namespace, body):
        for attempt in range(1, 4):
            try:
                payload = self.api.patch_namespaced_custom_object(
                    group="argoproj.io",
                    version="v1alpha1",
                    plural="rollouts",
                    name=name,
                    namespace=namespace,
                    body=body,
                )
                logger.info("Rollout patch succeeded for %s/%s on attempt %s: %s", namespace, name, attempt, payload)
                return True
            except Exception as exc:  # pragma: no cover - integration guard
                logger.warning("Rollout patch failed for %s/%s (attempt %s/%s): %s", namespace, name, attempt, 3, exc)
                if attempt < 3:
                    time.sleep(2)
        logger.critical("Rollout patch failed for %s/%s after retries", namespace, name)
        return False
