import json
from typing import Any, Dict, List, Optional
from os import getenv

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger


class AWSTools(Toolkit):
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region: str = "us-east-1",
        **kwargs,
    ):
        """Initialize AWS Tools.

        Args:
            access_key_id (Optional[str]): AWS access key ID
            secret_access_key (Optional[str]): AWS secret access key
            region (str): AWS region
        """
        self.access_key_id = access_key_id or getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or getenv("AWS_SECRET_ACCESS_KEY")
        self.region = region

        tools: List[Any] = [
            self.list_s3_buckets,
            self.upload_to_s3,
            self.download_from_s3,
            self.list_ec2_instances,
            self.start_ec2_instance,
            self.stop_ec2_instance,
            self.invoke_lambda,
            self.send_sns_message,
        ]

        super().__init__(name="aws_tools", tools=tools, **kwargs)

    def _get_boto3_client(self, service_name: str):
        """Get boto3 client for AWS service."""
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError("boto3 not installed. Please install using `pip install boto3`")

        return boto3.client(
            service_name,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )

    def list_s3_buckets(self) -> str:
        """List all S3 buckets.

        Returns:
            str: List of S3 buckets or error message
        """
        try:
            s3_client = self._get_boto3_client('s3')
            response = s3_client.list_buckets()
            
            buckets = []
            for bucket in response['Buckets']:
                buckets.append({
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate'].isoformat()
                })
            
            return json.dumps({"buckets": buckets})
        except Exception as e:
            return json.dumps({"error": f"Failed to list S3 buckets: {str(e)}"})

    def upload_to_s3(self, bucket_name: str, file_path: str, object_key: str) -> str:
        """Upload a file to S3.

        Args:
            bucket_name (str): S3 bucket name
            file_path (str): Local file path
            object_key (str): S3 object key

        Returns:
            str: Upload result or error message
        """
        try:
            s3_client = self._get_boto3_client('s3')
            s3_client.upload_file(file_path, bucket_name, object_key)
            
            return json.dumps({
                "success": f"File uploaded to s3://{bucket_name}/{object_key}"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to upload to S3: {str(e)}"})

    def download_from_s3(self, bucket_name: str, object_key: str, file_path: str) -> str:
        """Download a file from S3.

        Args:
            bucket_name (str): S3 bucket name
            object_key (str): S3 object key
            file_path (str): Local file path to save

        Returns:
            str: Download result or error message
        """
        try:
            s3_client = self._get_boto3_client('s3')
            s3_client.download_file(bucket_name, object_key, file_path)
            
            return json.dumps({
                "success": f"File downloaded from s3://{bucket_name}/{object_key} to {file_path}"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to download from S3: {str(e)}"})

    def list_ec2_instances(self) -> str:
        """List EC2 instances.

        Returns:
            str: List of EC2 instances or error message
        """
        try:
            ec2_client = self._get_boto3_client('ec2')
            response = ec2_client.describe_instances()
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'instance_id': instance['InstanceId'],
                        'instance_type': instance['InstanceType'],
                        'state': instance['State']['Name'],
                        'public_ip': instance.get('PublicIpAddress'),
                        'private_ip': instance.get('PrivateIpAddress'),
                        'launch_time': instance['LaunchTime'].isoformat()
                    })
            
            return json.dumps({"instances": instances})
        except Exception as e:
            return json.dumps({"error": f"Failed to list EC2 instances: {str(e)}"})

    def start_ec2_instance(self, instance_id: str) -> str:
        """Start an EC2 instance.

        Args:
            instance_id (str): EC2 instance ID

        Returns:
            str: Start result or error message
        """
        try:
            ec2_client = self._get_boto3_client('ec2')
            response = ec2_client.start_instances(InstanceIds=[instance_id])
            
            return json.dumps({
                "success": f"Instance {instance_id} start initiated",
                "current_state": response['StartingInstances'][0]['CurrentState']['Name']
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to start instance: {str(e)}"})

    def stop_ec2_instance(self, instance_id: str) -> str:
        """Stop an EC2 instance.

        Args:
            instance_id (str): EC2 instance ID

        Returns:
            str: Stop result or error message
        """
        try:
            ec2_client = self._get_boto3_client('ec2')
            response = ec2_client.stop_instances(InstanceIds=[instance_id])
            
            return json.dumps({
                "success": f"Instance {instance_id} stop initiated",
                "current_state": response['StoppingInstances'][0]['CurrentState']['Name']
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to stop instance: {str(e)}"})

    def invoke_lambda(self, function_name: str, payload: Optional[Dict] = None) -> str:
        """Invoke a Lambda function.

        Args:
            function_name (str): Lambda function name
            payload (Optional[Dict]): Function payload

        Returns:
            str: Lambda response or error message
        """
        try:
            lambda_client = self._get_boto3_client('lambda')
            
            invoke_payload = json.dumps(payload or {})
            response = lambda_client.invoke(
                FunctionName=function_name,
                Payload=invoke_payload
            )
            
            response_payload = response['Payload'].read().decode('utf-8')
            
            return json.dumps({
                "status_code": response['StatusCode'],
                "payload": json.loads(response_payload) if response_payload else None
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to invoke Lambda function: {str(e)}"})

    def send_sns_message(self, topic_arn: str, message: str, subject: Optional[str] = None) -> str:
        """Send a message via SNS.

        Args:
            topic_arn (str): SNS topic ARN
            message (str): Message content
            subject (Optional[str]): Message subject

        Returns:
            str: SNS response or error message
        """
        try:
            sns_client = self._get_boto3_client('sns')
            
            publish_args = {
                'TopicArn': topic_arn,
                'Message': message
            }
            
            if subject:
                publish_args['Subject'] = subject
                
            response = sns_client.publish(**publish_args)
            
            return json.dumps({
                "message_id": response['MessageId'],
                "success": "Message sent successfully"
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to send SNS message: {str(e)}"})