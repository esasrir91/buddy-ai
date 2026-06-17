# Documents & Chunking

Before text can be embedded, it must be **read** into `Document` objects and
**chunked** into passages small enough to embed and retrieve. Both steps live in
`buddy.document`.

!!! note "Pipeline position"
    `reader → chunking strategy → embedder → vector db`. Readers produce
    `Document`s; chunking strategies split each `Document` into a list of smaller
    `Document`s. If no strategy is set, the reader falls back to
    `FixedSizeChunking`.

## Readers

A reader subclasses `Reader` (`buddy.document.reader.base`) — a dataclass with
`chunk=True`, `chunk_size=5000`, a list of `separators`, and an optional
`chunking_strategy`. Each reader implements `read()` / `async_read()` and returns
`List[Document]`.

| Reader | Module | Reads |
|--------|--------|-------|
| `PDFReader`, `PDFImageReader` | `pdf_reader` | Local PDF files |
| `PDFUrlReader`, `PDFUrlImageReader` | `pdf_reader` | PDFs from a URL |
| `TextReader` | `text_reader` | Plain text files |
| `CSVReader`, `CSVUrlReader` | `csv_reader` | CSV files / CSV URLs |
| `DocxReader` | `docx_reader` | Word `.doc` / `.docx` |
| `JSONReader` | `json_reader` | JSON files |
| `MarkdownReader` | `markdown_reader` | Markdown files |
| `URLReader` | `url_reader` | Web pages by URL |
| `WebsiteReader` | `website_reader` | Crawled websites |
| `ArxivReader` | `arxiv_reader` | arXiv search results |
| `YouTubeReader` | `youtube_reader` | YouTube transcripts |
| `FirecrawlReader` | `firecrawl_reader` | Firecrawl scrapes |

```python
from buddy.document.reader import Reader  # base class
```

Most of the time you do not instantiate a reader directly — each knowledge base
ships with a sensible default reader (see [Knowledge sources](sources.md)).

## Chunking strategies

All strategies subclass `ChunkingStrategy`
(`buddy.document.chunking.strategy`) and implement
`chunk(document) -> List[Document]`.

| Strategy | Class | Key parameters | Behavior |
|----------|-------|----------------|----------|
| Fixed | `FixedSizeChunking` | `chunk_size=5000`, `overlap=0` | Fixed-size windows, avoids splitting mid-word |
| Recursive | `RecursiveChunking` | `chunk_size=5000`, `overlap=0` | Splits at natural breakpoints (`\n`, `.`) |
| Document | `DocumentChunking` | `chunk_size=5000`, `overlap=0` | Groups whole paragraphs (`\n\n`) up to the size limit |
| Markdown | `MarkdownChunking` | `chunk_size=5000`, `overlap=0` | Structure-aware split by headers/sections |
| Semantic | `SemanticChunking` | `embedder`, `chunk_size=5000`, `similarity_threshold=0.5` | Embedding-similarity boundaries |
| Agentic | `AgenticChunking` | `model`, `max_chunk_size=5000` | An LLM picks breakpoints |
| Row | `RowChunking` | `skip_header=False`, `clean_rows=True` | One chunk per line/row (tabular data) |

!!! warning "Optional dependencies"
    `SemanticChunking` requires `chonkie` (`pip install chonkie`) and
    `MarkdownChunking` requires `unstructured` (`pip install unstructured markdown`).
    Both raise an `ImportError` on import if the dependency is missing.

## Choosing a strategy

```python
from buddy.knowledge.text import TextKnowledgeBase
from buddy.document.chunking.recursive import RecursiveChunking
from buddy.vectordb.chroma import ChromaDb

knowledge = TextKnowledgeBase(
    path="notes/",
    vector_db=ChromaDb(collection="notes"),
    chunking_strategy=RecursiveChunking(chunk_size=1200, overlap=100),
)
knowledge.load()
```

Setting `chunking_strategy` on the knowledge base propagates it to the reader (an
`AgentKnowledge` validator wires the reader's `chunking_strategy` if it is unset).

## Practical guidance

- **Prose / mixed docs** — `RecursiveChunking` or `DocumentChunking` keep
  sentences and paragraphs intact.
- **Markdown** — `MarkdownChunking` preserves headers and sections.
- **CSV / logs** — `RowChunking` keeps each record addressable.
- **Highest retrieval quality** — `SemanticChunking` groups text by meaning, at
  the cost of extra embedding calls.
- **Maximum control over cost** — `FixedSizeChunking` (the default) is
  deterministic and dependency-free.
