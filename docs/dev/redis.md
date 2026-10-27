# Redis as a JSON Document Store for FastAPI and Agents

This document summarizes a practical pattern for using Redis as a document database with JSON support, combined with FastAPI validation through Pydantic v2. The goal is to store structured task data, query it efficiently, and use Redis Streams for asynchronous agent processing.

## 1. Why use RedisJSON?

Redis is often treated as a cache, but with RedisJSON and persistence enabled, it can work as a real document database for structured data.

Benefits:

- Native JSON storage for nested structures
- Type-safe validation with Pydantic
- Fast in-memory reads and writes
- Atomic updates to individual fields inside a document
- Search and indexing support via RediSearch
- Persistence using AOF to protect data across restarts

---

## 2. Enabling disk persistence

For a production-like setup, enable AOF persistence in your Memurai/Redis configuration.

```ini
# Enable append-only file persistence
appendonly yes

# Flush to disk once per second
appendfsync everysec
```

Once enabled, Redis can safely keep JSON documents even after restarts or outages.

---

## 3. Defining the data model with Pydantic v2

A task payload can be validated before it ever reaches Redis.

```python
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class TaskTarget(BaseModel):
    host_ip: str
    os_platform: str = Field(description="Target OS like windows, linux")


class JobPayload(BaseModel):
    job_id: str
    command: str
    arguments: List[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)
    target: TaskTarget
    created_by: Optional[EmailStr] = None
```

This gives you:

- automatic validation on incoming HTTP payloads
- strong typing for the application layer
- an easy way to convert to native JSON dictionaries using `model_dump()`

---

## 4. FastAPI integration with RedisJSON

This example validates a request and stores the task directly as a JSON document.

```python
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, status

from pydantic import BaseModel

app = FastAPI()

redis_pool = aioredis.ConnectionPool(
    host="localhost",
    port=6379,
    decode_responses=True,
)
r = aioredis.Redis(connection_pool=redis_pool)


class TaskTarget(BaseModel):
    host_ip: str
    os_platform: str


class JobPayload(BaseModel):
    job_id: str
    command: str
    arguments: list[str] = []
    timeout_seconds: int = 300
    target: TaskTarget


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(payload: JobPayload):
    db_key = f"task:{payload.job_id}"

    try:
        native_dict = payload.model_dump()
        await r.json().set(db_key, "$", native_dict)

        return {
            "status": "stored",
            "key": db_key,
            "job_id": payload.job_id,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database write failed: {str(exc)}",
        )


@app.get("/tasks/{job_id}", response_model=JobPayload)
async def get_task_by_id(job_id: str):
    db_key = f"task:{job_id}"
    raw_doc = await r.json().get(db_key, "$")

    if not raw_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested job profile could not be found.",
        )

    actual_data = raw_doc[0]
    return JobPayload.model_validate(actual_data)
```

Notes:

- `payload.model_dump()` converts the Pydantic object to a native dictionary
- `r.json().set(key, "$", value)` writes the JSON document at the root path
- returning `JobPayload.model_validate(...)` rehydrates the structure safely

---

## 5. Updating only part of a JSON document

RedisJSON supports direct field-level changes without rewriting the entire object.

```python
await r.json().set(f"task:{job_id}", "$.timeout_seconds", 600)
```

This is useful when you need to adjust task metadata without re-saving the whole document.

---

## 6. JSON examples with Python

The async Redis client supports JSON operations directly.

```python
import asyncio
import redis.asyncio as aioredis


async def main():
    r = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    user_profile = {
        "name": "Nikolay",
        "age": 45,
        "skills": ["Python", "Azure", "DevOps"],
        "is_active": True,
        "address": {
            "city": "Brisbane",
            "country": "Australia",
        },
    }

    await r.json().set("user:101", "$", user_profile)

    await r.json().set("user:101", "$.age", 46)
    await r.json().arrappend("user:101", "$.skills", "Terraform")

    result = await r.json().get("user:101", "$.name", "$.skills")
    print(result)

    await r.close()


if __name__ == "__main__":
    asyncio.run(main())
```

This pattern is similar to storing documents in MongoDB, but with Redis speed and direct field-level updates.

---

## 7. Search and indexing with RediSearch

If you need search across JSON values, create an index over relevant fields.

```python
from redis.commands.search.field import TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType


async def setup_search_index(r):
    schema = (
        TextField("$.name", as_name="name"),
        NumericField("$.age", as_name="age"),
        TextField("$.address.city", as_name="city"),
    )

    try:
        await r.ft("idx:users").create_index(
            fields=schema,
            definition=IndexDefinition(prefix=["user:"], index_type=IndexType.JSON),
        )
        print("[✓] Search index created.")
    except Exception as exc:
        print("[!] Index already exists or failed:", exc)
```

A search example:

```python
# result = await r.ft("idx:users").search("@city:Brisbane @age:[40 INF]")
```

This enables queries like “all users in Brisbane older than 40”.

---

## 8. Long polling with Redis Streams and FastAPI

For agent-based systems, Redis Streams can be used to fan out tasks to workers while keeping the API responsive.

```python
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
redis_pool = aioredis.ConnectionPool(host="localhost", port=6379, decode_responses=True)
r = aioredis.Redis(connection_pool=redis_pool)

STREAM_NAME = "tasks_stream"
GROUP_NAME = "agents_group"


@app.on_event("startup")
async def startup_event():
    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except aioredis.exceptions.ResponseError:
        pass


class AckRequest(BaseModel):
    task_id: str


@app.get("/get-task")
async def get_task(agent_id: str):
    try:
        response = await r.xreadgroup(
            groupname=GROUP_NAME,
            consumername=agent_id,
            streams={STREAM_NAME: ">"},
            count=1,
            block=20000,
        )

        if not response:
            return {"status": "no_tasks"}

        stream_name, messages = response[0]
        message_id, payload = messages[0]

        return {
            "status": "success",
            "task_id": message_id,
            "data": payload,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ack-task")
async def ack_task(body: AckRequest):
    try:
        await r.xack(STREAM_NAME, GROUP_NAME, body.task_id)
        return {"status": "confirmed"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

This pattern uses long polling so agents can wait efficiently for available work without blocking the server thread pool.

---

## 9. Example agent in Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

const (
    apiURL  = "http://localhost:8000"
    agentID = "go_agent_01"
)

type APIResponse struct {
    Status string                 `json:"status"`
    TaskID string                 `json:"task_id"`
    Data   map[string]interface{} `json:"data"`
}

func main() {
    client := &http.Client{Timeout: 30 * time.Second}

    for {
        url := fmt.Sprintf("%s/get-task?agent_id=%s", apiURL, agentID)
        resp, err := client.Get(url)
        if err != nil {
            fmt.Println("[!] Network error, retrying in 5 seconds:", err)
            time.Sleep(5 * time.Second)
            continue
        }

        var res APIResponse
        json.NewDecoder(resp.Body).Decode(&res)
        resp.Body.Close()

        if res.Status == "no_tasks" {
            continue
        }

        if res.Status == "success" {
            fmt.Printf("[~] Task %s received: %v\n", res.TaskID, res.Data)
            time.Sleep(1 * time.Second)

            ackBody, _ := json.Marshal(map[string]string{"task_id": res.TaskID})
            ackResp, err := client.Post(apiURL+"/ack-task", "application/json", bytes.NewBuffer(ackBody))
            if err == nil {
                fmt.Printf("[✓] Task %s acknowledged\n", res.TaskID)
                ackResp.Body.Close()
            }
        }
    }
}
```

---

## 10. Example agent in PowerShell

```powershell
$ApiUrl = "http://localhost:8000"
$AgentId = "win_agent_01"

Write-Host "[*] Agent $AgentId started..." -ForegroundColor Cyan

while ($true) {
    try {
        $Response = Invoke-RestMethod -Uri "$ApiUrl/get-task?agent_id=$AgentId" -Method Get -TimeoutSec 30

        if ($Response.status -eq "no_tasks") {
            continue
        }

        if ($Response.status -eq "success") {
            $TaskId = $Response.task_id
            Write-Host "[~] Task $TaskId received: $($Response.data | ConvertTo-Json -Compress)" -ForegroundColor Yellow

            Start-Sleep -Seconds 1

            $AckBody = @{ task_id = $TaskId } | ConvertTo-Json
            $AckResponse = Invoke-RestMethod -Uri "$ApiUrl/ack-task" -Method Post -Body $AckBody -ContentType "application/json"

            if ($AckResponse.status -eq "confirmed") {
                Write-Host "[✓] Task $TaskId completed and acknowledged!" -ForegroundColor Green
            }
        }
    }
    catch {
        Write-Host "[!] Request error: $_. Retrying in 5 seconds..." -ForegroundColor Red
        Start-Sleep -Seconds 5
    }
}
```

---

## 11. Key advantages of this architecture

- Speed: Redis keeps data in memory for extremely fast access.
- Flexibility: nested JSON documents can be stored without rigid schemas.
- Validation: FastAPI + Pydantic ensures invalid payloads are rejected early.
- Atomic updates: individual fields can be changed without rewriting the full record.
- Reliability: AOF persistence allows Redis to function as a durable data store.
- Scalability: Streams and consumer groups support distributed task processing.

---

## 12. Recommended next step

A strong next step is to combine this pattern with Pydantic validation and Redis Streams so that a submitted task is both stored as JSON and published to a queue in the same workflow.

This creates a clean pipeline:

1. Accept an agent request via FastAPI
2. Validate it using Pydantic
3. Save it as JSON in Redis
4. Publish the task ID to a Redis Stream
5. Let a worker agent consume and execute it
6. Send an acknowledgment after completion

This design is a solid foundation for queue-driven automation and document-based task orchestration.
