import json
from typing import Any, Dict, List, Optional
from os import getenv

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class LinkedInTools(Toolkit):
    def __init__(
        self,
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        **kwargs,
    ):
        """Initialize LinkedIn Tools.

        Args:
            access_token (Optional[str]): LinkedIn access token
            client_id (Optional[str]): LinkedIn app client ID
            client_secret (Optional[str]): LinkedIn app client secret
        """
        self.access_token = access_token or getenv("LINKEDIN_ACCESS_TOKEN")
        self.client_id = client_id or getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = client_secret or getenv("LINKEDIN_CLIENT_SECRET")
        self.base_url = "https://api.linkedin.com/v2"

        tools: List[Any] = [
            self.post_update,
            self.get_profile,
            self.share_article,
            self.get_connections,
            self.send_message,
        ]

        super().__init__(name="linkedin", tools=tools, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for LinkedIn API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    def post_update(self, text: str, visibility: str = "PUBLIC") -> str:
        """Post a text update to LinkedIn.

        Args:
            text (str): Update content
            visibility (str): Post visibility (PUBLIC, CONNECTIONS)

        Returns:
            str: Post result or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            # Get user profile first
            profile_response = requests.get(
                f"{self.base_url}/people/~",
                headers=self._get_headers()
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
            person_urn = profile["id"]

            payload = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }

            response = requests.post(
                f"{self.base_url}/ugcPosts",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to post update: {str(e)}"})

    def get_profile(self) -> str:
        """Get user profile information.

        Returns:
            str: Profile data or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            response = requests.get(
                f"{self.base_url}/people/~",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get profile: {str(e)}"})

    def share_article(self, article_url: str, comment: str, title: Optional[str] = None) -> str:
        """Share an article on LinkedIn.

        Args:
            article_url (str): URL of the article to share
            comment (str): Comment about the article
            title (Optional[str]): Article title

        Returns:
            str: Share result or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            # Get user profile first
            profile_response = requests.get(
                f"{self.base_url}/people/~",
                headers=self._get_headers()
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
            person_urn = profile["id"]

            payload = {
                "author": f"urn:li:person:{person_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": comment
                        },
                        "shareMediaCategory": "ARTICLE",
                        "media": [{
                            "status": "READY",
                            "description": {
                                "text": title or "Shared article"
                            },
                            "originalUrl": article_url,
                            "title": {
                                "text": title or "Article"
                            }
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            response = requests.post(
                f"{self.base_url}/ugcPosts",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to share article: {str(e)}"})

    def get_connections(self, start: int = 0, count: int = 50) -> str:
        """Get user connections.

        Args:
            start (int): Starting index
            count (int): Number of connections to retrieve

        Returns:
            str: Connections data or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            params = {
                "start": start,
                "count": count
            }

            response = requests.get(
                f"{self.base_url}/people/~/connections",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get connections: {str(e)}"})

    def send_message(self, recipient_id: str, subject: str, message: str) -> str:
        """Send a message to a connection.

        Args:
            recipient_id (str): LinkedIn member ID of recipient
            subject (str): Message subject
            message (str): Message content

        Returns:
            str: Message result or error message
        """
        if not self.access_token:
            return json.dumps({"error": "Access token not provided"})

        try:
            payload = {
                "recipients": {
                    "values": [{
                        "person": {
                            "_path": f"/person/{recipient_id}"
                        }
                    }]
                },
                "subject": subject,
                "body": message
            }

            response = requests.post(
                f"{self.base_url}/people/~/mailbox",
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to send message: {str(e)}"})