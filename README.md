# Statefy

**Track state for everything.**

Statefy is an open-source project for tracking desired and observed state, detecting drift, and eventually reconciling resources across different technologies. The goal is a lightweight, extensible control plane that isn't tied to a single infrastructure platform.

## Vision

Statefy aims to support resources managed through tools such as Terraform, Bicep, Kubernetes, PowerShell, Bash, and custom integrations. It is designed to work **without mandatory agents**: APIs, SDKs, CI/CD pipelines, and webhooks can participate directly, with optional agents where useful.

Planned capabilities include:

- Resource registration and desired/observed state tracking
- Drift detection and configurable reconciliation
- Pluggable executors and state storage
- Execution history, logs, and a web UI

> Statefy is in early development. The capabilities above describe the direction of the project, not a completed feature set.

## Current stack

- **Backend:** Python, FastAPI, Pydantic
- **Testing:** pytest, coverage, HTML test reports
- **CI:** GitHub Actions
- **Planned:** etcd-backed storage, reconciliation engine, React/TypeScript UI

## Getting started

Requires Python 3.12 or newer.

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to explore the API.

Current endpoints include:

| Endpoint | Description |
| --- | --- |
| `GET /health` | Service health information |
| `GET /api/v1/resources` | Resource listing (initial placeholder) |

## Running tests

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

GitHub Actions runs the test suite on pushes and pull requests and uploads test and coverage reports as workflow artifacts.

## Project status

**Early development (v0.1).** The API foundation and CI/testing workflow are in place. Next steps are the resource model, state storage abstraction, and reconciliation engine.

## License

License information will be added as the project evolves.
