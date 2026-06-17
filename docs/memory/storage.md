# Memory Storage

User memories and session summaries are only durable if they are written to a
database. Buddy AI abstracts this behind a `MemoryDb` interface, with concrete
backends you wire to your memory object.

## The `MemoryDb` interface

Both memory layers define an abstract base class `MemoryDb` (an `ABC`) that every
backend implements:

- v1: `buddy.memory.db.base.MemoryDb` (re-exported as `buddy.memory.db.MemoryDb`).
- v2: `buddy.memory.v2.db.base.MemoryDb`.

You generally don't use the base class directly — you instantiate a concrete
backend and pass it as the `db` argument.

## Backends (v1 — `AgentMemory`)

For `AgentMemory`, backends live under `buddy/memory/db/`:

| Class | Module | Backing store |
|-------|--------|---------------|
| `SqliteMemoryDb` | `buddy.memory.db.sqlite` | SQLite |
| `PgMemoryDb` | `buddy.memory.db.postgres` | PostgreSQL |
| `MongoMemoryDb` | `buddy.memory.db.mongodb` | MongoDB |

```python
from buddy.memory.db.sqlite import SqliteMemoryDb
from buddy.memory.db.postgres import PgMemoryDb
from buddy.memory.db.mongodb import MongoMemoryDb

# SQLite — defaults to an in-memory database if no file/url is given
sqlite_db = SqliteMemoryDb(table_name="memory", db_file="memory.db")

# PostgreSQL — table_name is required
pg_db = PgMemoryDb(table_name="memory", db_url="postgresql+psycopg://user:pass@localhost/db")

# MongoDB
mongo_db = MongoMemoryDb(collection_name="memory", db_url="mongodb://localhost:27017", db_name="buddy")
```

`SqliteMemoryDb` resolves its connection in order of precedence: `db_engine`,
then `db_url`, then `db_file`, otherwise a fresh in-memory database.

## Backends (v2 — `Memory`)

The v2 `Memory` object adds Redis and Firestore backends, under
`buddy/memory/v2/db/`:

| Class | Module | Backing store |
|-------|--------|---------------|
| `SqliteMemoryDb` | `buddy.memory.v2.db.sqlite` | SQLite |
| `PostgresMemoryDb` | `buddy.memory.v2.db.postgres` | PostgreSQL |
| `MongoMemoryDb` | `buddy.memory.v2.db.mongodb` | MongoDB |
| `RedisMemoryDb` | `buddy.memory.v2.db.redis` | Redis |
| `FirestoreMemoryDb` | `buddy.memory.v2.db.firestore` | Google Firestore |

```python
from buddy.memory.v2.db.redis import RedisMemoryDb

redis_db = RedisMemoryDb(prefix="BUDDY_memory", host="localhost", port=6379, db=0)
```

!!! note "Two separate `MemoryDb` hierarchies"
    The v1 and v2 backends are distinct classes despite sharing names. Match the
    backend to the memory object you're using — v1 backends with `AgentMemory`,
    v2 backends with the v2 `Memory`.

## Wiring a backend to memory

Attach the `db` to your memory object, then pass that object to the agent.

=== "AgentMemory (v1)"

    ```python
    from buddy.agent import Agent
    from buddy.memory import AgentMemory
    from buddy.memory.db.sqlite import SqliteMemoryDb

    memory = AgentMemory(
        db=SqliteMemoryDb(db_file="memory.db"),
        user_id="dana@example.com",
    )

    agent = Agent(memory=memory, enable_user_memories=True)
    ```

=== "Memory (v2)"

    ```python
    from buddy.agent import Agent
    from buddy.memory.v2.memory import Memory
    from buddy.memory.v2.db.postgres import PostgresMemoryDb

    memory = Memory(
        db=PostgresMemoryDb(
            table_name="memory",
            db_url="postgresql+psycopg://user:pass@localhost/db",
        ),
    )

    agent = Agent(memory=memory, enable_user_memories=True)
    ```

## Choosing a backend

| Backend | Good for |
|---------|----------|
| SQLite | Local development, single-process apps, quick experiments. |
| PostgreSQL | Production, shared/multi-process deployments, durability. |
| MongoDB | Document-oriented stores already in your stack. |
| Redis (v2) | Low-latency access; supports key expiry via `expire`. |
| Firestore (v2) | Serverless / Google Cloud deployments. |

!!! warning "Install the driver"
    Each backend needs its client library — e.g. `sqlalchemy` for SQLite/Postgres,
    `pymongo` for MongoDB, `redis` for Redis. Install the relevant package before
    instantiating the backend.

See [User Memories](user-memories.md) for what gets stored and
[Memory Overview](overview.md) for how storage fits the wider memory system.
