# perf-platform

A bare-minimum (v1) performance gate: a tiny shop API (FastAPI + Postgres) plus k6 tests that run on every pull request.

## Run locally

```bash
docker compose up -d --build                     # app on :8000
k6 run scenarios/load/products.js                # load test (p95 < 500ms, <1% errors)
k6 run scenarios/concurrency/oversell.js         # 100 users buy 10 items; exactly 10 must succeed
docker compose down -v
```

Demo the race condition: `BUY_MODE=naive docker compose up -d --build` makes `oversell.js` fail (the read-then-write buy path oversells). The default `atomic` mode passes.

CI: [.github/workflows/perf-gate.yml](.github/workflows/perf-gate.yml) runs both tests on every PR; a broken threshold fails the check.

Not in v1: Prometheus/Grafana, baseline comparison, orchestrator API, Slack/PR comments.