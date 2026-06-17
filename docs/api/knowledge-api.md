# Knowledge API

Knowledge bases give agents retrieval-augmented context. `AgentKnowledge`
(`buddy.knowledge.agent`, re-exported as `from buddy import AgentKnowledge`) is
the base class; concrete subclasses load documents from PDFs, URLs, text, and
more, and index them into a vector database.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.knowledge.url import UrlKnowledge
from buddy.vectordb.chroma import ChromaDb

knowledge = UrlKnowledge(
    urls=["https://example.com/docs"],
    vector_db=ChromaDb(collection="docs"),
)
knowledge.load()  # read, chunk, embed, and index the documents

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    knowledge=knowledge,
    search_knowledge=True,
)
agent.print_response("Summarize the documentation.")
```

## AgentKnowledge

The base class holds the vector store, reader, and chunking configuration.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reader` | `Reader` | `None` | Reads source documents (PDF, URL, text, ...). |
| `vector_db` | `VectorDb` | `None` | Where embeddings are stored and searched. |
| `num_documents` | `int` | `5` | Number of results returned per search. |
| `optimize_on` | `int` | `1000` | Document count at which the vector DB is optimized. |
| `chunking_strategy` | `ChunkingStrategy` | `None` | How documents are split (defaults to fixed-size). |

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `load` | `load(recreate=False, upsert=False, skip_existing=True)` | Read, chunk, embed, and index the knowledge base. |
| `search` | `search(query, num_documents=None, filters=None) -> list[Document]` | Return documents relevant to `query`. |
| `async_search` | `async_search(query, num_documents=None, filters=None)` | Async version of `search`. |

!!! note "`load()` populates the vector DB"
    Call `load()` once before querying (or after adding documents). Pass
    `recreate=True` to drop and rebuild the collection, or `upsert=True` to
    update existing entries instead of inserting duplicates.

## Knowledge base classes

| Class | Module | Key parameters |
|-------|--------|----------------|
| `PDFKnowledgeBase` | `buddy.knowledge.pdf` | `path` (file, directory, or list of `{path, password, metadata}`) |
| `UrlKnowledge` | `buddy.knowledge.url` | `urls: list[str]` |
| `TextKnowledgeBase` | `buddy.knowledge.text` | `path` (`.txt` file or directory) |

Each subclass sets a sensible default `reader` (e.g. `PDFReader`, `URLReader`,
`TextReader`) and inherits `load()` / `search()` from `AgentKnowledge`.

=== "PDF"

    ```python
    from buddy.knowledge.pdf import PDFKnowledgeBase
    from buddy.vectordb.chroma import ChromaDb

    kb = PDFKnowledgeBase(
        path="docs/handbook.pdf",
        vector_db=ChromaDb(collection="handbook"),
    )
    kb.load()
    ```

=== "URL"

    ```python
    from buddy.knowledge.url import UrlKnowledge
    from buddy.vectordb.chroma import ChromaDb

    kb = UrlKnowledge(
        urls=["https://example.com/a", "https://example.com/b"],
        vector_db=ChromaDb(collection="web"),
    )
    kb.load()
    ```

=== "Text"

    ```python
    from buddy.knowledge.text import TextKnowledgeBase
    from buddy.vectordb.chroma import ChromaDb

    kb = TextKnowledgeBase(
        path="notes/",  # a .txt file or a directory of .txt files
        vector_db=ChromaDb(collection="notes"),
    )
    kb.load()
    ```

## Vector databases

Vector stores live under `buddy.vectordb.*`. For example, `ChromaDb`
(`buddy.vectordb.chroma`):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection` | `str` | — (required) | Collection name. |
| `embedder` | `Embedder` | `OpenAIEmbedder()` | Embedding model (defaults to OpenAI). |
| `distance` | `Distance` | `Distance.cosine` | Similarity metric. |
| `path` | `str` | `"tmp/chromadb"` | Storage path for the persistent client. |
| `persistent_client` | `bool` | `False` | Persist to disk instead of in-memory. |

!!! tip "Filtered retrieval"
    Pass `knowledge_filters={...}` to `Agent.run()` / `Team.run()`, or
    `filters=` to `search()`, to restrict retrieval by document metadata.
