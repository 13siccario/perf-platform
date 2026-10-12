# Chaos-Gated Canary Delivery Pipeline

This repository implements the chaos-gated canary delivery design described in the attached design document. The project is centered on a Python orchestrator that watches Argo Rollouts pause gates, runs LitmusChaos experiments, monitors Prometheus SLO burn rate, decides whether to promote or abort, and writes a final HTML evidence report to a PVC.

## What is included

- Python orchestrator in [orchestrator](orchestrator)
- Kubernetes RBAC, Deployment, PVC, and sample Rollout manifests in [k8s](k8s)
- LitmusChaos reference manifests in [k8s/chaos](k8s/chaos)
- Sloth/SLO definition examples in [slo](slo)
- A focused regression suite in [tests/test_orchestrator.py](tests/test_orchestrator.py)
- An HTML report template in [orchestrator/templates/report.html.j2](orchestrator/templates/report.html.j2)

## Design alignment

This implementation covers the main design areas:

- Rollout watch and gate detection
- SLO burn-rate monitor
- sequential chaos execution with fail-fast behavior
- promote/abort control via Kubernetes API patching
- HTML report generation with decision evidence
- deployment manifests for the orchestrator and RBAC model

## Local setup

Create and activate a local venv:

```bash
cd /Users/cheeseburger/Developer/projectsxd/perf-platform
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r orchestrator/requirements.txt
```

Run the check suite:

```bash
python -m pytest -q tests/test_orchestrator.py
```

## Run the orchestrator

In a Kubernetes cluster with Argo Rollouts, LitmusChaos, and Prometheus available:

```bash
export NAMESPACE=default
export CHAOS_GATE_STEP_INDEX=1
export PROMETHEUS_URL=http://prometheus-operated:9090
export SLO_SERVICE_NAME=backend-api
export ERROR_BUDGET_THRESHOLD=0.02
export CHAOS_DURATION_SECONDS=180
export POLL_INTERVAL_SECONDS=10
export REPORT_DIR=/reports

python -m orchestrator
```

## Kubernetes deployment

Apply the manifests in this order:

```bash
kubectl apply -f k8s/orchestrator/rbac.yaml
kubectl apply -f k8s/orchestrator/pvc.yaml
kubectl apply -f k8s/orchestrator/deployment.yaml
kubectl apply -f k8s/rollout/rollout.yaml
```

Then allow the rollout to pause at the designated gate step and let the orchestrator drive the promote or abort decision.

## Notes

This is an implementation aligned with the design document, but it still assumes the surrounding cluster components are available in the target environment. The repo is set up for the orchestrator logic and manifests rather than a standalone local-only demo app.