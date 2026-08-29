import json
from os import getenv
from typing import Any, Dict, List, Optional

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class YouTubeTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        **kwargs,
    ):
        """Initialize YouTube Tools.

        Args:
            api_key (Optional[str]): YouTube Data API key
            client_id (Optional[str]): OAuth client ID
            client_secret (Optional[str]): OAuth client secret
            refresh_token (Optional[str]): OAuth refresh token
        """
        self.api_key = api_key or getenv("YOUTUBE_API_KEY")
        self.client_id = client_id or getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = client_secret or getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = refresh_token or getenv("YOUTUBE_REFRESH_TOKEN")
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.access_token = None

        tools: List[Any] = [
            self.search_videos,
            self.get_video_details,
            self.get_channel_info,
            self.upload_video,
            self.get_playlist,
            self.get_comments,
        ]

        super().__init__(name="youtube", tools=tools, **kwargs)

    def _get_access_token(self) -> Optional[str]:
        """Get access token using refresh token."""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return None

        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post("https://oauth2.googleapis.com/token", data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")
            return self.access_token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    def search_videos(self, query: str, max_results: int = 25, order: str = "relevance") -> str:
        """Search for YouTube videos.

        Args:
            query (str): Search query
            max_results (int): Number of results to return
            order (str): Sort order (relevance, date, rating, viewCount, title)

        Returns:
            str: Search results or error message
        """
        if not self.api_key:
            return json.dumps({"error": "API key not provided"})

        try:
            params = {
                "part": "snippet",
                "q": query,
                "maxResults": max_results,
                "order": order,
                "type": "video",
                "key": self.api_key,
            }

            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to search videos: {str(e)}"})

    def get_video_details(self, video_id: str) -> str:
        """Get details for a specific video.

        Args:
            video_id (str): YouTube video ID

        Returns:
            str: Video details or error message
        """
        if not self.api_key:
            return json.dumps({"error": "API key not provided"})

        try:
            params = {"part": "snippet,statistics,contentDetails", "id": video_id, "key": self.api_key}

            response = requests.get(f"{self.base_url}/videos", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get video details: {str(e)}"})

    def get_channel_info(self, channel_id: str) -> str:
        """Get information about a YouTube channel.

        Args:
            channel_id (str): YouTube channel ID

        Returns:
            str: Channel information or error message
        """
        if not self.api_key:
            return json.dumps({"error": "API key not provided"})

        try:
            params = {"part": "snippet,statistics", "id": channel_id, "key": self.api_key}

            response = requests.get(f"{self.base_url}/channels", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get channel info: {str(e)}"})

    def upload_video(self, title: str, description: str, video_file_path: str, tags: Optional[List[str]] = None) -> str:
        """Upload a video to YouTube.

        Args:
            title (str): Video title
            description (str): Video description
            video_file_path (str): Path to video file
            tags (Optional[List[str]]): Video tags

        Returns:
            str: Upload result or error message
        """
        access_token = self._get_access_token()
        if not access_token:
            return json.dumps({"error": "Authentication failed"})

        try:
            metadata = {
                "snippet": {"title": title, "description": description, "tags": tags or []},
                "status": {"privacyStatus": "private"},
            }

            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

            # Note: This is a simplified version. Full video upload requires multipart upload
            # which is more complex and would need additional libraries
            params = {"part": "snippet,status"}

            response = requests.post(f"{self.base_url}/videos", headers=headers, params=params, json=metadata)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to upload video: {str(e)}"})

    def get_playlist(self, playlist_id: str, max_results: int = 50) -> str:
        """Get videos from a YouTube playlist.

        Args:
            playlist_id (str): YouTube playlist ID
            max_results (int): Number of videos to retrieve

        Returns:
            str: Playlist videos or error message
        """
        if not self.api_key:
            return json.dumps({"error": "API key not provided"})

        try:
            params = {"part": "snippet", "playlistId": playlist_id, "maxResults": max_results, "key": self.api_key}

            response = requests.get(f"{self.base_url}/playlistItems", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get playlist: {str(e)}"})

    def get_comments(self, video_id: str, max_results: int = 20) -> str:
        """Get comments for a video.

        Args:
            video_id (str): YouTube video ID
            max_results (int): Number of comments to retrieve

        Returns:
            str: Video comments or error message
        """
        if not self.api_key:
            return json.dumps({"error": "API key not provided"})

        try:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": max_results,
                "order": "relevance",
                "key": self.api_key,
            }

            response = requests.get(f"{self.base_url}/commentThreads", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get comments: {str(e)}"})
