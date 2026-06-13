# Knowledge Management

Give your agent access to a knowledge base for Retrieval-Augmented Generation (RAG).

## iRAG — Built-in RAG (No Vector DB Required)

iRAG is Buddy AI's custom RAG engine using spaCy NLP, TF-IDF, and cosine similarity.

```python
from buddy.knowledge.irag import IRAG
from buddy.knowledge.document.text import TextKnowledgeBase

knowledge = TextKnowledgeBase(
    texts=["Buddy AI supports 35+ LLM providers...", "iRAG uses spaCy NLP..."],
    irag=IRAG(),
)

agent = Agent(knowledge=knowledge, search_knowledge=True)
knowledge.load()
agent.print_response("How does iRAG work?")
```

## PDF Knowledge Base

```python
from buddy.knowledge.document.pdf import PDFKnowledgeBase
from buddy.vectordb.chroma import ChromaDb

knowledge = PDFKnowledgeBase(
    path="docs/manual.pdf",
    vector_db=ChromaDb(collection="manual"),
)
knowledge.load()
```

## Website Knowledge Base

```python
from buddy.knowledge.website import WebsiteKnowledgeBase

knowledge = WebsiteKnowledgeBase(urls=["https://docs.example.com"])
knowledge.load()
```

## Supported Sources

| Source | Class |
|--------|-------|
| Plain text | `TextKnowledgeBase` |
| PDF | `PDFKnowledgeBase` |
| DOCX | `DocxKnowledgeBase` |
| CSV | `CSVKnowledgeBase` |
| JSON | `JSONKnowledgeBase` |
| Markdown | `MarkdownKnowledgeBase` |
| Website / URL | `WebsiteKnowledgeBase` |
| Wikipedia | `WikipediaKnowledgeBase` |
| YouTube | `YouTubeKnowledgeBase` |
| ArXiv | `ArxivKnowledgeBase` |
| AWS S3 | `S3KnowledgeBase` |
| Google Cloud Storage | `GCSKnowledgeBase` |

See [Vector Databases](../knowledge/vectordb.md) for storage backend options.
