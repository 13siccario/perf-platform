import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    namespace: str = os.getenv("NAMESPACE", "default")
    chaos_gate_step_index: int = int(os.getenv("CHAOS_GATE_STEP_INDEX", "1"))
    prometheus_url: str = os.getenv("PROMETHEUS_URL", "http://prometheus-operated:9090")
    slo_service_name: str = os.getenv("SLO_SERVICE_NAME", "backend-api")
    error_budget_threshold: float = float(os.getenv("ERROR_BUDGET_THRESHOLD", "0.02"))
    chaos_duration_seconds: int = int(os.getenv("CHAOS_DURATION_SECONDS", "180"))
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
    chaos_app_label: str = os.getenv("CHAOS_APP_LABEL", "app=backend")
    chaos_app_namespace: str = os.getenv("CHAOS_APP_NAMESPACE", "default")
    chaos_service_account: str = os.getenv("CHAOS_SERVICE_ACCOUNT", "litmus-admin")
    chaos_result_timeout_seconds: int = int(os.getenv("CHAOS_RESULT_TIMEOUT_SECONDS", "300"))
    report_dir: str = os.getenv("REPORT_DIR", "/reports")
    grafana_dashboard_url: str = os.getenv("GRAFANA_DASHBOARD_URL", "")
    max_concurrent_gate_runs: int = int(os.getenv("MAX_CONCURRENT_GATE_RUNS", "2"))


SETTINGS = Settings()
