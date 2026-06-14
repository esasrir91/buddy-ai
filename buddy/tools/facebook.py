import json
from os import getenv
from typing import Any, Dict, List, Optional

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class FacebookTools(Toolkit):
    def __init__(
        self,
        access_token: Optional[str] = None,
        page_id: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Facebook Tools.

        Args:
            access_token (Optional[str]): Facebook access token
            page_id (Optional[str]): Facebook page ID
            app_id (Optional[str]): Facebook app ID
            app_secret (Optional[str]): Facebook app secret
        """
        self.access_token = access_token or getenv("FACEBOOK_ACCESS_TOKEN")
        self.page_id = page_id or getenv("FACEBOOK_PAGE_ID")
        self.app_id = app_id or getenv("FACEBOOK_APP_ID")
        self.app_secret = app_secret or getenv("FACEBOOK_APP_SECRET")
        self.base_url = "https://graph.facebook.com/v18.0"

        tools: List[Any] = [
            self.post_to_page,
            self.post_photo,
            self.get_page_insights,
            self.get_posts,
            self.delete_post,
        ]

        super().__init__(name="facebook", tools=tools, **kwargs)

    def post_to_page(self, message: str, link: Optional[str] = None) -> str:
        """Post a message to Facebook page.

        Args:
            message (str): Post content
            link (Optional[str]): URL to include with post

        Returns:
            str: Post result or error message
        """
        if not all([self.access_token, self.page_id]):
            return json.dumps({"error": "Access token and page ID not provided"})

        try:
            data = {"message": message, "access_token": self.access_token}

            if link:
                data["link"] = link

            response = requests.post(f"{self.base_url}/{self.page_id}/feed", data=data)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to post: {str(e)}"})

    def post_photo(self, image_url: str, caption: Optional[str] = None) -> str:
        """Post a photo to Facebook page.

        Args:
            image_url (str): URL of the image to post
            caption (Optional[str]): Photo caption

        Returns:
            str: Post result or error message
        """
        if not all([self.access_token, self.page_id]):
            return json.dumps({"error": "Access token and page ID not provided"})

        try:
            data = {"url": image_url, "access_token": self.access_token}

            if caption:
                data["caption"] = caption

            response = requests.post(f"{self.base_url}/{self.page_id}/photos", data=data)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to post photo: {str(e)}"})

    def get_page_insights(self, metric: str = "page_fans", period: str = "day") -> str:
        """Get Facebook page insights.

        Args:
            metric (str): Metric to retrieve (page_fans, page_views, etc.)
            period (str): Time period (day, week, days_28)

        Returns:
            str: Insights data or error message
        """
        if not all([self.access_token, self.page_id]):
            return json.dumps({"error": "Access token and page ID not provided"})

        try:
            params = {"metric": metric, "period": period, "access_token": self.access_token}

            response = requests.get(f"{self.base_url}/{self.page_id}/insights", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get insights: {str(e)}"})

    def get_posts(self, limit: int = 25) -> str:
        """Get recent posts from Facebook page.

        Args:
            limit (int): Number of posts to retrieve

        Returns:
            str: Posts data or error message
        """
        if not all([self.access_token, self.page_id]):
            return json.dumps({"error": "Access token and page ID not provided"})

        try:
            params = {
                "limit": limit,
                "fields": "id,message,created_time,likes.summary(true),comments.summary(true)",
                "access_token": self.access_token,
            }

            response = requests.get(f"{self.base_url}/{self.page_id}/posts", params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get posts: {str(e)}"})

    def delete_post(self, post_id: str) -> str:
        """Delete a Facebook post.

        Args:
            post_id (str): ID of the post to delete

        Returns:
            str: Delete result or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            params = {"access_token": self.access_token}

            response = requests.delete(f"{self.base_url}/{post_id}", params=params)
            response.raise_for_status()

            return json.dumps({"success": "Post deleted successfully"})
        except Exception as e:
            return json.dumps({"error": f"Failed to delete post: {str(e)}"})
