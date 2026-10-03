# perf-platform

A reusable k6 performance gate for pull requests and pushes. It includes a FastAPI + Postgres demo shop, load and concurrency scenarios, and GitHub Actions workflows that publish downloadable test summaries.

## What the checks measure

| Scenario | Workload | Pass condition |
| --- | --- | --- |
| `scenarios/load/products.js` | Ramps to 20 virtual users requesting `/products` | p95 latency under 500 ms and fewer than 1% failed requests |
| `scenarios/concurrency/oversell.js` | 100 users each try to buy from stock of 10 | Exactly 10 purchases succeed |

The demo app uses an atomic stock update by default. Set `BUY_MODE=naive` to enable a deliberately unsafe read-then-write implementation and see the concurrency threshold fail.

## Requirements

- Docker with the Compose plugin
- [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) to run the scenarios locally
- A GitHub repository with GitHub Actions enabled for automatic runs

## Run locally

From the repository root, start the app and run both scenarios:

```sh
docker compose up -d --build
curl http://localhost:8000/health
k6 run scenarios/load/products.js
k6 run scenarios/concurrency/oversell.js
```

To demonstrate the race condition, restart the app in naive mode and rerun the concurrency scenario:

```sh
docker compose down -v
BUY_MODE=naive docker compose up -d --build
k6 run scenarios/concurrency/oversell.js
```

The final command should fail because more than 10 requests can report a successful purchase. Restore the normal mode with:

```sh
docker compose down -v
docker compose up -d --build
```

`docker compose down -v` removes the demo database volume and its data.

## Automatic runs and reports

The included [performance workflow](.github/workflows/perf-gate.yml) runs automatically:

- On every branch push, including pushes to feature branches.
- When a pull request is opened, reopened, or updated.

A push to a branch with an open pull request triggers both events, so GitHub Actions creates two runs for that commit.

To find a run and its reports:

1. Open the repository on GitHub and select **Actions**.
2. Select the `perf-gate` workflow, then open the run for the branch or pull request you want.
3. Read the `Run load scenario` and `Run concurrency scenario` steps for the human-readable k6 output and threshold results.
4. In the run's **Artifacts** section, download `k6-reports-<run-id>-<attempt>` for `load-summary.json` and `concurrency-summary.json`.

Artifacts are retained for 30 days. Reports are uploaded even when a test fails, so summaries from tests that ran are still available. If app startup or the health check fails before k6 starts, no k6 report is produced.

## Use the workflow in another repository

1. Add or adapt k6 scenarios in the application repository. Each scenario should use `__ENV.TARGET_URL` for the app's base URL.
2. Add a workflow file under `.github/workflows/`, for example `performance.yml`:

```yaml
name: performance

on:
  push:
    branches: ['**']
  pull_request:

jobs:
  perf:
    uses: 13siccario/perf-platform/.github/workflows/reusable-perf-gate.yml@main
    with:
      app_start_command: docker compose up -d --build
      healthcheck_url: http://localhost:8000/health
      target_url: http://localhost:8000
      load_scenario: scenarios/load/products.js
      concurrency_scenario: scenarios/concurrency/oversell.js
      cleanup_command: docker compose down -v
```

The reusable workflow checks out the calling repository, installs k6, starts the app, waits for the optional health check, runs both scenarios, cleans up, and uploads the summaries to that run. Its scenario paths are relative to the calling repository.

### Inputs

| Input | Required | Description |
| --- | --- | --- |
| `target_url` | Yes | Base URL passed to both scenarios as `TARGET_URL`. Do not add a trailing slash when the scenarios append paths. |
| `load_scenario` | Yes | Repository-relative path to the load scenario. |
| `concurrency_scenario` | Yes | Repository-relative path to the concurrency scenario. |
| `app_start_command` | No | Shell command to start the app. The command should return once the app is running, for example by using `docker compose up -d`. |
| `healthcheck_url` | No | URL polled for up to 60 seconds before running k6. |
| `cleanup_command` | No | Shell command run after tests, including when a test fails. |

The included [caller workflow](.github/workflows/perf-gate.yml) shows how this repository runs the reusable workflow against the demo shop.

## Scope

Included: load and concurrency checks, a demo FastAPI + Postgres app, automatic GitHub Actions runs, downloadable k6 summaries, and a reusable workflow.

Not included: hosted dashboards, saved baseline comparisons, a separate orchestration API, or Slack and pull request comments.