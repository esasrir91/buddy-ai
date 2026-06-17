# Knowledge Management

Give an agent a **knowledge base** for Retrieval-Augmented Generation (RAG).
Every knowledge base subclasses `AgentKnowledge` (`buddy.knowledge.agent`),
exposes a `load()` method to ingest content, and a `search()` method the agent
uses to fetch relevant passages.

Attach one with `knowledge=`. The agent searches it automatically when
`search_knowledge=True` (the default).

```python
from buddy import Agent, AgentKnowledge  # AgentKnowledge is the base class
```

## iRAG — Built-in RAG (No Vector DB Required)

iRAG is Buddy AI's self-contained RAG engine (spaCy NLP, TF-IDF, and cosine
similarity over a local SQLite store). The class is `irag` in
`buddy.knowledge.irag`, and it ingests a file or a directory directly — no
vector database or embedder needed.

```python
from buddy import Agent
from buddy.models.openai import OpenAIChat
from buddy.knowledge.irag import irag

knowledge = irag(dir_path="docs/", formats=[".txt", ".md"])
knowledge.load()

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    knowledge=knowledge,
    search_knowledge=True,
)
agent.print_response("How does iRAG work?")
```

!!! tip "Single file vs. directory"
    Pass `file_path="notes.md"` to ingest one file, or `dir_path="docs/"` to
    ingest a folder recursively. Use `strict_kb_mode=True` to force the agent to
    answer only from the knowledge base.

## Vector-DB Knowledge Bases

The format-specific knowledge bases (PDF, text, website, …) store embeddings in
a **vector database**. Provide one via `vector_db`; `ChromaDb`
(`buddy.vectordb.chroma`) takes the collection name as its first argument.

```python
from buddy.knowledge.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

knowledge = PDFKnowledgeBase(
    path="docs/manual.pdf",
    vector_db=ChromaDb(collection="manual"),
)
knowledge.load()   # embeds and indexes the document(s)

agent = Agent(model=OpenAIChat(id="gpt-4o-mini"), knowledge=knowledge)
agent.print_response("Summarize the installation section.")
```

### Plain Text

```python
from buddy.knowledge.text import TextKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

knowledge = TextKnowledgeBase(
    path="docs/",                       # a .txt file or a directory of them
    vector_db=ChromaDb(collection="notes"),
)
knowledge.load()
```

### Website

```python
from buddy.knowledge.website import WebsiteKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

knowledge = WebsiteKnowledgeBase(
    urls=["https://docs.example.com"],
    max_depth=2,
    vector_db=ChromaDb(collection="site"),
)
knowledge.load()
```

!!! note "ChromaDB requires the `chromadb` package"
    `ChromaDb` raises an import error if `chromadb` is not installed
    (`pip install chromadb`). It defaults to `OpenAIEmbedder` when no `embedder`
    is supplied, so an `OPENAI_API_KEY` is needed unless you pass another
    embedder.

## Supported Sources

All classes below subclass `AgentKnowledge` and live under `buddy.knowledge`.

| Source | Class | Import |
|--------|-------|--------|
| Plain text | `TextKnowledgeBase` | `buddy.knowledge.text` |
| PDF | `PDFKnowledgeBase` | `buddy.knowledge.pdf` |
| DOCX | `DocxKnowledgeBase` | `buddy.knowledge.docx` |
| CSV | `CSVKnowledgeBase` | `buddy.knowledge.csv` |
| JSON | `JSONKnowledgeBase` | `buddy.knowledge.json` |
| Markdown | `MarkdownKnowledgeBase` | `buddy.knowledge.markdown` |
| Website / URL | `WebsiteKnowledgeBase` | `buddy.knowledge.website` |
| Wikipedia | `WikipediaKnowledgeBase` | `buddy.knowledge.wikipedia` |
| YouTube | `YouTubeKnowledgeBase` | `buddy.knowledge.youtube` |
| ArXiv | `ArxivKnowledgeBase` | `buddy.knowledge.arxiv` |
| AWS S3 | `S3KnowledgeBase` | `buddy.knowledge.s3.base` |
| Google Cloud Storage | `GCSKnowledgeBase` | `buddy.knowledge.gcs.base` |

## See Also

- [Tools](tools.md) — combine knowledge with live tool calls
- [Memory](memory.md) — durable per-user context
