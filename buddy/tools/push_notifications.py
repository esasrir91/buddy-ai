import json
from os import getenv
from typing import Any, Dict, List, Optional

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class PushNotificationTools(Toolkit):
    def __init__(
        self,
        firebase_server_key: Optional[str] = None,
        onesignal_app_id: Optional[str] = None,
        onesignal_api_key: Optional[str] = None,
        expo_access_token: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Push Notification Tools.

        Args:
            firebase_server_key (Optional[str]): Firebase Cloud Messaging server key
            onesignal_app_id (Optional[str]): OneSignal app ID
            onesignal_api_key (Optional[str]): OneSignal REST API key
            expo_access_token (Optional[str]): Expo push token
        """
        self.firebase_server_key = firebase_server_key or getenv("FIREBASE_SERVER_KEY")
        self.onesignal_app_id = onesignal_app_id or getenv("ONESIGNAL_APP_ID")
        self.onesignal_api_key = onesignal_api_key or getenv("ONESIGNAL_API_KEY")
        self.expo_access_token = expo_access_token or getenv("EXPO_ACCESS_TOKEN")

        tools: List[Any] = [
            self.send_firebase_notification,
            self.send_onesignal_notification,
            self.send_expo_notification,
            self.send_web_push,
        ]

        super().__init__(name="push_notifications", tools=tools, **kwargs)

    def send_firebase_notification(
        self, tokens: List[str], title: str, body: str, data: Optional[Dict] = None, image_url: Optional[str] = None
    ) -> str:
        """Send push notification via Firebase Cloud Messaging.

        Args:
            tokens (List[str]): List of device tokens
            title (str): Notification title
            body (str): Notification body
            data (Optional[Dict]): Custom data payload
            image_url (Optional[str]): Image URL for rich notifications

        Returns:
            str: Notification result or error message
        """
        if not self.firebase_server_key:
            return json.dumps({"error": "Firebase server key not provided"})

        try:
            headers = {"Authorization": f"key={self.firebase_server_key}", "Content-Type": "application/json"}

            notification_payload = {"title": title, "body": body}

            if image_url:
                notification_payload["image"] = image_url

            payload = {"registration_ids": tokens, "notification": notification_payload}

            if data:
                payload["data"] = data

            response = requests.post("https://fcm.googleapis.com/fcm/send", headers=headers, json=payload)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to send Firebase notification: {str(e)}"})

    def send_onesignal_notification(
        self,
        player_ids: List[str],
        title: str,
        content: str,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """Send push notification via OneSignal.

        Args:
            player_ids (List[str]): List of OneSignal player IDs
            title (str): Notification title
            content (str): Notification content
            url (Optional[str]): URL to open when notification is clicked
            image_url (Optional[str]): Large image URL

        Returns:
            str: Notification result or error message
        """
        if not all([self.onesignal_app_id, self.onesignal_api_key]):
            return json.dumps({"error": "OneSignal credentials not provided"})

        try:
            headers = {"Authorization": f"Basic {self.onesignal_api_key}", "Content-Type": "application/json"}

            payload = {
                "app_id": self.onesignal_app_id,
                "include_player_ids": player_ids,
                "headings": {"en": title},
                "contents": {"en": content},
            }

            if url:
                payload["url"] = url

            if image_url:
                payload["large_icon"] = image_url

            response = requests.post("https://onesignal.com/api/v1/notifications", headers=headers, json=payload)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to send OneSignal notification: {str(e)}"})

    def send_expo_notification(
        self, expo_tokens: List[str], title: str, body: str, data: Optional[Dict] = None, sound: str = "default"
    ) -> str:
        """Send push notification via Expo.

        Args:
            expo_tokens (List[str]): List of Expo push tokens
            title (str): Notification title
            body (str): Notification body
            data (Optional[Dict]): Custom data payload
            sound (str): Notification sound

        Returns:
            str: Notification result or error message
        """
        try:
            headers = {
                "Accept": "application/json",
                "Accept-encoding": "gzip, deflate",
                "Content-Type": "application/json",
            }

            if self.expo_access_token:
                headers["Authorization"] = f"Bearer {self.expo_access_token}"

            messages = []
            for token in expo_tokens:
                message = {"to": token, "title": title, "body": body, "sound": sound}
                if data:
                    message["data"] = data
                messages.append(message)

            response = requests.post("https://exp.host/--/api/v2/push/send", headers=headers, json=messages)
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to send Expo notification: {str(e)}"})

    def send_web_push(
        self,
        endpoint: str,
        title: str,
        body: str,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        actions: Optional[List[Dict]] = None,
    ) -> str:
        """Send web push notification.

        Args:
            endpoint (str): Push service endpoint
            title (str): Notification title
            body (str): Notification body
            icon (Optional[str]): Icon URL
            badge (Optional[str]): Badge URL
            actions (Optional[List[Dict]]): Action buttons

        Returns:
            str: Notification result or error message
        """
        try:
            payload = {"title": title, "body": body}

            if icon:
                payload["icon"] = icon
            if badge:
                payload["badge"] = badge
            if actions:
                payload["actions"] = actions

            headers = {"Content-Type": "application/json"}

            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()

            return json.dumps({"success": "Web push sent successfully"})
        except Exception as e:
            return json.dumps({"error": f"Failed to send web push: {str(e)}"})
