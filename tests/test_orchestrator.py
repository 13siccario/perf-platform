import asyncio
from types import SimpleNamespace

import pytest

from orchestrator.config import SETTINGS
from orchestrator.report_generator import ReportGenerator
from orchestrator.rollout_controller import RolloutController
from orchestrator.slo_monitor import SLOMonitor


def test_slo_monitor_detects_breach():
    class FakeResponse:
        status_code = 200
        text = "{\"status\":\"success\",\"data\":{\"resultType\":\"vector\",\"result\":[{\"metric\":{},\"value\":[1,\"0.03\"]}]}}"

    async def fake_query(url, params):
        return FakeResponse()

    monitor = SLOMonitor(prometheus_url="http://prometheus", threshold=0.02)
    monitor._query = fake_query

    ok, max_burn = asyncio.run(monitor.monitor(duration_seconds=0.01, poll_interval_seconds=0.01))

    assert ok is False
    assert max_burn == 0.03


def test_rollout_controller_promote_patch_uses_clear_pause():
    calls = []

    class FakeAPI:
        def patch_namespaced_custom_object(self, *args, **kwargs):
            calls.append(kwargs)
            return {"status": "patched"}

    controller = RolloutController(api=FakeAPI())
    controller.promote(name="demo-rollout", namespace="default")

    assert calls
    body = calls[0]["body"]
    assert body["spec"].get("paused") is None
    assert body["status"]["pauseConditions"] == []


def test_report_generator_writes_html():
    report_dir = "/tmp/chaos-gate-reports"
    generator = ReportGenerator(report_dir=report_dir)
    html = generator.render_html(
        rollout_name="demo-rollout",
        namespace="default",
        decision="PROMOTED",
        experiments=[{"name": "pod-delete", "duration": 60, "verdict": "Pass"}],
        service_name="backend-api",
        max_burn_seen=0.01,
        threshold=0.02,
        budget_ok=True,
        reason="All checks passed",
        grafana_url="",
    )

    assert "demo-rollout" in html
    assert "PROMOTED" in html
    assert "pod-delete" in html


@pytest.mark.asyncio
async def test_run_all_chaos_engine_uses_fail_fast():
    created = []

    class FakeAPI:
        def create_namespaced_custom_object(self, *args, **kwargs):
            created.append(kwargs["body"]["metadata"]["name"])
            return {"metadata": {"name": kwargs["body"]["metadata"]["name"]}}

        def get_namespaced_custom_object(self, *args, **kwargs):
            name = args[2]
            if "cpu-hog-exec" in name:
                return {"status": {"experimentStatus": {"verdict": "Fail"}}}
            return {"status": {"experimentStatus": {"verdict": "Pass"}}}

    engine = SimpleNamespace(api=FakeAPI(), experiments=["pod-delete", "cpu-hog-exec"])
    from orchestrator.chaos_engine import ChaosEngine

    result = await ChaosEngine(api=engine.api, experiments=["pod-delete", "cpu-hog-exec"]).run_all()

    assert result is False
    assert len(created) >= 1
