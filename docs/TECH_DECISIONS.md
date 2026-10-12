# StateOps — Technology Decisions

> **Track state for everything.**

## Purpose

StateOps is an open-source, technology-independent reconciliation platform. It tracks desired and observed state, detects drift, and coordinates reconciliation across Terraform, Bicep, Kubernetes, PowerShell, and other tools.

**Design principle:** A StateOps agent is **optional**. Any script or external automation system can integrate using the REST API, SDK, CLI, or webhooks.

## Technology stack

| Area | Decision | Notes |
| --- | --- | --- |
| Backend / API | **Python 3.12+ / FastAPI** | Async REST API and control plane |
| Data models | **Pydantic** | Typed validation and API schemas |
| Reconciliation | **Python / asyncio** | Provider-independent scheduling and orchestration |
| State store | **etcd** | Key-value state, prefix watches, transactions, leases and locks |
| Messaging (MVP) | **etcd watches** | Signal state changes; durable jobs need explicit lifecycle/claim logic |
| Messaging (later) | **NATS / JetStream** | Durable queues and pub/sub if needed |
| Log storage (MVP) | **Structured JSONL files** | Mounted persistent volume; keep bulk logs out of etcd |
| Log storage (later) | **Azure Blob / S3 / MinIO** | Object storage behind a `LogStore` interface |
| Observability | **OpenTelemetry** | Vendor-neutral export to Splunk, Elastic, New Relic, etc. |
| Live UI logs | **Server-Sent Events (SSE)** | Stream execution output to browser |
| Frontend | **React / TypeScript** | Argo CD-inspired interface |
| Remote agent | **Optional; Go candidate** | Outbound-only execution where useful, not required |
| Testing | **pytest / httpx** | Unit and API tests |
| Packaging | **Docker** | Docker Compose initially; Helm later |

## High-level architecture

```text
                 React / TypeScript UI
                         |
                    REST / SSE
                         |
               Python / FastAPI API
                         |
          Reconciliation Controller
              /          |          \
         StateStore   Scheduler   LogStore
             |           |           |
            etcd     Execution     JSONL files
                       adapters    / object store
                          |
          +---------------+----------------+
          |               |                |
       Local/SDK       Webhook/API     Optional agent
          |               |                |
       Terraform       CI/CD tools       Private networks
       Bicep           Scripts           Custom executors
       Kubernetes
       PowerShell
```

## Core interfaces

- **`StateStore`** — `get`, `put`, `delete`, `list`, `watch`; etcd-backed in the initial implementation.
- **`Reconciler`** — `observe`, `compare`, `plan`, `apply`, `verify` (capabilities may vary by provider).
- **`Executor`** — decides *where and how* an action runs: local, webhook, pipeline, SDK, or optional agent.
- **`LogStore`** — write, read, stream and search run logs; files first, object storage later.

## MVP scope

1. FastAPI service with `/health`, OpenAPI/Swagger, and tests.
2. Resource models for desired state, observed state, drift and reconciliation status.
3. Storage abstraction and etcd implementation with prefix watching.
4. Reconciliation scheduler with deduplication and safe job claiming.
5. REST integration for external scripts; no mandatory agent.
6. Structured run logs, basic search, and live SSE streaming.
7. React UI for resource status, reconciliation history and logs.

## Deferred decisions

- NATS/JetStream until durable messaging requirements justify it.
- Go agent and CLI until the agent protocol and REST API are stable.
- Object storage and Helm deployment until needed.
- Provider-specific semantics for Terraform, Bicep, Kubernetes and arbitrary scripts will be defined as the reconciliation contract evolves.

## Architecture guardrails

- **etcd holds small control-plane records**, not large logs, plans or artifacts.
- **Watches are notifications, not a durable work queue**; reconcile from persisted state and handle watch reconnects/revisions.
- **Prevent concurrent reconciliation** of the same resource using leases/atomic claims.
- **Keep storage and execution pluggable**; do not couple the reconciliation engine to an agent or specific provider.
- **Do not store secrets in plain etcd values or logs**; use references to external secret stores and redact sensitive output.
