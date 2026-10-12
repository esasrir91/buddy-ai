import asyncio
from typing import List
from urllib.parse import parse_qs, urlparse

from buddy.document.base import Document
from buddy.document.reader.base import Reader
from buddy.utils.log import log_debug, log_info, logger

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    raise ImportError(
        "`youtube_transcript_api` not installed. Please install it via `pip install youtube_transcript_api`."
    )


class YouTubeReader(Reader):
    """Reader for YouTube video transcripts"""

    @staticmethod
    def _extract_video_id(video_url: str) -> str:
        if not video_url:
            raise ValueError("No YouTube URL or video ID provided")

        parsed_url = urlparse(video_url)
        if parsed_url.hostname in {"youtu.be", "www.youtu.be"}:
            video_id = parsed_url.path.strip("/").split("/")[0]
        elif parsed_url.hostname and parsed_url.hostname.endswith("youtube.com"):
            video_id = parse_qs(parsed_url.query).get("v", [""])[0]
            if not video_id:
                path_parts = parsed_url.path.strip("/").split("/")
                video_id = path_parts[1] if len(path_parts) > 1 and path_parts[0] in {"shorts", "embed"} else ""
        else:
            video_id = video_url.strip()

        if not video_id:
            raise ValueError(f"Could not extract a YouTube video ID from: {video_url}")
        return video_id

    def read(self, video_url: str) -> List[Document]:
        try:
            # Extract video ID from URL
            video_id = self._extract_video_id(video_url)
            log_info(f"Reading transcript for video: {video_id}")

            # Get transcript
            log_debug(f"Fetching transcript for video: {video_id}")
            # Create an instance of YouTubeTranscriptApi
            ytt_api = YouTubeTranscriptApi()
            transcript_data = ytt_api.fetch(video_id)

            # Combine transcript segments into full text
            transcript_text = ""

            for segment in transcript_data:
                transcript_text += f"{segment.text} "

            documents = [
                Document(
                    name=f"youtube_{video_id}",
                    id=f"youtube_{video_id}",
                    meta_data={"video_url": video_url, "video_id": video_id},
                    content=transcript_text.strip(),
                )
            ]

            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document))
                return chunked_documents
            return documents

        except Exception as e:
            logger.error(f"Error reading transcript for {video_url}: {e}")
            return []

    async def async_read(self, video_url: str) -> List[Document]:
        return await asyncio.get_event_loop().run_in_executor(None, self.read, video_url)
