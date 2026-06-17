# Knowledge System

The **Knowledge** layer (`buddy.knowledge`) gives an agent a searchable body of
documents — the retrieval half of Retrieval-Augmented Generation (RAG). A
knowledge base reads source documents, splits them into chunks, embeds those
chunks, and stores the vectors in a vector database so the agent can pull back
relevant passages at query time.

!!! note "Version"
    This page documents buddy-ai **2.2.0**. Every class and parameter below is
    verified against the package source under `buddy/`.

## Architecture

Every knowledge base subclasses `AgentKnowledge` (`buddy.knowledge.agent`) and
composes four pieces:

| Piece | Role | Where |
|-------|------|-------|
| **Reader** | Turns a file/URL/query into `Document` objects | `buddy.document.reader` |
| **Chunking strategy** | Splits a `Document` into smaller chunks | `buddy.document.chunking` |
| **Embedder** | Converts chunk text into vectors | `buddy.embedder` |
| **Vector DB** | Stores and searches the vectors | `buddy.vectordb` |

```python
from buddy.knowledge import AgentKnowledge
```

`AgentKnowledge` exposes the fields `reader`, `vector_db`, `num_documents` (default
`5`), `optimize_on` (default `1000`) and `chunking_strategy`. Concrete subclasses
add source-specific fields such as `path`, `urls`, `queries` or `topics`.

## End-to-end example

The example below ingests a PDF into a Chroma collection and attaches the
knowledge base to an agent. The embedder defaults to `OpenAIEmbedder` when none
is passed to the vector DB.

```python
from buddy import Agent
from buddy.knowledge.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb
from buddy.embedder.openai import OpenAIEmbedder
from buddy.models.openai import OpenAIChat

knowledge = PDFKnowledgeBase(
    path="docs/handbook.pdf",
    vector_db=ChromaDb(
        collection="handbook",
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        persistent_client=True,
    ),
)

# Read, chunk, embed and store. Run once (or when sources change).
knowledge.load(recreate=False)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    search_knowledge=True,   # let the agent search the KB via a tool
)

agent.print_response("Summarize the leave policy.")
```

## How an agent uses knowledge

When an `Agent` (or `Team`) is given a `knowledge` base, two parameters control
how it is consulted:

- **`search_knowledge`** (default `True`) — adds a search tool so the model can
  decide *when* to query the knowledge base. This is **Agentic RAG**.
- **`add_references`** (default `False`) — performs retrieval **before** the
  model runs and injects the matched passages into the prompt (traditional RAG).

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    add_references=True,      # always inject context
    search_knowledge=False,   # disable the search tool
)
```

Both paths ultimately call `AgentKnowledge.search(query, num_documents, filters)`,
which delegates to the vector DB's `search()` method.

## Loading data

`load()` is the entry point for ingestion:

```python
knowledge.load(
    recreate=False,     # drop & rebuild the collection if True
    upsert=False,       # update existing docs (if the vector DB supports it)
    skip_existing=True, # skip documents already stored
)
```

An async variant, `aload(...)`, is available with the same signature.

## Where to go next

- [Knowledge sources](sources.md) — the full catalog of knowledge base classes.
- [Documents & chunking](documents.md) — readers and chunking strategies.
- [Vector databases](vectordb.md) — supported backends and how to swap them.
- [RAG implementation](rag.md) — retrieval flow, filters and `iRAG`.
