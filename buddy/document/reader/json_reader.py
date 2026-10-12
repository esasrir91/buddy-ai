import asyncio
import json
from pathlib import Path
from typing import IO, Any, List, Union
from uuid import uuid4

from buddy.document.base import Document
from buddy.document.reader.base import Reader
from buddy.utils.log import log_info


class JSONReader(Reader):
    """Reader for JSON files"""

    def __init__(
        self, chunk: bool = False, chunk_size: int = 5000, chunking_strategy=None
    ) -> None:
        super().__init__(chunk=chunk, chunk_size=chunk_size, chunking_strategy=chunking_strategy)

    def read(self, path: Union[Path, IO[Any]]) -> List[Document]:
        try:
            if isinstance(path, Path):
                if not path.exists():
                    raise FileNotFoundError(f"Could not find file: {path}")
                log_info(f"Reading: {path}")
                json_name = path.stem
                json_contents = json.loads(path.read_text("utf-8"))

            elif hasattr(path, "read"):
                log_info(f"Reading uploaded file: {path.name}")
                json_name = Path(path.name).stem
                path.seek(0)
                raw_contents = path.read()
                if isinstance(raw_contents, bytes):
                    raw_contents = raw_contents.decode("utf-8")
                json_contents = json.loads(raw_contents)

            else:
                raise ValueError("Unsupported file type. Must be Path or BytesIO.")

            if isinstance(json_contents, dict):
                json_contents = [json_contents]
            elif not isinstance(json_contents, list):
                json_contents = [json_contents]

            documents = [
                Document(
                    name=json_name,
                    id=str(uuid4()),
                    meta_data={"page": page_number},
                    content=json.dumps(content),
                )
                for page_number, content in enumerate(json_contents, start=1)
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents
        except Exception:
            raise

    async def async_read(self, path: Union[Path, IO[Any]]) -> List[Document]:
        """Asynchronously read JSON files.

        Args:
            path (Union[Path, IO[Any]]): Path to a JSON file or a file-like object

        Returns:
            List[Document]: List of documents from the JSON file
        """
        return await asyncio.to_thread(self.read, path)
