# Statefy — Redis State Store (first iteration)

This example keeps Redis access separate from FastAPI endpoints. It works with a local Memurai instance using standard Redis commands; **RedisJSON is not required**.

## 1. Install the Python client

From the `backend` directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install redis
```

Add `redis` to `backend/requirements.txt` so GitHub Actions installs it too.

## 2. Create `app/storage/redis_store.py`

```python
import json
from typing import Any

import redis.asyncio as redis


class RedisStateStore:
    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        self.client = redis.from_url(url, decode_responses=True)

    @staticmethod
    def _key(resource_id: str) -> str:
        if not resource_id or any(c in resource_id for c in ("/", "\\", "*", "?", "[", "]")):
            raise ValueError("Invalid resource ID")
        return f"statefy:resources:{resource_id}"

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def save(self, resource_id: str, state: dict[str, Any]) -> None:
        payload = json.dumps(state)
        await self.client.set(self._key(resource_id), payload)

    async def get(self, resource_id: str) -> dict[str, Any] | None:
        payload = await self.client.get(self._key(resource_id))
        return json.loads(payload) if payload is not None else None

    async def delete(self, resource_id: str) -> bool:
        return bool(await self.client.delete(self._key(resource_id)))

    async def close(self) -> None:
        await self.client.aclose()
```

**How it works:**

- `redis.asyncio` uses nonblocking calls, which fit FastAPI's async endpoints.
- Each resource is stored under `statefy:resources:<id>` as a JSON-encoded string.
- `save()` creates or replaces a resource; `get()` returns a Python dictionary or `None`; `delete()` returns whether the key existed.
- `decode_responses=True` returns strings rather than raw bytes.
- `close()` releases the client's connections.

## 3. Quick standalone test

Create `backend/try_redis.py`:

```python
import asyncio

from app.storage.redis_store import RedisStateStore


async def main() -> None:
    store = RedisStateStore()
    try:
        print("Connected:", await store.ping())
        await store.save("demo-1", {
            "provider": "terraform",
            "desired_state": {"region": "australiaeast"},
            "status": "unknown",
        })
        print("Resource:", await store.get("demo-1"))
        print("Deleted:", await store.delete("demo-1"))
    finally:
        await store.close()


asyncio.run(main())
```

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe try_redis.py
```

## 4. Use from FastAPI

For a quick demonstration, `app/api/resources.py` could use the store like this:

```python
from fastapi import APIRouter, HTTPException

from app.storage.redis_store import RedisStateStore

router = APIRouter(prefix="/resources", tags=["Resources"])
store = RedisStateStore()  # Demo only: manage lifetime at application startup later.


@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    resource = await store.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource
```

With the `/api/v1` prefix registered in `main.py`, this becomes `GET /api/v1/resources/{resource_id}`.

## 5. Important next steps

This is intentionally a **minimal prototype**, not a production-ready StateStore:

- `SET` replaces the entire JSON document; it does not perform partial RedisJSON updates.
- Add Pydantic validation using your existing `Resource` model before accepting API input.
- Add optimistic concurrency (revision checks) so two writers cannot silently overwrite one another.
- Avoid `KEYS` for listing resources at scale; design indexed/paginated queries instead.
- Manage the Redis connection through FastAPI's application lifespan and configuration (rather than a module-level global).
- Add authentication/TLS for remote Redis; `localhost:6379` is only for local development.
- Redis persistence must be configured separately if it is the source of truth.

**Suggested next milestone:** implement `StateStore` as a protocol, then adapt `RedisStateStore` to accept and return your `Resource` Pydantic model. Keep job-queue operations in a separate `JobStore` interface.
