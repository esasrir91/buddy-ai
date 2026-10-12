from typing import Iterator, List

from pydantic import Field

from buddy.document import Document
from buddy.knowledge.agent import AgentKnowledge

try:
    import wikipedia
except ImportError:
    wikipedia = None  # type: ignore[assignment]


class WikipediaKnowledgeBase(AgentKnowledge):
    topics: List[str] = Field(default_factory=list)
    auto_suggest: bool = True

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterate over urls and yield lists of documents.
        Each object yielded by the iterator is a list of documents.

        Returns:
            Iterator[List[Document]]: Iterator yielding list of documents
        """

        if wikipedia is None:
            raise ImportError("The `wikipedia` package is not installed. Please install it via `pip install wikipedia`.")

        for topic in self.topics:
            yield [
                Document(
                    name=topic,
                    meta_data={"topic": topic},
                    content=wikipedia.summary(topic, auto_suggest=self.auto_suggest),
                )
            ]
