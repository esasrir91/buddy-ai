import json
from typing import Any, Dict, List, Optional
from os import getenv

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class InstagramTools(Toolkit):
    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Instagram Tools.

        Args:
            access_token (Optional[str]): Instagram access token
            user_id (Optional[str]): Instagram user ID
        """
        self.access_token = access_token or getenv("INSTAGRAM_ACCESS_TOKEN")
        self.user_id = user_id or getenv("INSTAGRAM_USER_ID")
        self.base_url = "https://graph.instagram.com"

        tools: List[Any] = [
            self.post_photo,
            self.get_media,
            self.get_insights,
            self.get_hashtags,
            self.post_story,
        ]

        super().__init__(name="instagram", tools=tools, **kwargs)

    def post_photo(self, image_url: str, caption: Optional[str] = None) -> str:
        """Post a photo to Instagram.

        Args:
            image_url (str): URL of the image to post
            caption (Optional[str]): Photo caption

        Returns:
            str: Post result or error message
        """
        if not all([self.access_token, self.user_id]):
            return json.dumps({"error": "Access token and user ID not provided"})

        try:
            # First, create media object
            create_data = {
                "image_url": image_url,
                "access_token": self.access_token
            }

            if caption:
                create_data["caption"] = caption

            create_response = requests.post(
                f"{self.base_url}/{self.user_id}/media",
                data=create_data
            )
            create_response.raise_for_status()
            creation_id = create_response.json()["id"]

            # Then, publish the media
            publish_data = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }

            publish_response = requests.post(
                f"{self.base_url}/{self.user_id}/media_publish",
                data=publish_data
            )
            publish_response.raise_for_status()
            
            return json.dumps(publish_response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to post photo: {str(e)}"})

    def get_media(self, limit: int = 25) -> str:
        """Get recent media from Instagram.

        Args:
            limit (int): Number of media items to retrieve

        Returns:
            str: Media data or error message
        """
        if not all([self.access_token, self.user_id]):
            return json.dumps({"error": "Access token and user ID not provided"})

        try:
            params = {
                "fields": "id,caption,media_type,media_url,permalink,timestamp",
                "limit": limit,
                "access_token": self.access_token
            }

            response = requests.get(
                f"{self.base_url}/{self.user_id}/media",
                params=params
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get media: {str(e)}"})

    def get_insights(self, media_id: str, metrics: List[str] = None) -> str:
        """Get insights for a media post.

        Args:
            media_id (str): Instagram media ID
            metrics (List[str]): List of metrics to retrieve

        Returns:
            str: Insights data or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        if not metrics:
            metrics = ["impressions", "reach", "engagement"]

        try:
            params = {
                "metric": ",".join(metrics),
                "access_token": self.access_token
            }

            response = requests.get(
                f"{self.base_url}/{media_id}/insights",
                params=params
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get insights: {str(e)}"})

    def get_hashtags(self, hashtag: str, limit: int = 25) -> str:
        """Search for hashtag information.

        Args:
            hashtag (str): Hashtag to search for (without #)
            limit (int): Number of results to return

        Returns:
            str: Hashtag data or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            # First, get hashtag ID
            search_params = {
                "q": hashtag,
                "access_token": self.access_token
            }

            search_response = requests.get(
                f"{self.base_url}/ig_hashtag_search",
                params=search_params
            )
            search_response.raise_for_status()
            
            hashtag_data = search_response.json()
            if not hashtag_data.get("data"):
                return json.dumps({"error": "Hashtag not found"})

            hashtag_id = hashtag_data["data"][0]["id"]

            # Get hashtag media
            media_params = {
                "fields": "id,caption,media_type,comments_count,like_count,timestamp",
                "limit": limit,
                "access_token": self.access_token
            }

            media_response = requests.get(
                f"{self.base_url}/{hashtag_id}/recent_media",
                params=media_params
            )
            media_response.raise_for_status()
            
            return json.dumps(media_response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get hashtag data: {str(e)}"})

    def post_story(self, image_url: str) -> str:
        """Post a story to Instagram.

        Args:
            image_url (str): URL of the image for the story

        Returns:
            str: Story result or error message
        """
        if not all([self.access_token, self.user_id]):
            return json.dumps({"error": "Access token and user ID not provided"})

        try:
            # Create story media object
            create_data = {
                "image_url": image_url,
                "media_type": "STORIES",
                "access_token": self.access_token
            }

            create_response = requests.post(
                f"{self.base_url}/{self.user_id}/media",
                data=create_data
            )
            create_response.raise_for_status()
            creation_id = create_response.json()["id"]

            # Publish the story
            publish_data = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }

            publish_response = requests.post(
                f"{self.base_url}/{self.user_id}/media_publish",
                data=publish_data
            )
            publish_response.raise_for_status()
            
            return json.dumps(publish_response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to post story: {str(e)}"})