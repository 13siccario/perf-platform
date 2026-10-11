import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class ChaosEngine:
    DEFAULT_EXPERIMENTS = [
        "pod-delete",
        "cpu-hog-exec",
        "pod-network-latency",
    ]

    def __init__(self, api, experiments=None, namespace="default", timeout_seconds=300):
        self.api = api
        self.experiments = experiments or self.DEFAULT_EXPERIMENTS
        self.namespace = namespace
        self.timeout_seconds = timeout_seconds

    def _engine_name(self, experiment_name):
        timestamp = int(time.time())
        return f"chaos-gate-{experiment_name}-{timestamp}"

    def _result_name(self, engine_name, experiment_name):
        return f"{engine_name}-{experiment_name}"

    async def _wait_for_verdict(self, engine_name, experiment_name):
        result_name = self._result_name(engine_name, experiment_name)
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            try:
                result = self.api.get_namespaced_custom_object(
                    group="litmuschaos.io",
                    version="v1alpha1",
                    plural="chaosresults",
                    namespace=self.namespace,
                    name=result_name,
                )
                verdict = result.get("status", {}).get("experimentStatus", {}).get("verdict")
                if verdict in {"Pass", "Fail"}:
                    return verdict
            except Exception as exc:  # pragma: no cover - cluster-side fallback
                logger.warning("ChaosResult lookup for %s failed: %s", result_name, exc)
            await asyncio.sleep(10)
        return "Fail"

    async def run_all(self):
        for experiment_name in self.experiments:
            engine_name = self._engine_name(experiment_name)
            chaos_engine = {
                "apiVersion": "litmuschaos.io/v1alpha1",
                "kind": "ChaosEngine",
                "metadata": {"name": engine_name, "namespace": self.namespace},
                "spec": {
                    "appinfo": {"appns": self.namespace, "applabel": "app=backend"},
                    "chaosServiceAccount": "litmus-admin",
                    "experiments": [
                        {"name": experiment_name, "spec": {"components": {"env": []}}}
                    ],
                },
            }
            try:
                self.api.create_namespaced_custom_object(
                    group="litmuschaos.io",
                    version="v1alpha1",
                    plural="chaosengines",
                    namespace=self.namespace,
                    body=chaos_engine,
                )
            except Exception as exc:  # pragma: no cover - cluster-side fallback
                logger.error("Failed to create ChaosEngine for %s: %s", experiment_name, exc)
                return False

            verdict = await self._wait_for_verdict(engine_name, experiment_name)
            if verdict != "Pass":
                logger.error("Chaos experiment %s returned %s; aborting gate", experiment_name, verdict)
                return False
        return True
