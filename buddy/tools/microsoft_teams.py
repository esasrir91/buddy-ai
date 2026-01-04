import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class MicrosoftTeamsTools(Toolkit):
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        webhook_url: Optional[str] = None,
        **kwargs,
    ):
        """Initialize Microsoft Teams Tools.

        Args:
            tenant_id (Optional[str]): Azure AD tenant ID
            client_id (Optional[str]): Azure app client ID
            client_secret (Optional[str]): Azure app client secret
            webhook_url (Optional[str]): Teams webhook URL for sending messages
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.webhook_url = webhook_url
        self.access_token = None
        self.token_expiry = None

        tools: List[Any] = [
            self.send_message,
            self.send_card_message,
            self.create_meeting,
            self.get_teams,
            self.get_channels,
        ]

        super().__init__(name="microsoft_teams", tools=tools, **kwargs)

    def _get_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API."""
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            logger.error("Microsoft Teams credentials not provided")
            return None

        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        try:
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default"
            }

            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=token_data["expires_in"] - 60)
            
            return self.access_token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    def send_message(self, message: str, title: Optional[str] = None) -> str:
        """Send a message to Microsoft Teams via webhook.

        Args:
            message (str): Message content
            title (Optional[str]): Message title

        Returns:
            str: Success or error message
        """
        if not self.webhook_url:
            return json.dumps({"error": "Webhook URL not provided"})

        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "text": message
            }
            
            if title:
                payload["title"] = title

            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            
            return json.dumps({"success": "Message sent successfully"})
        except Exception as e:
            return json.dumps({"error": f"Failed to send message: {str(e)}"})

    def send_card_message(self, title: str, message: str, actions: Optional[List[Dict]] = None) -> str:
        """Send an adaptive card message to Teams.

        Args:
            title (str): Card title
            message (str): Card message
            actions (Optional[List[Dict]]): Card actions

        Returns:
            str: Success or error message
        """
        if not self.webhook_url:
            return json.dumps({"error": "Webhook URL not provided"})

        try:
            card = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "title": title,
                "text": message
            }
            
            if actions:
                card["potentialAction"] = actions

            response = requests.post(self.webhook_url, json=card)
            response.raise_for_status()
            
            return json.dumps({"success": "Card message sent successfully"})
        except Exception as e:
            return json.dumps({"error": f"Failed to send card: {str(e)}"})

    def create_meeting(self, subject: str, start_time: str, duration_minutes: int = 60, attendees: Optional[List[str]] = None) -> str:
        """Create a Teams meeting.

        Args:
            subject (str): Meeting subject
            start_time (str): Meeting start time (ISO format)
            duration_minutes (int): Meeting duration in minutes
            attendees (Optional[List[str]]): List of attendee email addresses

        Returns:
            str: Meeting details or error message
        """
        token = self._get_access_token()
        if not token:
            return json.dumps({"error": "Authentication failed"})

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            meeting_data = {
                "subject": subject,
                "start": {
                    "dateTime": start_time,
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": (datetime.fromisoformat(start_time.replace('Z', '+00:00')) + 
                              timedelta(minutes=duration_minutes)).isoformat(),
                    "timeZone": "UTC"
                },
                "isOnlineMeeting": True,
                "onlineMeetingProvider": "teamsForBusiness"
            }

            if attendees:
                meeting_data["attendees"] = [
                    {"emailAddress": {"address": email}} for email in attendees
                ]

            response = requests.post(
                "https://graph.microsoft.com/v1.0/me/events",
                headers=headers,
                json=meeting_data
            )
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to create meeting: {str(e)}"})

    def get_teams(self) -> str:
        """Get list of teams.

        Returns:
            str: Teams list or error message
        """
        token = self._get_access_token()
        if not token:
            return json.dumps({"error": "Authentication failed"})

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get("https://graph.microsoft.com/v1.0/me/joinedTeams", headers=headers)
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get teams: {str(e)}"})

    def get_channels(self, team_id: str) -> str:
        """Get channels for a team.

        Args:
            team_id (str): Team ID

        Returns:
            str: Channels list or error message
        """
        token = self._get_access_token()
        if not token:
            return json.dumps({"error": "Authentication failed"})

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels", headers=headers)
            response.raise_for_status()
            
            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get channels: {str(e)}"})