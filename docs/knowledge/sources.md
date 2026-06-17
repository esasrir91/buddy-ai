# Knowledge Sources

A **knowledge source** is a concrete `AgentKnowledge` subclass that knows how to
ingest one kind of input. Each lives in its own module under `buddy.knowledge`
and ships with a default reader, so you only provide the source (a `path`,
`urls`, `queries`, `topics`, …) and a `vector_db`.

!!! note "Verified class names"
    These names were read from `buddy/knowledge/`. Note `UrlKnowledge` (not
    `UrlKnowledgeBase`) and the lowercase `irag`. The base class
    `AgentKnowledge` is importable as `from buddy.knowledge import AgentKnowledge`.

## File-based sources

| Source | Import | Class | Main field |
|--------|--------|-------|------------|
| PDF | `from buddy.knowledge.pdf import PDFKnowledgeBase` | `PDFKnowledgeBase` | `path` |
| Text | `from buddy.knowledge.text import TextKnowledgeBase` | `TextKnowledgeBase` | `path` |
| CSV | `from buddy.knowledge.csv import CSVKnowledgeBase` | `CSVKnowledgeBase` | `path` |
| JSON | `from buddy.knowledge.json import JSONKnowledgeBase` | `JSONKnowledgeBase` | `path` |
| DOCX | `from buddy.knowledge.docx import DocxKnowledgeBase` | `DocxKnowledgeBase` | `path` |
| Markdown | `from buddy.knowledge.markdown import MarkdownKnowledgeBase` | `MarkdownKnowledgeBase` | `path` |
| PDF bytes | `from buddy.knowledge.pdf_bytes import PDFBytesKnowledgeBase` | `PDFBytesKnowledgeBase` | `pdfs` |

## Web & URL sources

| Source | Import | Class | Main field |
|--------|--------|-------|------------|
| URL | `from buddy.knowledge.url import UrlKnowledge` | `UrlKnowledge` | `urls` |
| Website (crawl) | `from buddy.knowledge.website import WebsiteKnowledgeBase` | `WebsiteKnowledgeBase` | `urls` |
| PDF URL | `from buddy.knowledge.pdf_url import PDFUrlKnowledgeBase` | `PDFUrlKnowledgeBase` | `urls` |
| CSV URL | `from buddy.knowledge.csv_url import CSVUrlKnowledgeBase` | `CSVUrlKnowledgeBase` | `urls` |
| Firecrawl | `from buddy.knowledge.firecrawl import FireCrawlKnowledgeBase` | `FireCrawlKnowledgeBase` | `urls` |

## Research & media sources

| Source | Import | Class | Main field |
|--------|--------|-------|------------|
| arXiv | `from buddy.knowledge.arxiv import ArxivKnowledgeBase` | `ArxivKnowledgeBase` | `queries` |
| Wikipedia | `from buddy.knowledge.wikipedia import WikipediaKnowledgeBase` | `WikipediaKnowledgeBase` | `topics` |
| YouTube | `from buddy.knowledge.youtube import YouTubeKnowledgeBase` | `YouTubeKnowledgeBase` | `urls` |

## Composite & integration sources

| Source | Import | Class | Notes |
|--------|--------|-------|-------|
| Combined | `from buddy.knowledge.combined import CombinedKnowledgeBase` | `CombinedKnowledgeBase` | `sources: List[AgentKnowledge]` |
| Documents | `from buddy.knowledge.document import DocumentKnowledgeBase` | `DocumentKnowledgeBase` | In-memory `Document`s |
| LangChain | `from buddy.knowledge.langchain import LangChainKnowledgeBase` | `LangChainKnowledgeBase` | Wraps a LangChain retriever/vectorstore |
| LlamaIndex | `from buddy.knowledge.llamaindex import LlamaIndexKnowledgeBase` | `LlamaIndexKnowledgeBase` | Wraps a LlamaIndex `retriever` |
| LightRAG | `from buddy.knowledge.light_rag import LightRagKnowledgeBase` | `LightRagKnowledgeBase` | Talks to a LightRAG server |
| iRAG | `from buddy.knowledge import irag` | `irag` | Local SQLite RAG — see [RAG](rag.md) |

## Examples

=== "PDF file"

    ```python
    from buddy.knowledge.pdf import PDFKnowledgeBase
    from buddy.vectordb.chroma import ChromaDb

    kb = PDFKnowledgeBase(path="docs/handbook.pdf",
                          vector_db=ChromaDb(collection="handbook"))
    kb.load()
    ```

=== "Website"

    ```python
    from buddy.knowledge.website import WebsiteKnowledgeBase
    from buddy.vectordb.chroma import ChromaDb

    kb = WebsiteKnowledgeBase(
        urls=["https://example.com/docs"],
        max_depth=3, max_links=10,
        vector_db=ChromaDb(collection="site"),
    )
    kb.load()
    ```

=== "Wikipedia"

    ```python
    from buddy.knowledge.wikipedia import WikipediaKnowledgeBase
    from buddy.vectordb.chroma import ChromaDb

    kb = WikipediaKnowledgeBase(topics=["Quantum computing"],
                                vector_db=ChromaDb(collection="wiki"))
    kb.load()
    ```

=== "Combined"

    ```python
    from buddy.knowledge.combined import CombinedKnowledgeBase

    kb = CombinedKnowledgeBase(sources=[pdf_kb, website_kb], vector_db=shared_db)
    kb.load()
    ```

!!! tip "Optional dependencies"
    Some sources pull in extra packages — e.g. `WikipediaKnowledgeBase` requires
    `wikipedia`, `LlamaIndexKnowledgeBase` requires `llama-index-core`, and
    `FireCrawlKnowledgeBase` requires the Firecrawl client. A missing dependency
    raises an `ImportError` on import.
