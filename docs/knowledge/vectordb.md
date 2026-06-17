# Vector Databases

A **vector database** stores chunk embeddings and answers similarity queries.
Every backend subclasses `VectorDb` (`buddy.vectordb.base`) and implements a
common interface — `create()`, `insert()`, `upsert()`, `search()`, `drop()`,
`exists()` (plus `async_*` variants) — so backends are interchangeable.

```python
from buddy.vectordb import VectorDb
```

!!! note "Verified class names"
    The classes below were read directly from `buddy/vectordb/<provider>/`. Note
    the non-obvious casing: `ChromaDb`, `MongoDb`, `PineconeDb`, `PgVector`,
    `UpstashVectorDb`, and `CouchbaseSearch`.

## Supported backends

| Provider | Import | Class |
|----------|--------|-------|
| Chroma | `from buddy.vectordb.chroma import ChromaDb` | `ChromaDb` |
| PgVector | `from buddy.vectordb.pgvector import PgVector` | `PgVector` |
| Qdrant | `from buddy.vectordb.qdrant import Qdrant` | `Qdrant` |
| Pinecone | `from buddy.vectordb.pineconedb import PineconeDb` | `PineconeDb` |
| Milvus | `from buddy.vectordb.milvus import Milvus` | `Milvus` |
| MongoDB | `from buddy.vectordb.mongodb import MongoDb` | `MongoDb` |
| Weaviate | `from buddy.vectordb.weaviate import Weaviate` | `Weaviate` |
| Cassandra | `from buddy.vectordb.cassandra import Cassandra` | `Cassandra` |
| ClickHouse | `from buddy.vectordb.clickhouse import Clickhouse` | `Clickhouse` |
| Couchbase | `from buddy.vectordb.couchbase import CouchbaseSearch` | `CouchbaseSearch` |
| SingleStore | `from buddy.vectordb.singlestore import SingleStore` | `SingleStore` |
| SurrealDB | `from buddy.vectordb.surrealdb import SurrealDb` | `SurrealDb` |
| Upstash | `from buddy.vectordb.upstashdb import UpstashVectorDb` | `UpstashVectorDb` |

Each provider also requires its own client library (e.g. `pip install chromadb`,
`pip install qdrant-client`); the module raises an `ImportError` describing the
missing package.

## ChromaDb example

`ChromaDb`'s first positional argument is the `collection` name. An embedder is
optional — if omitted it defaults to `OpenAIEmbedder`.

```python
from buddy.vectordb.chroma import ChromaDb
from buddy.embedder.openai import OpenAIEmbedder
from buddy.vectordb.distance import Distance

vector_db = ChromaDb(
    collection="handbook",
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    distance=Distance.cosine,
    path="tmp/chromadb",
    persistent_client=True,   # persist to disk at `path`
)
```

Attach it to any knowledge base:

```python
from buddy.knowledge.pdf import PDFKnowledgeBase

knowledge = PDFKnowledgeBase(path="docs/handbook.pdf", vector_db=vector_db)
knowledge.load()
```

## Swapping backends

Because every backend implements the same `VectorDb` interface, switching is a
one-line change — only the constructor arguments differ.

=== "Qdrant"

    ```python
    from buddy.vectordb.qdrant import Qdrant

    vector_db = Qdrant(collection="handbook", url="http://localhost:6333")
    ```

=== "PgVector"

    ```python
    from buddy.vectordb.pgvector import PgVector

    vector_db = PgVector(table_name="handbook", db_url="postgresql+psycopg://...")
    ```

=== "Pinecone"

    ```python
    from buddy.vectordb.pineconedb import PineconeDb

    vector_db = PineconeDb(name="handbook", dimension=1536, api_key="...")
    ```

!!! tip "Verify constructor arguments"
    Constructor signatures vary per provider. Read the class in
    `buddy/vectordb/<provider>/` to confirm the exact arguments (collection vs.
    table name, connection URL, index parameters such as `HNSW`/`Ivfflat`) before
    deploying.

## Search interface

`VectorDb.search(query, limit=5, filters=None)` returns a `List[Document]`.
Knowledge bases call this for you via `AgentKnowledge.search()`; you rarely call
it directly. Some backends additionally expose `vector_search`, `keyword_search`
and `hybrid_search`, selectable through a `SearchType` (`buddy.vectordb.search`)
where supported.
