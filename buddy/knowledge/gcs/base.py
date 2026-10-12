from __future__ import annotations

from typing import AsyncIterator, Iterator, List, Optional

try:
    from google.cloud import storage
except ImportError:
    storage = None  # type: ignore[assignment]

from buddy.document import Document
from buddy.knowledge.agent import AgentKnowledge


class GCSKnowledgeBase(AgentKnowledge):
    bucket: Optional[storage.Bucket] = None
    bucket_name: Optional[str] = None
    blob_name: Optional[str] = None
    prefix: Optional[str] = None

    @property
    def gcs_blobs(self) -> List[storage.Blob]:
        if storage is None:
            raise ImportError(
                "The `google-cloud-storage` package is not installed. Please install it via `pip install google-cloud-storage`."
            )
        if self.bucket is None and self.bucket_name is None:
            raise ValueError("No bucket or bucket_name provided")
        if self.bucket is not None and self.bucket_name is not None:
            raise ValueError("Provide either bucket or bucket_name")
        bucket = self.bucket
        if self.bucket_name is not None:
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
        blobs_to_read = []
        if self.blob_name is not None:
            blobs_to_read.append(bucket.blob(self.blob_name))  # type: ignore
        elif self.prefix is not None:
            blobs_to_read.extend(bucket.list_blobs(prefix=self.prefix))  # type: ignore
        else:
            blobs_to_read.extend(bucket.list_blobs())  # type: ignore
        return list(blobs_to_read)

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        raise NotImplementedError

    @property
    def async_document_lists(self) -> AsyncIterator[List[Document]]:
        raise NotImplementedError
