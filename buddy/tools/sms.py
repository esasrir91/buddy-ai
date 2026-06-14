import json
from os import getenv
from typing import Any, List, Optional

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class SMSTools(Toolkit):
    def __init__(
        self,
        provider: str = "twilio",
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        aws_region: str = "us-east-1",
        **kwargs,
    ):
        """Initialize SMS Tools.

        Args:
            provider (str): SMS provider ('twilio' or 'aws_sns')
            account_sid (Optional[str]): Twilio account SID
            auth_token (Optional[str]): Twilio auth token
            from_number (Optional[str]): Phone number to send from
            aws_access_key (Optional[str]): AWS access key for SNS
            aws_secret_key (Optional[str]): AWS secret key for SNS
            aws_region (str): AWS region for SNS
        """
        self.provider = provider
        self.account_sid = account_sid or getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or getenv("TWILIO_PHONE_NUMBER")
        self.aws_access_key = aws_access_key or getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = aws_region

        tools: List[Any] = [
            self.send_sms,
            self.send_bulk_sms,
            self.get_message_status,
        ]

        super().__init__(name="sms_tools", tools=tools, **kwargs)

    def send_sms(self, to_number: str, message: str) -> str:
        """Send an SMS message.

        Args:
            to_number (str): Phone number to send to
            message (str): Message content

        Returns:
            str: Message details or error message
        """
        if self.provider == "twilio":
            return self._send_twilio_sms(to_number, message)
        elif self.provider == "aws_sns":
            return self._send_aws_sns_sms(to_number, message)
        else:
            return json.dumps({"error": "Unsupported provider"})

    def _send_twilio_sms(self, to_number: str, message: str) -> str:
        """Send SMS via Twilio."""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            return json.dumps({"error": "Twilio credentials not provided"})

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

            data = {"From": self.from_number, "To": to_number, "Body": message}

            response = requests.post(url, data=data, auth=(self.account_sid, self.auth_token))
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to send SMS: {str(e)}"})

    def _send_aws_sns_sms(self, to_number: str, message: str) -> str:
        """Send SMS via AWS SNS."""
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            return json.dumps({"error": "boto3 not installed. Please install using `pip install boto3`"})

        if not all([self.aws_access_key, self.aws_secret_key]):
            return json.dumps({"error": "AWS credentials not provided"})

        try:
            sns_client = boto3.client(
                "sns",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )

            response = sns_client.publish(PhoneNumber=to_number, Message=message)

            return json.dumps({"message_id": response["MessageId"], "status": "sent"})
        except ClientError as e:
            return json.dumps({"error": f"AWS SNS error: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Failed to send SMS: {str(e)}"})

    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> str:
        """Send SMS to multiple recipients.

        Args:
            phone_numbers (List[str]): List of phone numbers
            message (str): Message content

        Returns:
            str: Bulk send results
        """
        results = []

        for number in phone_numbers:
            result = self.send_sms(number, message)
            results.append({"number": number, "result": json.loads(result)})

        return json.dumps({"bulk_results": results})

    def get_message_status(self, message_sid: str) -> str:
        """Get status of a Twilio message.

        Args:
            message_sid (str): Message SID from Twilio

        Returns:
            str: Message status or error message
        """
        if self.provider != "twilio":
            return json.dumps({"error": "Message status only available for Twilio"})

        if not all([self.account_sid, self.auth_token]):
            return json.dumps({"error": "Twilio credentials not provided"})

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages/{message_sid}.json"

            response = requests.get(url, auth=(self.account_sid, self.auth_token))
            response.raise_for_status()

            return json.dumps(response.json())
        except Exception as e:
            return json.dumps({"error": f"Failed to get message status: {str(e)}"})
