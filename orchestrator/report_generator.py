import html
import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    def __init__(self, report_dir, template_dir=None):
        self.report_dir = report_dir
        self.template_dir = template_dir or os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir), autoescape=True)

    def render_html(
        self,
        rollout_name,
        namespace,
        decision,
        experiments,
        service_name,
        max_burn_seen,
        threshold,
        budget_ok,
        reason,
        grafana_url="",
    ):
        return self.env.get_template("report.html.j2").render(
            rollout_name=rollout_name,
            namespace=namespace,
            decision=decision,
            decision_colour="green" if decision == "PROMOTED" else "red",
            experiments=experiments,
            service_name=service_name,
            max_burn_seen=max_burn_seen,
            threshold=threshold,
            budget_ok=budget_ok,
            reason=reason,
            grafana_url=grafana_url,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def generate(self, rollout_name, namespace, decision, experiments, service_name, max_burn_seen, threshold, budget_ok, reason, grafana_url=""):
        Path(self.report_dir).mkdir(parents=True, exist_ok=True)
        html_content = self.render_html(
            rollout_name=rollout_name,
            namespace=namespace,
            decision=decision,
            experiments=experiments,
            service_name=service_name,
            max_burn_seen=max_burn_seen,
            threshold=threshold,
            budget_ok=budget_ok,
            reason=reason,
            grafana_url=grafana_url,
        )
        file_name = f"{rollout_name}-{int(datetime.now(timezone.utc).timestamp())}.html"
        target_path = os.path.join(self.report_dir, file_name)
        with open(target_path, "w", encoding="utf-8") as handle:
            handle.write(html_content)
        return target_path
