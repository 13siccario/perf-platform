import asyncio
import logging
import os
from datetime import datetime, timezone

from kubernetes import client, config

from .chaos_engine import ChaosEngine
from .config import SETTINGS
from .report_generator import ReportGenerator
from .rollout_controller import RolloutController
from .slo_monitor import SLOMonitor
from .watcher import RolloutWatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ChaosGatedOrchestrator:
    def __init__(self):
        try:
            config.load_incluster_config()
        except Exception:  # pragma: no cover - local development fallback
            config.load_kube_config()

        self.k8s_api = client.CustomObjectsApi()
        self.rollout_watcher = RolloutWatcher(
            self.k8s_api,
            namespace=SETTINGS.namespace,
            gate_step_index=SETTINGS.chaos_gate_step_index,
        )
        self.slo_monitor = SLOMonitor(
            prometheus_url=SETTINGS.prometheus_url,
            threshold=SETTINGS.error_budget_threshold,
            service_name=SETTINGS.slo_service_name,
        )
        self.chaos_engine = ChaosEngine(
            api=self.k8s_api,
            experiments=["pod-delete", "cpu-hog-exec", "pod-network-latency"],
            namespace=SETTINGS.namespace,
            timeout_seconds=SETTINGS.chaos_result_timeout_seconds,
        )
        self.rollout_controller = RolloutController(api=self.k8s_api)
        self.report_generator = ReportGenerator(report_dir=SETTINGS.report_dir)

    async def handle_gate(self, rollout):
        name = rollout.get("metadata", {}).get("name")
        namespace = rollout.get("metadata", {}).get("namespace", SETTINGS.namespace)
        logger.info("Triggering chaos gate for rollout %s/%s", namespace, name)

        chaos_task = asyncio.create_task(self.chaos_engine.run_all())
        slo_task = asyncio.create_task(
            self.slo_monitor.monitor(
                duration_seconds=SETTINGS.chaos_duration_seconds,
                poll_interval_seconds=SETTINGS.poll_interval_seconds,
            )
        )

        chaos_ok, budget_ok = await asyncio.gather(chaos_task, slo_task)
        chaos_success = bool(chaos_ok)
        slo_success, max_burn_seen = budget_ok

        decision = "PROMOTED" if chaos_success and slo_success else "ABORTED"
        reason = "All chaos checks and SLO budgets passed"
        if not chaos_success:
            reason = "At least one chaos experiment returned Fail or timed out"
        elif not slo_success:
            reason = f"error budget burned {max_burn_seen:.3f} exceeding threshold {SETTINGS.error_budget_threshold:.3f}"

        if decision == "PROMOTED":
            self.rollout_controller.promote(name=name, namespace=namespace)
        else:
            self.rollout_controller.abort(name=name, namespace=namespace)

        self.report_generator.generate(
            rollout_name=name,
            namespace=namespace,
            decision=decision,
            experiments=[
                {"name": ex, "duration": 60, "verdict": "Pass" if chaos_success else "Fail"}
                for ex in self.chaos_engine.experiments
            ],
            service_name=SETTINGS.slo_service_name,
            max_burn_seen=max_burn_seen,
            threshold=SETTINGS.error_budget_threshold,
            budget_ok=slo_success,
            reason=reason,
            grafana_url=SETTINGS.grafana_dashboard_url,
        )
        logger.info("Finished gate run for %s/%s with outcome %s", namespace, name, decision)

    async def run(self):
        async for rollout in self.rollout_watcher.watch():
            await self.handle_gate(rollout)


async def main():
    orchestrator = ChaosGatedOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
