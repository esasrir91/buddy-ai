import json
from os import getenv
from typing import Any, Dict, List, Optional

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class TwitterTools(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        bearer_token: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Twitter Tools.

        Args:
            api_key (Optional[str]): Twitter API key
            api_secret (Optional[str]): Twitter API secret
            access_token (Optional[str]): Twitter access token
            access_token_secret (Optional[str]): Twitter access token secret
            bearer_token (Optional[str]): Twitter bearer token
        """
        self.api_key = api_key or getenv("TWITTER_API_KEY")
        self.api_secret = api_secret or getenv("TWITTER_API_SECRET")
        self.access_token = access_token or getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or getenv("TWITTER_ACCESS_TOKEN_SECRET")
        self.bearer_token = bearer_token or getenv("TWITTER_BEARER_TOKEN")
        self.base_url = "https://api.twitter.com/2"

        tools: List[Any] = [
            self.post_tweet,
            self.get_tweets,
            self.search_tweets,
            self.get_user_info,
            self.follow_user,
            self.retweet,
        ]

        super().__init__(name="twitter", tools=tools, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Twitter API requests."""
        if self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}", "Content-Type": "application/json"}
        else:
            return {"Content-Type": "application/json"}

    def post_tweet(self, text: str, reply_to_id: Optional[str] = None) -> str:
        """Post a tweet.

        Args:
            text (str): Tweet content (max 280 characters)
            reply_to_id (Optional[str]): Tweet ID to reply to

        Returns:
            str: Tweet result or error message
        """
        if not self.bearer_token:
            return json.dumps({"error": "Bearer token not provided"})

        try:
            payload = {"text": text}

            if reply_to_id:
                payload["reply"] = {"in_reply_to_tweet_id": reply_to_id}

            response = requests.post(f"{self.base_url}/tweets", headers=self._get_headers(), json=payload)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to post tweet: {str(e)}"})

    def get_tweets(self, user_id: str, max_results: int = 10) -> str:
        """Get tweets from a user.

        Args:
            user_id (str): Twitter user ID
            max_results (int): Number of tweets to retrieve

        Returns:
            str: Tweets data or error message
        """
        if not self.bearer_token:
            return json.dumps({"error": "Bearer token not provided"})

        try:
            params = {"max_results": max_results, "tweet.fields": "created_at,author_id,public_metrics"}

            response = requests.get(
                f"{self.base_url}/users/{user_id}/tweets", headers=self._get_headers(), params=params
            )
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get tweets: {str(e)}"})

    def search_tweets(self, query: str, max_results: int = 10) -> str:
        """Search for tweets.

        Args:
            query (str): Search query
            max_results (int): Number of results to return

        Returns:
            str: Search results or error message
        """
        if not self.bearer_token:
            return json.dumps({"error": "Bearer token not provided"})

        try:
            params = {"query": query, "max_results": max_results, "tweet.fields": "created_at,author_id,public_metrics"}

            response = requests.get(f"{self.base_url}/tweets/search/recent", headers=self._get_headers(), params=params)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to search tweets: {str(e)}"})

    def get_user_info(self, username: str) -> str:
        """Get user information.

        Args:
            username (str): Twitter username (without @)

        Returns:
            str: User data or error message
        """
        if not self.bearer_token:
            return json.dumps({"error": "Bearer token not provided"})

        try:
            params = {"user.fields": "created_at,description,location,public_metrics,verified"}

            response = requests.get(
                f"{self.base_url}/users/by/username/{username}", headers=self._get_headers(), params=params
            )
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get user info: {str(e)}"})

    def follow_user(self, user_id: str) -> str:
        """Follow a user.

        Args:
            user_id (str): Twitter user ID to follow

        Returns:
            str: Follow result or error message
        """
        if not self.bearer_token:
            return json.dumps({"error": "Bearer token not provided"})

        try:
            payload = {"target_user_id": user_id}

            response = requests.post(f"{self.base_url}/users/me/following", headers=self._get_headers(), json=payload)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to follow user: {str(e)}"})

    def retweet(self, tweet_id: str) -> str:
        """Retweet a tweet.

        Args:
            tweet_id (str): Tweet ID to retweet

        Returns:
            str: Retweet result or error message
        """
        if not self.bearer_token:
            return json.dumps({"error": "Bearer token not provided"})

        try:
            payload = {"tweet_id": tweet_id}

            response = requests.post(f"{self.base_url}/users/me/retweets", headers=self._get_headers(), json=payload)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to retweet: {str(e)}"})
