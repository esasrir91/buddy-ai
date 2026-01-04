# Built-in Tools Reference

Buddy AI comes with 200+ built-in tools organized into categories. Each tool provides specific functionality that agents can use to interact with external services, process data, and perform actions.

## 📚 Tool Categories Overview

| Category | Tools | Description |
|----------|--------|-------------|
| **Web & Search** | 15+ tools | Web scraping, search engines, URL processing |
| **Communication** | 12+ tools | Email, SMS, Slack, Teams, social media |
| **File & Data** | 20+ tools | File operations, CSV, JSON, database queries |
| **Cloud Services** | 18+ tools | AWS, Google Cloud, Azure integrations |
| **Development** | 15+ tools | GitHub, Docker, Kubernetes, code execution |
| **AI/ML** | 10+ tools | Image generation, transcription, embeddings |
| **Business** | 12+ tools | Calendar, CRM, project management |
| **Utilities** | 25+ tools | Calculations, time zones, QR codes, etc. |

## 🌐 Web & Search Tools

### DuckDuckGoSearch
Privacy-focused web search engine.

```python
from buddy.tools.web import DuckDuckGoSearch

search = DuckDuckGoSearch(
    max_results=10,
    region="us-en",
    safesearch="moderate",
    timeout=10
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[search],
    instructions="Use web search for current information."
)
```

**Methods:**
- `search(query: str, max_results: int = 5) -> List[SearchResult]`

### WebScraper
Extract content from web pages.

```python
from buddy.tools.web import WebScraper

scraper = WebScraper(
    timeout=30,
    headers={"User-Agent": "BuddyAI"},
    max_content_length=1000000
)
```

**Methods:**
- `scrape_url(url: str) -> str` - Extract text content
- `scrape_links(url: str) -> List[str]` - Extract all links
- `scrape_images(url: str) -> List[str]` - Extract image URLs

### GoogleSearch (via SerpAPI)
Google search with advanced features.

```python
from buddy.tools.serpapi import GoogleSearch

google_search = GoogleSearch(
    api_key="your-serpapi-key",
    engine="google",
    location="United States"
)
```

### Tavily Search
AI-optimized search engine.

```python
from buddy.tools.tavily import TavilySearch

tavily = TavilySearch(
    api_key="your-tavily-key",
    search_depth="basic",  # or "advanced"
    max_results=10
)
```

### Website Tools
Comprehensive website interaction.

```python
from buddy.tools.website import WebsiteTools

website = WebsiteTools()
```

**Methods:**
- `read_website(url: str) -> str`
- `search_website(url: str, query: str) -> List[str]`
- `get_website_links(url: str) -> List[str]`

## 💻 Development Tools

### GitHub Tools
Complete GitHub integration for repository management, issues, and pull requests.

```python
from buddy.tools.github import GithubTools

github = GithubTools(
    access_token="your-github-token",  # or set GITHUB_ACCESS_TOKEN env var
    search_repositories=True,
    list_repositories=True,
    get_repository=True,
    create_issue=True,
    get_pull_request=True,
    create_pull_request=True,
    get_file_content=True,
    update_file=True,
    create_file=True,
    delete_file=True,
    list_branches=True,
    create_branch=True,
    search_code=True
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[github],
    instructions="Help with GitHub repository management."
)
```

**Repository Management:**
- `search_repositories(query: str, sort: str = "stars") -> List[Dict]` - Search GitHub repositories
- `list_repositories(username: str, type: str = "all") -> List[Dict]` - List user repositories  
- `get_repository(owner: str, repo: str) -> Dict` - Get repository details
- `create_repository(name: str, description: str = "", private: bool = False) -> Dict` - Create new repository
- `delete_repository(owner: str, repo: str) -> bool` - Delete repository
- `get_repository_languages(owner: str, repo: str) -> Dict` - Get programming languages used
- `get_repository_stars(owner: str, repo: str) -> int` - Get star count

**File Operations:**
- `get_file_content(owner: str, repo: str, path: str, branch: str = "main") -> str` - Read file content
- `create_file(owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> Dict` - Create new file
- `update_file(owner: str, repo: str, path: str, content: str, message: str, sha: str, branch: str = "main") -> Dict` - Update existing file
- `delete_file(owner: str, repo: str, path: str, message: str, sha: str, branch: str = "main") -> Dict` - Delete file
- `get_directory_content(owner: str, repo: str, path: str = "", branch: str = "main") -> List[Dict]` - List directory contents

**Branch Management:**
- `list_branches(owner: str, repo: str) -> List[str]` - List all branches
- `create_branch(owner: str, repo: str, branch_name: str, source_branch: str = "main") -> Dict` - Create new branch
- `set_default_branch(owner: str, repo: str, branch: str) -> bool` - Set default branch
- `get_branch_content(owner: str, repo: str, branch: str) -> Dict` - Get branch information

**Issues Management:**
- `list_issues(owner: str, repo: str, state: str = "open") -> List[Dict]` - List repository issues
- `get_issue(owner: str, repo: str, issue_number: int) -> Dict` - Get specific issue
- `create_issue(owner: str, repo: str, title: str, body: str = "", labels: List[str] = None) -> Dict` - Create new issue
- `edit_issue(owner: str, repo: str, issue_number: int, title: str = None, body: str = None, state: str = None) -> Dict` - Edit existing issue
- `close_issue(owner: str, repo: str, issue_number: int) -> Dict` - Close issue
- `reopen_issue(owner: str, repo: str, issue_number: int) -> Dict` - Reopen closed issue
- `assign_issue(owner: str, repo: str, issue_number: int, assignees: List[str]) -> Dict` - Assign users to issue
- `label_issue(owner: str, repo: str, issue_number: int, labels: List[str]) -> Dict` - Add labels to issue
- `comment_on_issue(owner: str, repo: str, issue_number: int, comment: str) -> Dict` - Comment on issue
- `list_issue_comments(owner: str, repo: str, issue_number: int) -> List[Dict]` - Get issue comments

**Pull Request Management:**
- `get_pull_requests(owner: str, repo: str, state: str = "open") -> List[Dict]` - List pull requests
- `get_pull_request(owner: str, repo: str, pr_number: int) -> Dict` - Get specific pull request
- `create_pull_request(owner: str, repo: str, title: str, body: str, head: str, base: str) -> Dict` - Create pull request
- `get_pull_request_changes(owner: str, repo: str, pr_number: int) -> List[Dict]` - Get PR file changes
- `get_pull_request_comments(owner: str, repo: str, pr_number: int) -> List[Dict]` - Get PR comments
- `create_pull_request_comment(owner: str, repo: str, pr_number: int, comment: str) -> Dict` - Comment on PR
- `edit_pull_request_comment(owner: str, repo: str, comment_id: int, comment: str) -> Dict` - Edit PR comment
- `get_pull_request_count(owner: str, repo: str) -> int` - Get total PR count
- `create_review_request(owner: str, repo: str, pr_number: int, reviewers: List[str]) -> Dict` - Request PR review

**Search Operations:**
- `search_code(query: str, language: str = None, repo: str = None) -> List[Dict]` - Search code across GitHub
- `search_issues_and_prs(query: str, type: str = "issue") -> List[Dict]` - Search issues and pull requests

**Example Usage:**
```python
# Search for Python repositories
repos = github.search_repositories("python machine learning", sort="stars")

# Create an issue
issue = github.create_issue(
    owner="username",
    repo="repository", 
    title="Bug: Application crashes on startup",
    body="The application crashes when trying to start...",
    labels=["bug", "priority-high"]
)

# Read file content
content = github.get_file_content("username", "repository", "src/main.py")

# Create a pull request
pr = github.create_pull_request(
    owner="username",
    repo="repository",
    title="Fix startup crash bug",
    body="This PR fixes the startup crash issue...", 
    head="fix-startup-crash",
    base="main"
)
```

### Docker Tools
Complete Docker container and image management.

```python
from buddy.tools.docker import DockerTools

docker_tools = DockerTools(
    enable_container_management=True,
    enable_image_management=True,
    enable_volume_management=True,
    enable_network_management=True
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[docker_tools],
    instructions="Help with Docker container management."
)
```

**Container Management:**
- `list_containers(all: bool = True) -> List[Dict]` - List all containers
- `run_container(image: str, name: str = None, command: str = None, ports: Dict = None, volumes: Dict = None, environment: Dict = None, detach: bool = True) -> Dict` - Run new container
- `start_container(container_id: str) -> bool` - Start stopped container
- `stop_container(container_id: str, timeout: int = 10) -> bool` - Stop running container
- `remove_container(container_id: str, force: bool = False) -> bool` - Remove container
- `inspect_container(container_id: str) -> Dict` - Get detailed container information
- `get_container_logs(container_id: str, tail: int = 100, follow: bool = False) -> str` - Get container logs
- `exec_in_container(container_id: str, command: str, workdir: str = None) -> Dict` - Execute command in container

**Image Management:**
- `list_images() -> List[Dict]` - List all Docker images
- `pull_image(repository: str, tag: str = "latest") -> Dict` - Pull image from registry
- `build_image(path: str, tag: str, dockerfile: str = "Dockerfile") -> Dict` - Build image from Dockerfile
- `remove_image(image_id: str, force: bool = False) -> bool` - Remove Docker image
- `inspect_image(image_id: str) -> Dict` - Get detailed image information
- `tag_image(image_id: str, repository: str, tag: str) -> bool` - Tag image
- `push_image(repository: str, tag: str = "latest") -> Dict` - Push image to registry

**Volume Management:**
- `list_volumes() -> List[Dict]` - List all Docker volumes
- `create_volume(name: str, driver: str = "local", options: Dict = None) -> Dict` - Create new volume
- `remove_volume(name: str, force: bool = False) -> bool` - Remove volume
- `inspect_volume(name: str) -> Dict` - Get volume details

**Network Management:**
- `list_networks() -> List[Dict]` - List all Docker networks
- `create_network(name: str, driver: str = "bridge", options: Dict = None) -> Dict` - Create network
- `remove_network(name: str) -> bool` - Remove network
- `inspect_network(name: str) -> Dict` - Get network details

**Example Usage:**
```python
# Run a new container
container = docker_tools.run_container(
    image="nginx:latest",
    name="my-nginx",
    ports={"80/tcp": 8080},
    environment={"ENV": "production"}
)

# Execute command in running container
result = docker_tools.exec_in_container(
    container_id="my-nginx",
    command="nginx -t"
)

# Build image from Dockerfile
image = docker_tools.build_image(
    path="./docker-build",
    tag="my-app:latest",
    dockerfile="Dockerfile"
)

# Create and manage volumes
volume = docker_tools.create_volume(
    name="app-data",
    options={"device": "/opt/data"}
)
```

### Kubernetes Tools
Complete Kubernetes cluster management and orchestration.

```python
from buddy.tools.kubernetes_tools import KubernetesTools

k8s_tools = KubernetesTools(
    config_file="~/.kube/config",  # Path to kubeconfig file
    namespace="default"            # Default namespace
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[k8s_tools],
    instructions="Help with Kubernetes cluster management."
)
```

**Pod Management:**
- `get_pods(namespace: str = None) -> List[Dict]` - List all pods in namespace
- `create_pod(pod_manifest: Dict, namespace: str = None) -> Dict` - Create new pod
- `delete_pod(pod_name: str, namespace: str = None) -> bool` - Delete pod
- `get_logs(pod_name: str, namespace: str = None, container: str = None, tail_lines: int = 100) -> str` - Get pod logs

**Service Management:**
- `get_services(namespace: str = None) -> List[Dict]` - List all services
- `create_service(service_manifest: Dict, namespace: str = None) -> Dict` - Create service
- `delete_service(service_name: str, namespace: str = None) -> bool` - Delete service

**Deployment Management:**
- `get_deployments(namespace: str = None) -> List[Dict]` - List all deployments
- `create_deployment(deployment_manifest: Dict, namespace: str = None) -> Dict` - Create deployment
- `scale_deployment(deployment_name: str, replicas: int, namespace: str = None) -> Dict` - Scale deployment
- `delete_deployment(deployment_name: str, namespace: str = None) -> bool` - Delete deployment

**Cluster Operations:**
- `apply_yaml(yaml_content: str, namespace: str = None) -> Dict` - Apply YAML configuration
- `get_cluster_info() -> Dict` - Get cluster information
- `get_nodes() -> List[Dict]` - List cluster nodes
- `get_namespaces() -> List[Dict]` - List all namespaces

**Example Usage:**
```python
# List all pods in a namespace
pods = k8s_tools.get_pods(namespace="production")

# Scale a deployment
result = k8s_tools.scale_deployment(
    deployment_name="web-app",
    replicas=5,
    namespace="production"
)

# Apply YAML configuration
yaml_config = '''
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: test-container
    image: nginx:latest
'''

k8s_tools.apply_yaml(yaml_config, namespace="testing")

# Get application logs
logs = k8s_tools.get_logs(
    pod_name="web-app-123",
    namespace="production",
    tail_lines=50
)
```

## ☁️ Cloud Services

### AWS Tools
Comprehensive Amazon Web Services integration.

```python
from buddy.tools.aws_tools import AWSTools

aws_tools = AWSTools(
    access_key_id="your-access-key",      # or set AWS_ACCESS_KEY_ID env var
    secret_access_key="your-secret-key",  # or set AWS_SECRET_ACCESS_KEY env var
    region="us-east-1"                    # AWS region
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[aws_tools],
    instructions="Help with AWS cloud services management."
)
```

**S3 Storage:**
- `list_s3_buckets() -> List[Dict]` - List all S3 buckets
- `upload_to_s3(bucket_name: str, key: str, file_path: str, content_type: str = None) -> Dict` - Upload file to S3
- `download_from_s3(bucket_name: str, key: str, local_path: str) -> Dict` - Download file from S3
- `delete_from_s3(bucket_name: str, key: str) -> bool` - Delete object from S3
- `list_s3_objects(bucket_name: str, prefix: str = "") -> List[Dict]` - List objects in S3 bucket

**EC2 Instances:**
- `list_ec2_instances(state: str = "all") -> List[Dict]` - List EC2 instances
- `start_ec2_instance(instance_id: str) -> Dict` - Start EC2 instance
- `stop_ec2_instance(instance_id: str) -> Dict` - Stop EC2 instance
- `reboot_ec2_instance(instance_id: str) -> Dict` - Reboot EC2 instance
- `terminate_ec2_instance(instance_id: str) -> Dict` - Terminate EC2 instance

**Lambda Functions:**
- `invoke_lambda(function_name: str, payload: Dict = None) -> Dict` - Invoke Lambda function
- `list_lambda_functions() -> List[Dict]` - List all Lambda functions
- `get_lambda_logs(function_name: str, start_time: str = None) -> List[str]` - Get Lambda logs

**SNS Messaging:**
- `send_sns_message(topic_arn: str, message: str, subject: str = None) -> Dict` - Send SNS message
- `list_sns_topics() -> List[Dict]` - List SNS topics
- `create_sns_topic(name: str) -> Dict` - Create SNS topic

**CloudWatch:**
- `get_cloudwatch_metrics(namespace: str, metric_name: str, dimensions: Dict = None) -> List[Dict]` - Get CloudWatch metrics
- `put_cloudwatch_metric(namespace: str, metric_name: str, value: float, unit: str = "Count") -> bool` - Put custom metric

**Example Usage:**
```python
# Upload file to S3
upload_result = aws_tools.upload_to_s3(
    bucket_name="my-bucket",
    key="documents/report.pdf",
    file_path="/local/path/report.pdf",
    content_type="application/pdf"
)

# Start EC2 instance
start_result = aws_tools.start_ec2_instance(instance_id="i-1234567890abcdef0")

# Invoke Lambda function
lambda_result = aws_tools.invoke_lambda(
    function_name="process-data",
    payload={"input": "data to process"}
)

# Send notification
sns_result = aws_tools.send_sns_message(
    topic_arn="arn:aws:sns:us-east-1:123456789012:my-topic",
    message="Processing completed successfully",
    subject="Job Status Update"
)
```

## 📧 Communication Tools

### Email Tools
Send emails via SMTP with support for various email providers.

```python
from buddy.tools.email import EmailTools

email_tools = EmailTools(
    sender_email="your-email@gmail.com",
    sender_passkey="your-app-password",  # Gmail app password
    sender_name="Your Name",
    receiver_email="recipient@example.com"  # Default receiver
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[email_tools],
    instructions="Help with sending email communications."
)
```

**Email Operations:**
- `email_user(subject: str, body: str, receiver_email: str = None) -> str` - Send email to user

**Example Usage:**
```python
# Send email notification
result = email_tools.email_user(
    subject="Project Status Update",
    body="The project has been completed successfully. Please review the results.",
    receiver_email="manager@company.com"  # Override default receiver
)

# Send automated report
report_body = """
Daily Report Summary:
- Tasks completed: 15
- Issues resolved: 3
- New tickets: 2

Best regards,
AI Assistant
"""

email_tools.email_user(
    subject="Daily Report - " + datetime.now().strftime("%Y-%m-%d"),
    body=report_body
)
```

### Gmail Tools
Advanced Gmail integration with full API access.

```python
from buddy.tools.gmail import GmailTools

gmail_tools = GmailTools(
    credentials_path="path/to/credentials.json",  # Google API credentials
    token_path="path/to/token.json",             # OAuth token
    scopes=["https://www.googleapis.com/auth/gmail.modify"]
)
```

**Email Management:**
- `send_email(to: str, subject: str, body: str, cc: str = None, bcc: str = None, attachments: List[str] = None) -> Dict` - Send email with attachments
- `list_emails(query: str = "", max_results: int = 10) -> List[Dict]` - Search and list emails
- `read_email(message_id: str) -> Dict` - Read specific email
- `mark_as_read(message_id: str) -> bool` - Mark email as read
- `mark_as_unread(message_id: str) -> bool` - Mark email as unread
- `delete_email(message_id: str) -> bool` - Delete email
- `create_draft(to: str, subject: str, body: str) -> Dict` - Create email draft

**Example Usage:**
```python
# Send email with attachment
gmail_tools.send_email(
    to="client@company.com",
    subject="Quarterly Report",
    body="Please find the quarterly report attached.",
    attachments=["./reports/Q4_2024.pdf"]
)

# Search for emails
emails = gmail_tools.list_emails(
    query="from:important@client.com is:unread",
    max_results=20
)

# Read and process email
for email in emails:
    content = gmail_tools.read_email(email['id'])
    # Process email content
    gmail_tools.mark_as_read(email['id'])
```

### Slack Tools
Complete Slack workspace integration for messaging and collaboration.

```python
from buddy.tools.slack import SlackTools

slack_tools = SlackTools(
    token="xoxb-your-bot-token",  # or set SLACK_TOKEN env var
    send_message=True,
    send_message_thread=True,
    list_channels=True,
    get_channel_history=True
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[slack_tools],
    instructions="Help with Slack workspace communication."
)
```

**Messaging:**
- `send_message(channel: str, text: str) -> str` - Send message to channel
- `send_message_thread(channel: str, text: str, thread_ts: str) -> str` - Reply to thread
- `send_direct_message(user_id: str, text: str) -> str` - Send DM to user
- `send_file(channel: str, file_path: str, comment: str = None) -> str` - Upload and share file

**Channel Management:**
- `list_channels() -> List[Dict]` - List all channels
- `get_channel_info(channel: str) -> Dict` - Get channel details
- `create_channel(name: str, is_private: bool = False) -> Dict` - Create new channel
- `join_channel(channel: str) -> bool` - Join channel
- `leave_channel(channel: str) -> bool` - Leave channel

**Message History:**
- `get_channel_history(channel: str, limit: int = 10, oldest: str = None) -> List[Dict]` - Get recent messages
- `search_messages(query: str, count: int = 20) -> List[Dict]` - Search messages across workspace
- `get_thread_replies(channel: str, thread_ts: str) -> List[Dict]` - Get thread replies

**User Management:**
- `list_users() -> List[Dict]` - List workspace users
- `get_user_info(user_id: str) -> Dict` - Get user details
- `set_user_status(status_text: str, status_emoji: str = None) -> bool` - Set bot status

**Example Usage:**
```python
# Send notification to team channel
slack_tools.send_message(
    channel="#general",
    text="🚀 Deployment completed successfully! All systems are operational."
)

# Reply to a thread
slack_tools.send_message_thread(
    channel="#development",
    text="I've reviewed the code and it looks good to merge.",
    thread_ts="1234567890.123456"
)

# Upload file with comment
slack_tools.send_file(
    channel="#reports",
    file_path="./weekly_report.pdf",
    comment="Here's the weekly performance report for review."
)

# Get recent messages from channel
messages = slack_tools.get_channel_history(
    channel="#support",
    limit=50
)

# Search for specific messages
search_results = slack_tools.search_messages(
    query="bug report",
    count=20
)
```

### Microsoft Teams Tools
Integration with Microsoft Teams for messaging, meetings, and collaboration.

```python
from buddy.tools.microsoft_teams import MicrosoftTeamsTools

teams_tools = MicrosoftTeamsTools(
    tenant_id="your-tenant-id",           # Azure AD tenant
    client_id="your-client-id",           # Azure app client ID
    client_secret="your-client-secret",   # Azure app client secret
    webhook_url="https://outlook.office.com/webhook/..."  # Teams webhook
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[teams_tools],
    instructions="Help with Microsoft Teams communication."
)
```

**Messaging:**
- `send_message(text: str, title: str = None) -> Dict` - Send message via webhook
- `send_card_message(title: str, subtitle: str, text: str, actions: List[Dict] = None) -> Dict` - Send adaptive card
- `send_channel_message(team_id: str, channel_id: str, content: str) -> Dict` - Send message to specific channel

**Meeting Management:**
- `create_meeting(subject: str, start_time: str, end_time: str, attendees: List[str]) -> Dict` - Create Teams meeting
- `get_meetings(start_date: str = None, end_date: str = None) -> List[Dict]` - List scheduled meetings
- `join_meeting_url(meeting_id: str) -> str` - Get meeting join URL

**Team and Channel Operations:**
- `get_teams() -> List[Dict]` - List user's teams
- `get_channels(team_id: str) -> List[Dict]` - List channels in team
- `create_channel(team_id: str, name: str, description: str = "", type: str = "standard") -> Dict` - Create new channel

**File Sharing:**
- `upload_file(team_id: str, channel_id: str, file_path: str, message: str = None) -> Dict` - Upload file to channel
- `share_file_link(file_url: str, team_id: str, channel_id: str, message: str = None) -> Dict` - Share file link

**Example Usage:**
```python
# Send simple message
teams_tools.send_message(
    text="🎉 Project milestone completed! Great work everyone.",
    title="Project Update"
)

# Send interactive card
teams_tools.send_card_message(
    title="Approval Required",
    subtitle="Budget Request",
    text="Please review and approve the Q2 budget proposal.",
    actions=[
        {
            "type": "Action.OpenUrl",
            "title": "Review Document", 
            "url": "https://company.sharepoint.com/budget-q2"
        },
        {
            "type": "Action.Submit",
            "title": "Approve",
            "data": {"action": "approve", "id": "budget-q2-2024"}
        }
    ]
)

# Create team meeting
meeting = teams_tools.create_meeting(
    subject="Weekly Planning Meeting",
    start_time="2024-01-10T10:00:00Z",
    end_time="2024-01-10T11:00:00Z",
    attendees=["user1@company.com", "user2@company.com"]
)

# Upload file to team channel
teams_tools.upload_file(
    team_id="team-123",
    channel_id="channel-456", 
    file_path="./presentation.pptx",
    message="Here's the presentation for tomorrow's meeting."
)
```

## 🗄️ Database Tools

### PostgreSQL Tools
Complete PostgreSQL database interaction and management.

```python
from buddy.tools.postgres import PostgresTools

postgres_tools = PostgresTools(
    db_name="your_database",
    user="username",
    password="password",
    host="localhost",
    port=5432,
    run_queries=True,
    inspect_queries=True,
    summarize_tables=True,
    export_tables=True,
    table_schema="public"
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[postgres_tools],
    instructions="Help with PostgreSQL database operations."
)
```

**Database Schema:**
- `show_tables(schema: str = None) -> List[Dict]` - List all tables in schema
- `describe_table(table_name: str) -> Dict` - Get table structure and columns
- `get_table_indexes(table_name: str) -> List[Dict]` - Show table indexes
- `get_foreign_keys(table_name: str) -> List[Dict]` - Get foreign key relationships

**Query Operations:**
- `run_query(query: str) -> List[Dict]` - Execute SQL query and return results
- `inspect_query(query: str) -> Dict` - Analyze query execution plan
- `explain_query(query: str) -> str` - Get query execution plan

**Data Analysis:**
- `summarize_table(table_name: str, limit: int = 1000) -> Dict` - Get table statistics
- `count_rows(table_name: str, where_clause: str = None) -> int` - Count table rows
- `get_column_stats(table_name: str, column_name: str) -> Dict` - Column statistics

**Data Export:**
- `export_table_to_csv(table_name: str, file_path: str, limit: int = None) -> str` - Export table to CSV
- `export_query_to_csv(query: str, file_path: str) -> str` - Export query results to CSV

**Example Usage:**
```python
# List all tables
tables = postgres_tools.show_tables()

# Describe table structure
table_info = postgres_tools.describe_table("users")

# Run analytical query
results = postgres_tools.run_query("""
    SELECT 
        DATE_TRUNC('month', created_at) as month,
        COUNT(*) as user_count,
        AVG(age) as avg_age
    FROM users 
    WHERE created_at >= '2024-01-01'
    GROUP BY DATE_TRUNC('month', created_at)
    ORDER BY month;
""")

# Get table summary statistics
summary = postgres_tools.summarize_table("orders")
print(f"Table has {summary['row_count']} rows")
print(f"Average order value: ${summary['avg_order_value']:.2f}")

# Export data to CSV
postgres_tools.export_query_to_csv(
    query="SELECT * FROM sales WHERE date >= '2024-01-01'",
    file_path="./sales_2024.csv"
)
```

### SQL Tools
Generic SQL database tools supporting multiple database engines.

```python
from buddy.tools.sql import SQLTools

sql_tools = SQLTools(
    connection_string="postgresql://user:pass@localhost:5432/db",
    # Supports: postgresql, mysql, sqlite, mssql, oracle
    engine="postgresql",
    run_queries=True,
    create_tables=True,
    modify_schema=False  # Set to True for DDL operations
)
```

**Query Execution:**
- `execute_query(query: str) -> List[Dict]` - Execute any SQL query
- `execute_transaction(queries: List[str]) -> bool` - Execute multiple queries in transaction
- `bulk_insert(table_name: str, data: List[Dict]) -> int` - Bulk insert data

**Schema Operations:**
- `create_table(table_name: str, columns: Dict, primary_key: str = None) -> bool` - Create new table
- `alter_table(table_name: str, operation: str, column_def: str = None) -> bool` - Modify table structure
- `drop_table(table_name: str, cascade: bool = False) -> bool` - Delete table

**Example Usage:**
```python
# Execute complex query
results = sql_tools.execute_query("""
    WITH monthly_sales AS (
        SELECT 
            EXTRACT(MONTH FROM sale_date) as month,
            SUM(amount) as total_sales
        FROM sales 
        WHERE EXTRACT(YEAR FROM sale_date) = 2024
        GROUP BY EXTRACT(MONTH FROM sale_date)
    )
    SELECT 
        month,
        total_sales,
        LAG(total_sales) OVER (ORDER BY month) as prev_month_sales,
        total_sales - LAG(total_sales) OVER (ORDER BY month) as growth
    FROM monthly_sales
    ORDER BY month;
""")

# Bulk insert data
new_records = [
    {"name": "John Doe", "email": "john@example.com", "age": 30},
    {"name": "Jane Smith", "email": "jane@example.com", "age": 25}
]
inserted_count = sql_tools.bulk_insert("users", new_records)
```

## 📁 File & Data Processing

### CSV Tools
Comprehensive CSV file processing and analysis with SQL querying.

```python
from buddy.tools.csv_toolkit import CsvTools

csv_tools = CsvTools(
    csvs=["./data/sales.csv", "./data/customers.csv"],  # CSV files to work with
    row_limit=10000,                                    # Limit rows for large files
    read_csvs=True,
    list_csvs=True,
    query_csvs=True,                                   # Enable SQL queries via DuckDB
    read_column_names=True
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[csv_tools],
    instructions="Help with CSV data analysis and processing."
)
```

**File Operations:**
- `list_csv_files() -> List[str]` - List available CSV files
- `read_csv_file(file_path: str, limit: int = None) -> List[Dict]` - Read CSV file contents
- `get_columns(file_path: str) -> List[str]` - Get column names from CSV
- `write_csv_file(file_path: str, data: List[Dict], headers: List[str] = None) -> str` - Write data to CSV

**Data Querying (via DuckDB):**
- `query_csv_file(query: str) -> List[Dict]` - Execute SQL queries on CSV files
- `describe_csv(file_path: str) -> Dict` - Get statistical summary of CSV data
- `join_csvs(query: str) -> List[Dict]` - Join multiple CSV files with SQL

**Data Analysis:**
- `summarize_column(file_path: str, column: str) -> Dict` - Get column statistics
- `filter_csv(file_path: str, conditions: Dict) -> List[Dict]` - Filter CSV data
- `group_by_analysis(file_path: str, group_by: str, aggregations: Dict) -> List[Dict]` - Group and aggregate data

**Example Usage:**
```python
# Read CSV file with limit
data = csv_tools.read_csv_file("./data/sales.csv", limit=100)

# Execute SQL query on CSV
results = csv_tools.query_csv_file("""
    SELECT 
        product_category,
        SUM(sales_amount) as total_sales,
        COUNT(*) as transaction_count,
        AVG(sales_amount) as avg_sale
    FROM './data/sales.csv'
    GROUP BY product_category
    ORDER BY total_sales DESC;
""")

# Join multiple CSV files
joined_data = csv_tools.join_csvs("""
    SELECT 
        s.product_id,
        s.sales_amount,
        c.customer_name,
        c.customer_segment
    FROM './data/sales.csv' s
    LEFT JOIN './data/customers.csv' c
    ON s.customer_id = c.customer_id
    WHERE s.sales_date >= '2024-01-01';
""")

# Get column statistics
stats = csv_tools.summarize_column("./data/sales.csv", "sales_amount")
print(f"Average sale: ${stats['mean']:.2f}")
print(f"Maximum sale: ${stats['max']:.2f}")
```

### Pandas Tools
Advanced data manipulation and analysis using pandas.

```python
from buddy.tools.pandas import PandasTools

pandas_tools = PandasTools(
    enable_plotting=True,        # Enable matplotlib plots
    enable_statistics=True,      # Statistical functions
    enable_transformations=True, # Data transformations
    max_rows_display=1000       # Limit output size
)
```

**Data Loading:**
- `read_csv(file_path: str, **kwargs) -> str` - Load CSV into DataFrame
- `read_excel(file_path: str, sheet_name: str = None) -> str` - Load Excel file
- `read_json(file_path: str) -> str` - Load JSON data
- `read_parquet(file_path: str) -> str` - Load Parquet file

**Data Analysis:**
- `describe_dataframe(df_name: str) -> Dict` - Statistical summary
- `info_dataframe(df_name: str) -> Dict` - DataFrame structure info
- `correlation_matrix(df_name: str, columns: List[str] = None) -> Dict` - Correlation analysis
- `value_counts(df_name: str, column: str) -> Dict` - Count unique values

**Data Transformation:**
- `filter_dataframe(df_name: str, condition: str) -> str` - Filter DataFrame
- `group_by_aggregate(df_name: str, group_by: List[str], aggregations: Dict) -> str` - Group and aggregate
- `merge_dataframes(left_df: str, right_df: str, on: str, how: str = "inner") -> str` - Merge DataFrames
- `pivot_table(df_name: str, values: str, index: str, columns: str, aggfunc: str = "mean") -> str` - Create pivot table

**Visualization:**
- `plot_histogram(df_name: str, column: str, bins: int = 20) -> str` - Create histogram
- `plot_scatter(df_name: str, x_column: str, y_column: str) -> str` - Scatter plot
- `plot_line_chart(df_name: str, x_column: str, y_column: str) -> str` - Line chart
- `plot_heatmap(df_name: str, columns: List[str] = None) -> str` - Correlation heatmap

**Example Usage:**
```python
# Load and analyze data
df_id = pandas_tools.read_csv("./data/sales.csv")

# Get statistical summary
summary = pandas_tools.describe_dataframe(df_id)

# Filter and analyze
filtered_df = pandas_tools.filter_dataframe(
    df_name=df_id,
    condition="sales_amount > 1000 and product_category == 'Electronics'"
)

# Create aggregated analysis
monthly_sales = pandas_tools.group_by_aggregate(
    df_name=df_id,
    group_by=["year", "month"],
    aggregations={"sales_amount": ["sum", "mean", "count"]}
)

# Generate visualization
pandas_tools.plot_histogram(
    df_name=df_id,
    column="sales_amount",
    bins=30
)
```

## 🎨 AI/ML Tools

### DALL-E Image Generation
Generate images using OpenAI's DALL-E models.

```python
from buddy.tools.dalle import DalleTools

dalle_tools = DalleTools(
    model="dall-e-3",              # or "dall-e-2"
    n=1,                          # Number of images (DALL-E 3 supports only 1)
    size="1024x1024",             # Image resolution
    quality="standard",           # or "hd"
    style="vivid",                # or "natural"
    api_key="your-openai-key"     # or set OPENAI_API_KEY env var
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[dalle_tools],
    instructions="Help with image generation and visual content creation."
)
```

**Image Generation:**
- `generate_image(prompt: str, save_path: str = None) -> str` - Generate image from text prompt
- `edit_image(image_path: str, mask_path: str, prompt: str) -> str` - Edit existing image with mask
- `create_variation(image_path: str, n: int = 1) -> List[str]` - Create variations of existing image

**Example Usage:**
```python
# Generate image from prompt
image_path = dalle_tools.generate_image(
    prompt="A futuristic city skyline at sunset with flying cars and neon lights, digital art style",
    save_path="./generated_images/futuristic_city.png"
)

# Create multiple variations (DALL-E 2 only)
dalle_2 = DalleTools(model="dall-e-2", n=3)
variations = dalle_2.create_variation(
    image_path="./base_image.png",
    n=3
)
```

### ElevenLabs Speech Synthesis
Generate high-quality speech audio using ElevenLabs API.

```python
from buddy.tools.eleven_labs import ElevenLabsTools

elevenlabs_tools = ElevenLabsTools(
    api_key="your-elevenlabs-key",    # or set ELEVEN_LABS_API_KEY env var
    voice_id="default_voice_id",      # Specific voice to use
    model="eleven_monolingual_v1",    # Speech model
    stability=0.75,                   # Voice stability (0-1)
    similarity_boost=0.75,            # Similarity to original voice (0-1)
    optimize_streaming_latency=0      # Latency optimization level
)
```

**Speech Generation:**
- `text_to_speech(text: str, voice_id: str = None, save_path: str = None) -> str` - Convert text to speech
- `list_voices() -> List[Dict]` - Get available voices
- `get_voice_settings(voice_id: str) -> Dict` - Get voice configuration
- `clone_voice(audio_files: List[str], voice_name: str, description: str = None) -> Dict` - Clone voice from samples

**Example Usage:**
```python
# Generate speech from text
audio_path = elevenlabs_tools.text_to_speech(
    text="Welcome to our AI-powered customer service. How can I assist you today?",
    voice_id="professional_voice",
    save_path="./audio/greeting.mp3"
)

# List available voices
voices = elevenlabs_tools.list_voices()
for voice in voices:
    print(f"Voice: {voice['name']} - {voice['description']}")

# Clone custom voice
custom_voice = elevenlabs_tools.clone_voice(
    audio_files=["./voice_samples/sample1.wav", "./voice_samples/sample2.wav"],
    voice_name="Custom Assistant Voice",
    description="Professional customer service voice"
)
```

### OpenAI Tools
Access OpenAI's various AI models and capabilities.

```python
from buddy.tools.openai import OpenAITools

openai_tools = OpenAITools(
    api_key="your-openai-key",        # or set OPENAI_API_KEY env var
    enable_chat=True,                 # GPT chat models
    enable_embeddings=True,           # Text embeddings
    enable_moderation=True,           # Content moderation
    enable_fine_tuning=False,         # Fine-tuning operations
    enable_assistants=True            # OpenAI Assistants API
)
```

**Text Processing:**
- `generate_embeddings(text: str, model: str = "text-embedding-3-small") -> List[float]` - Generate text embeddings
- `moderate_content(text: str) -> Dict` - Check content for policy violations
- `complete_text(prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 150) -> str` - Text completion

**Assistant Management:**
- `create_assistant(name: str, instructions: str, model: str = "gpt-4") -> Dict` - Create OpenAI assistant
- `list_assistants() -> List[Dict]` - List available assistants
- `run_assistant(assistant_id: str, message: str) -> str` - Interact with assistant

**Example Usage:**
```python
# Generate embeddings for semantic search
embeddings = openai_tools.generate_embeddings(
    text="Machine learning and artificial intelligence",
    model="text-embedding-3-small"
)

# Check content moderation
moderation_result = openai_tools.moderate_content(
    text="User-generated content to check"
)

if moderation_result['flagged']:
    print("Content flagged for:", moderation_result['categories'])

# Create specialized assistant
assistant = openai_tools.create_assistant(
    name="Code Review Assistant",
    instructions="You are an expert code reviewer. Analyze code for best practices, bugs, and improvements.",
    model="gpt-4"
)

# Use assistant
review = openai_tools.run_assistant(
    assistant_id=assistant['id'],
    message="Please review this Python function: def calculate_average(numbers): return sum(numbers) / len(numbers)"
)
```

### Computer Vision Tools
Image analysis and processing using OpenCV.

```python
from buddy.tools.opencv import OpenCVTools

opencv_tools = OpenCVTools(
    enable_face_detection=True,
    enable_object_detection=True,
    enable_image_processing=True,
    enable_video_analysis=True,
    model_path="./models/"  # Path to ML models
)
```

**Image Analysis:**
- `detect_faces(image_path: str, save_result: bool = True) -> Dict` - Detect faces in image
- `detect_objects(image_path: str, confidence_threshold: float = 0.5) -> List[Dict]` - Object detection
- `extract_text_ocr(image_path: str, language: str = "eng") -> str` - Extract text from image
- `analyze_image_properties(image_path: str) -> Dict` - Get image dimensions, format, etc.

**Image Processing:**
- `resize_image(image_path: str, width: int, height: int, save_path: str) -> str` - Resize image
- `rotate_image(image_path: str, angle: float, save_path: str) -> str` - Rotate image
- `apply_filter(image_path: str, filter_type: str, save_path: str) -> str` - Apply image filters
- `crop_image(image_path: str, x: int, y: int, width: int, height: int, save_path: str) -> str` - Crop image

## 🌐 Web Automation Tools

### Selenium Web Automation
Complete web browser automation and testing.

```python
from buddy.tools.selenium_tool import SeleniumTools

selenium_tools = SeleniumTools(
    browser="chrome",              # chrome, firefox, edge, safari
    headless=False,               # Run in headless mode
    implicit_wait=10,             # Default wait time
    page_load_timeout=30,         # Page load timeout
    window_size=(1920, 1080),     # Browser window size
    user_agent="custom-agent",     # Custom user agent
    proxy_server=None,            # Proxy configuration
    enable_screenshots=True       # Enable screenshot capability
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[selenium_tools],
    instructions="Help with web automation and testing tasks."
)
```

**Browser Control:**
- `open_url(url: str) -> str` - Navigate to URL
- `go_back() -> str` - Go back in browser history
- `go_forward() -> str` - Go forward in browser history
- `refresh_page() -> str` - Refresh current page
- `close_browser() -> str` - Close browser instance
- `get_current_url() -> str` - Get current page URL
- `get_page_title() -> str` - Get page title

**Element Interaction:**
- `find_element(selector: str, by: str = "css") -> Dict` - Find single element
- `find_elements(selector: str, by: str = "css") -> List[Dict]` - Find multiple elements
- `click_element(selector: str) -> str` - Click on element
- `send_keys(selector: str, text: str) -> str` - Type text into element
- `clear_element(selector: str) -> str` - Clear element content
- `get_element_text(selector: str) -> str` - Get element text content
- `get_element_attribute(selector: str, attribute: str) -> str` - Get element attribute

**Form Handling:**
- `fill_form(form_data: Dict[str, str]) -> str` - Fill form fields
- `submit_form(form_selector: str) -> str` - Submit form
- `select_dropdown_option(selector: str, option: str, by_value: bool = False) -> str` - Select dropdown option
- `check_checkbox(selector: str, check: bool = True) -> str` - Check/uncheck checkbox
- `select_radio_button(selector: str) -> str` - Select radio button

**Wait Strategies:**
- `wait_for_element(selector: str, timeout: int = 10) -> str` - Wait for element to appear
- `wait_for_element_clickable(selector: str, timeout: int = 10) -> str` - Wait for clickable element
- `wait_for_text_present(text: str, timeout: int = 10) -> str` - Wait for text to appear
- `wait_for_page_load(timeout: int = 30) -> str` - Wait for page to fully load

**Data Extraction:**
- `scrape_table(table_selector: str) -> List[Dict]` - Extract table data
- `extract_links(base_url: str = None) -> List[Dict]` - Get all page links
- `extract_images(download_path: str = None) -> List[Dict]` - Get all images
- `get_page_source() -> str` - Get full HTML source

**Screenshots and Recording:**
- `take_screenshot(save_path: str = None) -> str` - Capture screenshot
- `take_element_screenshot(selector: str, save_path: str = None) -> str` - Screenshot specific element
- `start_video_recording() -> str` - Start recording browser session
- `stop_video_recording(save_path: str = None) -> str` - Stop recording and save

**Example Usage:**
```python
# Automate form submission
selenium_tools.open_url("https://example.com/contact")
selenium_tools.fill_form({
    "#name": "John Doe",
    "#email": "john@example.com",
    "#message": "Hello, I'm interested in your services."
})
selenium_tools.submit_form("#contact-form")

# Scrape product information
selenium_tools.open_url("https://shop.example.com/products")
products = selenium_tools.scrape_table(".product-table")

# Wait for dynamic content and extract
selenium_tools.wait_for_element(".dynamic-content")
content = selenium_tools.get_element_text(".dynamic-content")

# Take screenshot of specific element
selenium_tools.take_element_screenshot(".product-gallery", "./screenshots/product.png")
```

### Playwright Web Automation
Modern web automation with Playwright (faster and more reliable than Selenium).

```python
from buddy.tools.playwright_tool import PlaywrightTools

playwright_tools = PlaywrightTools(
    browser="chromium",           # chromium, firefox, webkit
    headless=True,               # Run headless by default
    viewport_size=(1920, 1080),  # Browser viewport
    timeout=30000,               # Default timeout in milliseconds
    slow_mo=0,                   # Slow down operations (ms)
    enable_video=True,           # Enable video recording
    enable_tracing=True          # Enable debugging traces
)
```

**Browser Management:**
- `launch_browser(context_options: Dict = None) -> str` - Launch browser with options
- `create_page() -> str` - Create new page/tab
- `navigate_to(url: str, wait_until: str = "load") -> str` - Navigate to URL
- `close_page(page_id: str = None) -> str` - Close specific page
- `close_browser() -> str` - Close entire browser

**Advanced Interactions:**
- `click(selector: str, modifiers: List[str] = None, position: Dict = None) -> str` - Advanced click
- `double_click(selector: str) -> str` - Double click element
- `right_click(selector: str) -> str` - Right click for context menu
- `hover(selector: str) -> str` - Hover over element
- `drag_and_drop(source_selector: str, target_selector: str) -> str` - Drag and drop

**Network and Performance:**
- `intercept_requests(url_pattern: str, response_override: Dict = None) -> str` - Mock network requests
- `wait_for_response(url_pattern: str, timeout: int = 30000) -> Dict` - Wait for API response
- `get_performance_metrics() -> Dict` - Get page performance metrics
- `block_resources(resource_types: List[str]) -> str` - Block specific resources (images, CSS, etc.)

**Example Usage:**
```python
# Test web application with network interception
playwright_tools.launch_browser()
playwright_tools.intercept_requests("*/api/users", {"status": 200, "body": {"users": []}})
playwright_tools.navigate_to("https://app.example.com")
playwright_tools.click("#load-users-btn")

# Performance testing
metrics = playwright_tools.get_performance_metrics()
print(f"Page load time: {metrics['loadEventEnd'] - metrics['navigationStart']}ms")
```

## 💼 Business & Productivity Tools

### Jira Project Management
Complete Jira integration for issue tracking and project management.

```python
from buddy.tools.jira import JiraTools

jira_tools = JiraTools(
    server_url="https://your-company.atlassian.net",
    username="your-email@company.com",
    token="your-api-token",  # Atlassian API token
    # Alternative: use password instead of token
    # password="your-password"
)

# Usage in agent
agent = Agent(
    model=OpenAIChat(),
    tools=[jira_tools],
    instructions="Help with Jira project management and issue tracking."
)
```

**Issue Management:**
- `get_issue(issue_key: str) -> Dict` - Get issue details by key
- `create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task", priority: str = "Medium") -> Dict` - Create new issue
- `update_issue(issue_key: str, fields: Dict) -> Dict` - Update issue fields
- `delete_issue(issue_key: str) -> bool` - Delete issue
- `assign_issue(issue_key: str, assignee: str) -> Dict` - Assign issue to user
- `transition_issue(issue_key: str, transition: str) -> Dict` - Change issue status

**Search and Filtering:**
- `search_issues(jql: str, max_results: int = 50) -> List[Dict]` - Search using JQL
- `get_issues_by_project(project_key: str, status: str = None) -> List[Dict]` - Get project issues
- `get_my_issues(status: str = None) -> List[Dict]` - Get issues assigned to current user
- `get_issues_by_assignee(assignee: str) -> List[Dict]` - Get issues by assignee

**Comments and Collaboration:**
- `add_comment(issue_key: str, comment: str) -> Dict` - Add comment to issue
- `get_comments(issue_key: str) -> List[Dict]` - Get all issue comments
- `update_comment(issue_key: str, comment_id: str, comment: str) -> Dict` - Edit comment
- `delete_comment(issue_key: str, comment_id: str) -> bool` - Delete comment

**Project Information:**
- `get_projects() -> List[Dict]` - List all accessible projects
- `get_project_info(project_key: str) -> Dict` - Get project details
- `get_issue_types(project_key: str) -> List[Dict]` - Get available issue types
- `get_project_versions(project_key: str) -> List[Dict]` - Get project versions

**Example Usage:**
```python
# Create a bug report
bug_issue = jira_tools.create_issue(
    project_key="PROJ",
    summary="User login fails on mobile devices",
    description="Users report being unable to log in using mobile Safari browser. Error message: 'Invalid credentials'",
    issue_type="Bug",
    priority="High"
)

# Search for open bugs
open_bugs = jira_tools.search_issues(
    jql="project = PROJ AND issuetype = Bug AND status = Open",
    max_results=20
)

# Add comment with investigation results
jira_tools.add_comment(
    issue_key="PROJ-123",
    comment="Investigated the issue. Found that the mobile login form has a CSS issue causing input validation to fail."
)

# Transition issue to In Progress
jira_tools.transition_issue(
    issue_key="PROJ-123",
    transition="Start Progress"
)
```

### Linear Project Management
Modern issue tracking with Linear.

```python
from buddy.tools.linear import LinearTools

linear_tools = LinearTools(
    api_key="lin_api_your_api_key",  # or set LINEAR_API_KEY env var
    team_id="your-team-id"           # Default team
)
```

**Issue Operations:**
- `create_issue(title: str, description: str, team_id: str = None, assignee_id: str = None, priority: int = 0) -> Dict` - Create issue
- `get_issue(issue_id: str) -> Dict` - Get issue by ID
- `update_issue(issue_id: str, title: str = None, description: str = None, state_id: str = None) -> Dict` - Update issue
- `delete_issue(issue_id: str) -> bool` - Archive issue
- `search_issues(query: str, team_id: str = None) -> List[Dict]` - Search issues

**Team Management:**
- `get_teams() -> List[Dict]` - List teams
- `get_team_members(team_id: str) -> List[Dict]` - Get team members
- `get_workflows(team_id: str) -> List[Dict]` - Get workflow states

**Example Usage:**
```python
# Create feature request
feature = linear_tools.create_issue(
    title="Add dark mode support",
    description="Users have requested a dark mode option for better usability in low-light conditions.",
    priority=2  # High priority
)

# Search for related issues
related = linear_tools.search_issues("dark mode OR theme")
```

### Google Calendar Integration
Calendar management and scheduling.

```python
from buddy.tools.googlecalendar import GoogleCalendarTools

calendar_tools = GoogleCalendarTools(
    credentials_path="path/to/credentials.json",  # Google API credentials
    token_path="path/to/token.json",             # OAuth token
    calendar_id="primary"                        # Default calendar ID
)
```

**Event Management:**
- `create_event(title: str, start_time: str, end_time: str, description: str = None, attendees: List[str] = None) -> Dict` - Create calendar event
- `get_events(start_date: str = None, end_date: str = None, max_results: int = 10) -> List[Dict]` - Get calendar events
- `update_event(event_id: str, title: str = None, start_time: str = None, end_time: str = None) -> Dict` - Update event
- `delete_event(event_id: str) -> bool` - Delete event
- `find_free_time(duration_minutes: int, start_date: str, end_date: str) -> List[Dict]` - Find available time slots

**Calendar Operations:**
- `list_calendars() -> List[Dict]` - List accessible calendars
- `create_calendar(name: str, description: str = None) -> Dict` - Create new calendar
- `share_calendar(calendar_id: str, email: str, role: str = "reader") -> Dict` - Share calendar

**Example Usage:**
```python
# Schedule team meeting
meeting = calendar_tools.create_event(
    title="Weekly Team Standup",
    start_time="2024-01-10T10:00:00Z",
    end_time="2024-01-10T11:00:00Z",
    description="Weekly progress review and planning session",
    attendees=["team1@company.com", "team2@company.com"]
)

# Find next available 2-hour slot
free_slots = calendar_tools.find_free_time(
    duration_minutes=120,
    start_date="2024-01-10",
    end_date="2024-01-17"
)
```

### Google Sheets Integration
Spreadsheet automation and data management.

```python
from buddy.tools.googlesheets import GoogleSheetsTools

sheets_tools = GoogleSheetsTools(
    credentials_path="path/to/credentials.json",
    token_path="path/to/token.json"
)
```

**Sheet Operations:**
- `create_spreadsheet(title: str, sheet_names: List[str] = None) -> Dict` - Create new spreadsheet
- `open_spreadsheet(spreadsheet_id: str) -> Dict` - Open existing spreadsheet
- `list_spreadsheets() -> List[Dict]` - List accessible spreadsheets
- `duplicate_sheet(spreadsheet_id: str, sheet_id: int, new_name: str) -> Dict` - Duplicate worksheet

**Data Operations:**
- `read_range(spreadsheet_id: str, range_name: str) -> List[List]` - Read cell range
- `write_range(spreadsheet_id: str, range_name: str, values: List[List]) -> Dict` - Write to range
- `append_rows(spreadsheet_id: str, sheet_name: str, values: List[List]) -> Dict` - Append data
- `clear_range(spreadsheet_id: str, range_name: str) -> Dict` - Clear cell range
- `batch_update(spreadsheet_id: str, requests: List[Dict]) -> Dict` - Batch operations

**Formatting and Analysis:**
- `format_cells(spreadsheet_id: str, range_name: str, format_options: Dict) -> Dict` - Format cells
- `create_chart(spreadsheet_id: str, sheet_id: int, chart_config: Dict) -> Dict` - Create chart
- `add_filter(spreadsheet_id: str, sheet_id: int, range_name: str) -> Dict` - Add data filter
- `calculate_formulas(spreadsheet_id: str, formulas: List[str]) -> List` - Calculate formulas

**Example Usage:**
```python
# Create expense tracking spreadsheet
spreadsheet = sheets_tools.create_spreadsheet(
    title="Q1 2024 Expense Tracking",
    sheet_names=["Expenses", "Categories", "Summary"]
)

# Add expense data
expenses_data = [
    ["Date", "Category", "Amount", "Description"],
    ["2024-01-05", "Travel", "120.50", "Client visit transportation"],
    ["2024-01-06", "Meals", "45.00", "Business lunch"],
    ["2024-01-07", "Office", "230.00", "Office supplies"]
]

sheets_tools.write_range(
    spreadsheet_id=spreadsheet['spreadsheetId'],
    range_name="Expenses!A1:D4",
    values=expenses_data
)

# Create summary with formulas
summary_formulas = [
    ["Total Expenses", "=SUM(Expenses!C2:C1000)"],
    ["Average Per Day", "=AVERAGE(Expenses!C2:C1000)"],
    ["Max Expense", "=MAX(Expenses!C2:C1000)"]
]

sheets_tools.write_range(
    spreadsheet_id=spreadsheet['spreadsheetId'],
    range_name="Summary!A1:B3",
    values=summary_formulas
)
```

### HubSpot CRM Integration
Customer relationship management and sales automation.

```python
from buddy.tools.hubspot import HubSpotTools

hubspot_tools = HubSpotTools(
    api_key="your-hubspot-api-key"  # Private app access token
)
```

**Contact Management:**
- `create_contact(email: str, firstname: str = None, lastname: str = None, company: str = None, phone: str = None, properties: Dict = None) -> Dict` - Create contact
- `get_contact(contact_id: str) -> Dict` - Get contact by ID
- `get_contact_by_email(email: str) -> Dict` - Get contact by email
- `update_contact(contact_id: str, properties: Dict) -> Dict` - Update contact properties
- `delete_contact(contact_id: str) -> bool` - Delete contact
- `search_contacts(query: str, properties: List[str] = None) -> List[Dict]` - Search contacts

**Company Management:**
- `create_company(name: str, domain: str = None, properties: Dict = None) -> Dict` - Create company
- `get_company(company_id: str) -> Dict` - Get company details
- `update_company(company_id: str, properties: Dict) -> Dict` - Update company
- `associate_contact_to_company(contact_id: str, company_id: str) -> Dict` - Link contact to company

**Deal Management:**
- `create_deal(dealname: str, amount: float = None, closedate: str = None, dealstage: str = None) -> Dict` - Create deal
- `get_deal(deal_id: str) -> Dict` - Get deal details
- `update_deal(deal_id: str, properties: Dict) -> Dict` - Update deal
- `get_deals_by_stage(stage: str) -> List[Dict]` - Get deals by pipeline stage

**Example Usage:**
```python
# Create lead from website form
contact = hubspot_tools.create_contact(
    email="john.doe@example.com",
    firstname="John",
    lastname="Doe",
    company="Example Corp",
    phone="+1-555-123-4567",
    properties={
        "lead_source": "Website form",
        "lifecycle_stage": "lead"
    }
)

# Create associated deal
deal = hubspot_tools.create_deal(
    dealname="Example Corp - Website Redesign",
    amount=25000.00,
    dealstage="appointmentscheduled",
    closedate="2024-03-15"
)
```

## 🛠️ Utility & System Tools

### Calculator & Math
Mathematical computations and formula evaluation.

```python
from buddy.tools.calculator import CalculatorTools

calc_tools = CalculatorTools()
```

**Basic Operations:**
- `calculate(expression: str) -> float` - Evaluate mathematical expression
- `add(a: float, b: float) -> float` - Addition
- `subtract(a: float, b: float) -> float` - Subtraction
- `multiply(a: float, b: float) -> float` - Multiplication
- `divide(a: float, b: float) -> float` - Division with zero check

**Advanced Math:**
- `power(base: float, exponent: float) -> float` - Exponentiation
- `square_root(number: float) -> float` - Square root
- `factorial(n: int) -> int` - Factorial calculation
- `percentage(value: float, total: float) -> float` - Percentage calculation
- `compound_interest(principal: float, rate: float, time: float, frequency: int = 1) -> float` - Financial calculation

**Scientific Functions:**
- `sin(angle_radians: float) -> float` - Sine function
- `cos(angle_radians: float) -> float` - Cosine function
- `tan(angle_radians: float) -> float` - Tangent function
- `log(number: float, base: float = 10) -> float` - Logarithm
- `natural_log(number: float) -> float` - Natural logarithm

**Example Usage:**
```python
# Complex calculation
result = calc_tools.calculate("2 * (3 + 4) ** 2 - 15")  # = 83

# Financial calculation
investment_value = calc_tools.compound_interest(
    principal=10000,
    rate=0.07,  # 7% annual
    time=5,     # 5 years
    frequency=12  # Monthly compounding
)
```

### Date & Time Utilities
Date/time manipulation and timezone handling.

```python
from buddy.tools.datetime import DateTimeTools

datetime_tools = DateTimeTools(
    default_timezone="UTC"  # Default timezone for operations
)
```

**Current Date/Time:**
- `now(timezone: str = None) -> str` - Current datetime in timezone
- `today(timezone: str = None) -> str` - Current date
- `timestamp() -> float` - Unix timestamp
- `utc_now() -> str` - Current UTC datetime

**Date Formatting:**
- `format_date(date_str: str, output_format: str = "%Y-%m-%d") -> str` - Format date string
- `parse_date(date_str: str, input_format: str = None) -> datetime` - Parse date string
- `to_iso_format(date_str: str) -> str` - Convert to ISO format
- `human_readable(date_str: str) -> str` - Human-friendly format

**Date Arithmetic:**
- `add_days(date_str: str, days: int) -> str` - Add days to date
- `add_months(date_str: str, months: int) -> str` - Add months to date
- `date_difference(start_date: str, end_date: str, unit: str = "days") -> int` - Calculate difference
- `is_weekend(date_str: str) -> bool` - Check if date is weekend
- `is_business_day(date_str: str) -> bool` - Check if business day

**Timezone Operations:**
- `convert_timezone(datetime_str: str, from_tz: str, to_tz: str) -> str` - Convert between timezones
- `list_timezones() -> List[str]` - List available timezones
- `get_timezone_info(timezone: str) -> Dict` - Timezone information

**Example Usage:**
```python
# Schedule meeting 3 business days from now
meeting_date = datetime_tools.add_days(
    datetime_tools.today(),
    3
)

# Convert to client timezone
client_time = datetime_tools.convert_timezone(
    "2024-01-10 14:00:00",
    from_tz="UTC",
    to_tz="America/New_York"
)

# Check project deadline
days_remaining = datetime_tools.date_difference(
    datetime_tools.today(),
    "2024-06-30",
    unit="days"
)
```

### QR Code Generator
QR code creation and customization.

```python
from buddy.tools.qrcode import QRCodeTools

qr_tools = QRCodeTools(
    output_dir="./qr_codes",  # Output directory
    default_size=10,          # Default module size
    border=4                  # Default border size
)
```

**QR Code Generation:**
- `generate_qr(data: str, filename: str = None, size: int = None, border: int = None) -> str` - Generate basic QR code
- `generate_url_qr(url: str, filename: str = None) -> str` - QR code for URL
- `generate_wifi_qr(ssid: str, password: str, security: str = "WPA", filename: str = None) -> str` - WiFi QR code
- `generate_contact_qr(name: str, phone: str = None, email: str = None, filename: str = None) -> str` - Contact QR code

**Customization:**
- `generate_styled_qr(data: str, filename: str, fill_color: str = "black", back_color: str = "white", border_color: str = None) -> str` - Custom colors
- `generate_logo_qr(data: str, logo_path: str, filename: str) -> str` - QR with embedded logo
- `batch_generate(data_list: List[str], prefix: str = "qr") -> List[str]` - Generate multiple QR codes

**Reading and Validation:**
- `read_qr(image_path: str) -> str` - Extract data from QR code image
- `validate_qr(image_path: str, expected_data: str) -> bool` - Validate QR code content

**Example Usage:**
```python
# Generate restaurant menu QR
menu_qr = qr_tools.generate_url_qr(
    url="https://restaurant.com/menu",
    filename="menu_qr.png"
)

# WiFi access QR for guests
wifi_qr = qr_tools.generate_wifi_qr(
    ssid="GuestNetwork",
    password="guest123",
    security="WPA",
    filename="guest_wifi.png"
)

# Contact card for business
contact_qr = qr_tools.generate_contact_qr(
    name="John Smith",
    phone="+1-555-123-4567",
    email="john.smith@company.com",
    filename="business_card.png"
)
```

### Weather Information
Weather data and forecasting.

```python
from buddy.tools.weather import WeatherTools

weather_tools = WeatherTools(
    api_key="your-openweathermap-api-key"  # OpenWeatherMap API key
)
```

**Current Weather:**
- `get_current_weather(location: str, units: str = "metric") -> Dict` - Current weather conditions
- `get_weather_by_coords(latitude: float, longitude: float, units: str = "metric") -> Dict` - Weather by coordinates
- `get_weather_summary(location: str) -> str` - Human-readable weather summary

**Forecasting:**
- `get_forecast(location: str, days: int = 5, units: str = "metric") -> List[Dict]` - Weather forecast
- `get_hourly_forecast(location: str, hours: int = 24, units: str = "metric") -> List[Dict]` - Hourly forecast
- `get_extended_forecast(location: str, days: int = 14) -> List[Dict]` - Extended forecast

**Historical Data:**
- `get_historical_weather(location: str, date: str, units: str = "metric") -> Dict` - Historical weather
- `get_weather_trends(location: str, start_date: str, end_date: str) -> Dict` - Weather trends

**Alerts and Monitoring:**
- `get_weather_alerts(location: str) -> List[Dict]` - Active weather alerts
- `check_rain_probability(location: str, threshold: float = 0.5) -> bool` - Rain likelihood
- `get_uv_index(location: str) -> Dict` - UV index information

**Example Usage:**
```python
# Check weather for outdoor event planning
weather = weather_tools.get_current_weather(
    location="New York, NY",
    units="imperial"  # Fahrenheit
)

# Get weekend forecast
weekend_forecast = weather_tools.get_forecast(
    location="San Francisco, CA",
    days=3
)

# Check for weather alerts
alerts = weather_tools.get_weather_alerts("Miami, FL")
if alerts:
    print(f"Weather alerts active: {len(alerts)}")

# Rain probability for tomorrow
rain_likely = weather_tools.check_rain_probability(
    location="Seattle, WA",
    threshold=0.7  # 70% probability
)
```

## 📱 Social Media & Marketing Tools

### Twitter/X Integration
Twitter posting, monitoring, and engagement.

```python
from buddy.tools.twitter import TwitterTools

twitter_tools = TwitterTools(
    api_key="your-api-key",
    api_secret="your-api-secret",
    access_token="your-access-token",
    access_token_secret="your-access-token-secret",
    bearer_token="your-bearer-token"  # For API v2
)
```

**Tweet Management:**
- `post_tweet(text: str, media_ids: List[str] = None, reply_to: str = None) -> Dict` - Post tweet
- `delete_tweet(tweet_id: str) -> bool` - Delete tweet
- `get_tweet(tweet_id: str) -> Dict` - Get tweet details
- `retweet(tweet_id: str) -> Dict` - Retweet
- `quote_tweet(tweet_id: str, comment: str) -> Dict` - Quote tweet with comment

**Media Upload:**
- `upload_image(image_path: str, alt_text: str = None) -> str` - Upload image
- `upload_video(video_path: str) -> str` - Upload video
- `upload_gif(gif_path: str) -> str` - Upload GIF

**Engagement:**
- `like_tweet(tweet_id: str) -> bool` - Like tweet
- `unlike_tweet(tweet_id: str) -> bool` - Remove like
- `follow_user(username: str) -> bool` - Follow user
- `unfollow_user(username: str) -> bool` - Unfollow user
- `reply_to_tweet(tweet_id: str, text: str) -> Dict` - Reply to tweet

**Search and Monitoring:**
- `search_tweets(query: str, count: int = 10, result_type: str = "recent") -> List[Dict]` - Search tweets
- `get_user_tweets(username: str, count: int = 20) -> List[Dict]` - Get user's tweets
- `get_mentions(count: int = 20) -> List[Dict]` - Get mentions
- `get_trending_topics(location_id: int = 1) -> List[Dict]` - Trending topics

**Analytics:**
- `get_tweet_metrics(tweet_id: str) -> Dict` - Tweet engagement metrics
- `get_follower_count(username: str) -> int` - Follower count
- `get_user_analytics(username: str) -> Dict` - User analytics

**Example Usage:**
```python
# Schedule product announcement
# Upload product image first
image_id = twitter_tools.upload_image(
    image_path="product_launch.png",
    alt_text="New product launch announcement with features highlighted"
)

# Post announcement tweet
announcement = twitter_tools.post_tweet(
    text="🚀 Excited to announce our new AI-powered analytics dashboard! "
          "Real-time insights, intelligent predictions, and beautiful visualizations. "
          "#ProductLaunch #Analytics #AI",
    media_ids=[image_id]
)

# Monitor brand mentions
mentions = twitter_tools.search_tweets(
    query="@YourBrand OR YourProduct",
    count=50,
    result_type="recent"
)

# Engage with customers
for mention in mentions:
    if "question" in mention["text"].lower() or "help" in mention["text"].lower():
        twitter_tools.reply_to_tweet(
            tweet_id=mention["id"],
            text="Hi! Thanks for reaching out. We'd be happy to help! "
                 "Please DM us with more details and we'll get back to you quickly. 😊"
        )
```

### LinkedIn Professional Network
Professional networking and content marketing.

```python
from buddy.tools.linkedin import LinkedInTools

linkedin_tools = LinkedInTools(
    access_token="your-linkedin-access-token",
    # OAuth 2.0 token with required scopes: 
    # r_liteprofile, r_emailaddress, w_member_social
)
```

**Profile Management:**
- `get_profile() -> Dict` - Get current user profile
- `update_profile(headline: str = None, summary: str = None, location: str = None) -> Dict` - Update profile
- `get_user_profile(user_id: str) -> Dict` - Get another user's profile
- `search_people(keywords: str, location: str = None) -> List[Dict]` - Search for people

**Content Publishing:**
- `post_update(text: str, visibility: str = "PUBLIC") -> Dict` - Post text update
- `post_article(title: str, content: str, visibility: str = "PUBLIC") -> Dict` - Publish long-form article
- `share_content(url: str, comment: str = None) -> Dict` - Share external content
- `upload_image(image_path: str) -> str` - Upload image for posts

**Network Management:**
- `get_connections(count: int = 500) -> List[Dict]` - Get connections
- `send_connection_request(user_id: str, message: str = None) -> bool` - Send connection request
- `get_connection_requests() -> List[Dict]` - Pending requests
- `accept_connection(invitation_id: str) -> bool` - Accept connection

**Company Pages:**
- `get_company_profile(company_id: str) -> Dict` - Get company information
- `post_company_update(company_id: str, text: str) -> Dict` - Post as company
- `get_company_followers(company_id: str) -> List[Dict]` - Company followers

**Example Usage:**
```python
# Share professional achievement
achievement_post = linkedin_tools.post_update(
    text="🎉 Excited to share that our AI automation project has helped clients "
          "reduce manual processing time by 75%! Grateful to work with such an "
          "innovative team. #AI #Automation #Success",
    visibility="PUBLIC"
)

# Publish thought leadership article
article = linkedin_tools.post_article(
    title="The Future of AI in Business Automation",
    content="""
    As artificial intelligence continues to evolve, businesses are finding
    innovative ways to streamline operations and enhance productivity...
    
    [Full article content with insights and analysis]
    """,
    visibility="PUBLIC"
)

# Network with industry professionals
industry_contacts = linkedin_tools.search_people(
    keywords="AI engineer data science",
    location="San Francisco Bay Area"
)

# Send personalized connection requests
for contact in industry_contacts[:5]:  # Connect with top 5 matches
    linkedin_tools.send_connection_request(
        user_id=contact["id"],
        message="Hi! I noticed we both work in AI/ML space. Would love to connect "
               "and share insights about the latest developments in our field."
    )
```

### Facebook Marketing
Facebook page management and advertising.

```python
from buddy.tools.facebook import FacebookTools

facebook_tools = FacebookTools(
    access_token="your-facebook-access-token",
    page_id="your-facebook-page-id"  # For page management
)
```

**Page Management:**
- `post_to_page(message: str, link: str = None, photo_path: str = None) -> Dict` - Post to Facebook page
- `get_page_posts(limit: int = 25) -> List[Dict]` - Get page posts
- `delete_post(post_id: str) -> bool` - Delete post
- `get_page_insights() -> Dict` - Page analytics

**Media Upload:**
- `upload_photo(photo_path: str, caption: str = None) -> Dict` - Upload photo
- `upload_video(video_path: str, title: str = None, description: str = None) -> Dict` - Upload video
- `create_photo_album(name: str, description: str = None) -> str` - Create photo album

**Audience Engagement:**
- `get_post_comments(post_id: str) -> List[Dict]` - Get post comments
- `reply_to_comment(comment_id: str, message: str) -> Dict` - Reply to comment
- `like_post(post_id: str) -> bool` - Like post
- `share_post(post_id: str, message: str = None) -> Dict` - Share post

**Advertising (Meta Business API):**
- `create_ad_campaign(name: str, objective: str, budget_amount: int, target_audience: Dict) -> str` - Create ad campaign
- `get_campaign_performance(campaign_id: str) -> Dict` - Campaign metrics
- `pause_campaign(campaign_id: str) -> bool` - Pause campaign
- `resume_campaign(campaign_id: str) -> bool` - Resume campaign

**Example Usage:**
```python
# Post promotional content with image
promo_post = facebook_tools.upload_photo(
    photo_path="summer_sale.jpg",
    caption="☀️ SUMMER SALE ALERT! ☀️\n\n"
           "Get up to 50% off on all summer essentials! "
           "Limited time offer - don't miss out! 🛍️\n\n"
           "#SummerSale #Shopping #Deals"
)

# Monitor and respond to comments
comments = facebook_tools.get_post_comments(promo_post["id"])
for comment in comments:
    if "price" in comment["message"].lower():
        facebook_tools.reply_to_comment(
            comment_id=comment["id"],
            message="Hi! Thanks for your interest! Please check our website "
                   "for detailed pricing or send us a direct message. 😊"
        )

# Create targeted ad campaign
campaign_id = facebook_tools.create_ad_campaign(
    name="Summer Collection 2024",
    objective="CONVERSIONS",
    budget_amount=500,  # $500 budget
    target_audience={
        "age_min": 25,
        "age_max": 45,
        "genders": ["female"],
        "interests": ["fashion", "summer clothing", "online shopping"],
        "locations": ["United States"]
    }
)
```

### Instagram Marketing
Instagram content creation and engagement.

```python
from buddy.tools.instagram import InstagramTools

instagram_tools = InstagramTools(
    access_token="your-instagram-access-token",
    instagram_business_id="your-instagram-business-account-id"
)
```

**Content Publishing:**
- `post_photo(image_path: str, caption: str, hashtags: List[str] = None) -> Dict` - Post photo
- `post_video(video_path: str, caption: str, hashtags: List[str] = None) -> Dict` - Post video  
- `post_carousel(media_paths: List[str], caption: str, hashtags: List[str] = None) -> Dict` - Multi-photo post
- `post_story(media_path: str, duration: int = 15) -> Dict` - Post Instagram story

**Content Management:**
- `get_posts(limit: int = 25) -> List[Dict]` - Get account posts
- `get_post_details(post_id: str) -> Dict` - Get post information
- `delete_post(post_id: str) -> bool` - Delete post
- `archive_post(post_id: str) -> bool` - Archive post

**Engagement:**
- `get_post_comments(post_id: str) -> List[Dict]` - Get post comments
- `reply_to_comment(comment_id: str, text: str) -> Dict` - Reply to comment
- `like_post(post_id: str) -> bool` - Like post
- `get_mentions() -> List[Dict]` - Get mentions

**Analytics:**
- `get_account_insights(metrics: List[str], period: str = "day") -> Dict` - Account analytics
- `get_post_insights(post_id: str) -> Dict` - Post performance
- `get_story_insights(story_id: str) -> Dict` - Story analytics
- `get_audience_insights() -> Dict` - Audience demographics

**Hashtag Research:**
- `search_hashtags(query: str) -> List[Dict]` - Search hashtags
- `get_hashtag_posts(hashtag: str, limit: int = 20) -> List[Dict]` - Posts with hashtag
- `analyze_hashtag_performance(hashtags: List[str]) -> Dict` - Hashtag analytics

**Example Usage:**
```python
# Post product showcase with optimized hashtags
product_post = instagram_tools.post_photo(
    image_path="new_product.jpg",
    caption="✨ Introducing our latest innovation! ✨\n\n"
           "Designed with you in mind - combining style, "
           "functionality, and sustainability. What do you think? 💭",
    hashtags=[
        "#newproduct", "#innovation", "#sustainable", "#design",
        "#lifestyle", "#quality", "#handmade", "#shoplocal",
        "#ecofriendly", "#mindfulbuying"
    ]
)

# Monitor engagement and respond
post_comments = instagram_tools.get_post_comments(product_post["id"])
for comment in post_comments:
    if any(word in comment["text"].lower() for word in ["love", "amazing", "great"]):
        instagram_tools.reply_to_comment(
            comment_id=comment["id"],
            text="Thank you so much! ❤️ We really appreciate your support!"
        )

# Analyze hashtag performance for future posts
hashtag_analysis = instagram_tools.analyze_hashtag_performance([
    "newproduct", "innovation", "sustainable", "design", "lifestyle"
])

# Post behind-the-scenes story
instagram_tools.post_story(
    media_path="behind_scenes.mp4",
    duration=15
)
```

### YouTube Content Management
YouTube video management and analytics.

```python
from buddy.tools.youtube import YouTubeTools

youtube_tools = YouTubeTools(
    api_key="your-youtube-api-key",
    channel_id="your-youtube-channel-id"
)
```

**Video Management:**
- `upload_video(video_path: str, title: str, description: str, tags: List[str] = None, privacy: str = "public") -> Dict` - Upload video
- `update_video(video_id: str, title: str = None, description: str = None, tags: List[str] = None) -> Dict` - Update video
- `delete_video(video_id: str) -> bool` - Delete video
- `get_video_details(video_id: str) -> Dict` - Get video information

**Channel Management:**
- `get_channel_info() -> Dict` - Get channel information
- `get_channel_videos(max_results: int = 50) -> List[Dict]` - Get channel videos
- `update_channel_info(title: str = None, description: str = None) -> Dict` - Update channel
- `get_playlists() -> List[Dict]` - Get channel playlists

**Analytics:**
- `get_video_analytics(video_id: str, metrics: List[str]) -> Dict` - Video analytics
- `get_channel_analytics(start_date: str, end_date: str, metrics: List[str]) -> Dict` - Channel analytics
- `get_subscriber_count() -> int` - Current subscriber count
- `get_watch_time_report(start_date: str, end_date: str) -> Dict` - Watch time analytics

**Search and Discovery:**
- `search_videos(query: str, max_results: int = 25) -> List[Dict]` - Search YouTube videos
- `get_trending_videos(region: str = "US", category: str = None) -> List[Dict]` - Trending videos
- `get_video_suggestions(video_id: str) -> List[Dict]` - Related video suggestions

**Example Usage:**
```python
# Upload tutorial video
tutorial_upload = youtube_tools.upload_video(
    video_path="ai_tutorial.mp4",
    title="Complete Guide to AI Agent Development - 2024 Tutorial",
    description="""
    🤖 Learn how to build powerful AI agents from scratch!
    
    In this comprehensive tutorial, you'll discover:
    ⭐ Setting up your development environment
    ⭐ Understanding AI agent architectures  
    ⭐ Implementing natural language processing
    ⭐ Building conversation flows
    ⭐ Testing and deployment strategies
    
    📚 Resources mentioned:
    - GitHub repository: https://github.com/your-repo
    - Documentation: https://your-docs.com
    
    💬 Questions? Drop them in the comments!
    
    #AI #MachineLearning #Tutorial #Programming #TechEducation
    """,
    tags=["AI", "machine learning", "tutorial", "programming", "python", "agents"],
    privacy="public"
)

# Check performance metrics
video_analytics = youtube_tools.get_video_analytics(
    video_id=tutorial_upload["id"],
    metrics=["views", "likes", "comments", "watchTime", "averageViewDuration"]
)

print(f"Video performance: {video_analytics['views']} views, "
      f"{video_analytics['likes']} likes, "
      f"{video_analytics['averageViewDuration']} avg watch time")

# Get channel growth metrics
channel_analytics = youtube_tools.get_channel_analytics(
    start_date="2024-01-01",
    end_date="2024-01-31", 
    metrics=["views", "subscribersGained", "watchTime", "estimatedRevenue"]
)
```

## 💰 Financial & Payment Tools

### Stripe Payment Processing
Payment processing and subscription management.

```python
from buddy.tools.stripe import StripeTools

stripe_tools = StripeTools(
    api_key="sk_test_your_stripe_secret_key",  # Use sk_live_ for production
    webhook_secret="whsec_your_webhook_secret"   # For webhook verification
)
```

**Payment Processing:**
- `create_payment_intent(amount: int, currency: str = "usd", customer_id: str = None, metadata: Dict = None) -> Dict` - Create payment intent
- `confirm_payment_intent(payment_intent_id: str, payment_method: str = None) -> Dict` - Confirm payment
- `capture_payment_intent(payment_intent_id: str, amount: int = None) -> Dict` - Capture authorized payment
- `cancel_payment_intent(payment_intent_id: str) -> Dict` - Cancel payment
- `refund_payment(payment_intent_id: str, amount: int = None, reason: str = None) -> Dict` - Process refund

**Customer Management:**
- `create_customer(email: str, name: str = None, phone: str = None, metadata: Dict = None) -> Dict` - Create customer
- `get_customer(customer_id: str) -> Dict` - Get customer details
- `update_customer(customer_id: str, email: str = None, name: str = None, metadata: Dict = None) -> Dict` - Update customer
- `delete_customer(customer_id: str) -> bool` - Delete customer
- `list_customers(limit: int = 10, email: str = None) -> List[Dict]` - List customers

**Subscription Management:**
- `create_subscription(customer_id: str, price_id: str, trial_period_days: int = None) -> Dict` - Create subscription
- `get_subscription(subscription_id: str) -> Dict` - Get subscription details
- `update_subscription(subscription_id: str, price_id: str = None, quantity: int = None) -> Dict` - Update subscription
- `cancel_subscription(subscription_id: str, at_period_end: bool = True) -> Dict` - Cancel subscription
- `pause_subscription(subscription_id: str, behavior: str = "mark_uncollectible") -> Dict` - Pause subscription

**Product and Pricing:**
- `create_product(name: str, description: str = None, metadata: Dict = None) -> Dict` - Create product
- `create_price(product_id: str, unit_amount: int, currency: str = "usd", recurring: Dict = None) -> Dict` - Create price
- `get_prices(product_id: str = None, active: bool = True) -> List[Dict]` - List prices

**Example Usage:**
```python
# Process one-time payment
customer = stripe_tools.create_customer(
    email="customer@example.com",
    name="John Smith",
    metadata={"order_id": "ORD-123"}
)

payment_intent = stripe_tools.create_payment_intent(
    amount=2999,  # $29.99 in cents
    currency="usd",
    customer_id=customer["id"],
    metadata={
        "product": "Premium Plan",
        "order_id": "ORD-123"
    }
)

# Create subscription service
product = stripe_tools.create_product(
    name="Premium AI Assistant",
    description="Monthly subscription to premium AI features"
)

monthly_price = stripe_tools.create_price(
    product_id=product["id"],
    unit_amount=1999,  # $19.99/month
    recurring={"interval": "month"}
)

subscription = stripe_tools.create_subscription(
    customer_id=customer["id"],
    price_id=monthly_price["id"],
    trial_period_days=14  # 14-day free trial
)
```

### PayPal Integration
PayPal payment processing and merchant services.

```python
from buddy.tools.paypal import PayPalTools

paypal_tools = PayPalTools(
    client_id="your-paypal-client-id",
    client_secret="your-paypal-client-secret",
    environment="sandbox"  # Use "live" for production
)
```

**Payment Processing:**
- `create_payment(amount: float, currency: str = "USD", description: str = None) -> Dict` - Create payment
- `execute_payment(payment_id: str, payer_id: str) -> Dict` - Execute approved payment
- `get_payment(payment_id: str) -> Dict` - Get payment details
- `refund_payment(sale_id: str, amount: float = None) -> Dict` - Process refund

**Invoicing:**
- `create_invoice(recipient_email: str, amount: float, currency: str = "USD", note: str = None) -> Dict` - Create invoice
- `send_invoice(invoice_id: str) -> Dict` - Send invoice to recipient
- `get_invoice(invoice_id: str) -> Dict` - Get invoice details
- `cancel_invoice(invoice_id: str) -> Dict` - Cancel sent invoice

**Subscription Billing:**
- `create_billing_plan(name: str, description: str, amount: float, frequency: str = "Month") -> Dict` - Create billing plan
- `create_billing_agreement(plan_id: str, payer_email: str) -> Dict` - Create subscription agreement
- `execute_billing_agreement(token: str) -> Dict` - Execute subscription

**Example Usage:**
```python
# Create and process payment
payment = paypal_tools.create_payment(
    amount=99.99,
    currency="USD",
    description="Premium Software License"
)

# Send invoice for services
invoice = paypal_tools.create_invoice(
    recipient_email="client@company.com",
    amount=1500.00,
    currency="USD",
    note="Consulting services - January 2024"
)

paypal_tools.send_invoice(invoice["id"])
```

### Cryptocurrency Tools
Cryptocurrency price tracking and wallet operations.

```python
from buddy.tools.crypto import CryptocurrencyTools

crypto_tools = CryptocurrencyTools(
    coinmarketcap_api_key="your-coinmarketcap-api-key",  # For price data
    blockchain_api_key="your-blockchain-api-key"         # For wallet operations
)
```

**Price and Market Data:**
- `get_price(symbol: str, convert: str = "USD") -> Dict` - Get current price
- `get_price_history(symbol: str, days: int = 30) -> List[Dict]` - Historical prices
- `get_market_data(symbol: str) -> Dict` - Market cap, volume, supply data
- `get_trending_coins(limit: int = 10) -> List[Dict]` - Trending cryptocurrencies
- `compare_prices(symbols: List[str], convert: str = "USD") -> Dict` - Compare multiple coins

**Portfolio Tracking:**
- `calculate_portfolio_value(holdings: Dict[str, float]) -> Dict` - Calculate portfolio worth
- `track_price_alerts(symbol: str, target_price: float, alert_type: str = "above") -> bool` - Set price alerts
- `get_portfolio_performance(holdings: Dict, start_date: str) -> Dict` - Portfolio performance analysis

**Wallet Operations (Limited - requires appropriate APIs):**
- `get_wallet_balance(address: str, currency: str = "BTC") -> float` - Check wallet balance
- `validate_address(address: str, currency: str) -> bool` - Validate cryptocurrency address
- `estimate_transaction_fee(currency: str, amount: float) -> float` - Estimate network fees

**Example Usage:**
```python
# Track investment portfolio
portfolio = {
    "BTC": 0.5,     # 0.5 Bitcoin
    "ETH": 2.0,     # 2 Ethereum
    "ADA": 1000.0   # 1000 Cardano
}

portfolio_value = crypto_tools.calculate_portfolio_value(portfolio)
print(f"Total portfolio value: ${portfolio_value['total_usd']:,.2f}")

# Monitor price movements
btc_price = crypto_tools.get_price("BTC")
if btc_price["price_usd"] > 50000:
    print("Bitcoin is above $50,000!")

# Set price alert
crypto_tools.track_price_alerts("ETH", 3000.00, "above")
```

## 📊 Monitoring & Observability Tools

### Datadog Monitoring
Application performance monitoring and infrastructure observability.

```python
from buddy.tools.datadog import DatadogTools

datadog_tools = DatadogTools(
    api_key="your-datadog-api-key",
    app_key="your-datadog-application-key"
)
```

**Metrics and Monitoring:**
- `send_metric(metric_name: str, value: float, tags: List[str] = None, timestamp: int = None) -> bool` - Send custom metric
- `query_metrics(query: str, from_timestamp: int, to_timestamp: int) -> Dict` - Query metric data
- `get_metric_metadata(metric_name: str) -> Dict` - Get metric information
- `list_active_metrics() -> List[str]` - List all active metrics

**Alerting:**
- `create_monitor(name: str, type: str, query: str, message: str, tags: List[str] = None) -> Dict` - Create monitor
- `get_monitor(monitor_id: int) -> Dict` - Get monitor configuration
- `update_monitor(monitor_id: int, name: str = None, query: str = None, message: str = None) -> Dict` - Update monitor
- `mute_monitor(monitor_id: int, end_timestamp: int = None) -> Dict` - Mute monitor alerts
- `delete_monitor(monitor_id: int) -> bool` - Delete monitor

**Dashboard Management:**
- `create_dashboard(title: str, description: str, widgets: List[Dict]) -> Dict` - Create dashboard
- `get_dashboard(dashboard_id: str) -> Dict` - Get dashboard configuration
- `update_dashboard(dashboard_id: str, title: str = None, widgets: List[Dict] = None) -> Dict` - Update dashboard
- `list_dashboards() -> List[Dict]` - List all dashboards

**Log Management:**
- `send_logs(logs: List[Dict]) -> bool` - Send log entries
- `search_logs(query: str, from_timestamp: int, to_timestamp: int, limit: int = 1000) -> List[Dict]` - Search logs
- `get_log_pipelines() -> List[Dict]` - Get log processing pipelines

**Example Usage:**
```python
# Send application metrics
datadog_tools.send_metric(
    metric_name="app.response_time",
    value=245.5,  # milliseconds
    tags=["service:api", "environment:production", "version:1.2.3"]
)

# Create performance monitor
monitor = datadog_tools.create_monitor(
    name="High API Response Time",
    type="metric alert",
    query="avg(last_5m):avg:app.response_time{service:api} > 500",
    message="@slack-alerts API response time is above 500ms. Please investigate.",
    tags=["team:backend", "severity:warning"]
)

# Create application dashboard
dashboard = datadog_tools.create_dashboard(
    title="Application Performance Dashboard",
    description="Real-time monitoring of application metrics",
    widgets=[
        {
            "definition": {
                "type": "timeseries",
                "requests": [
                    {"q": "avg:app.response_time{service:api}"}
                ],
                "title": "API Response Time"
            }
        },
        {
            "definition": {
                "type": "query_value",
                "requests": [
                    {"q": "sum:app.requests.count{service:api}.as_rate()"}
                ],
                "title": "Requests per Second"
            }
        }
    ]
)
```

### Grafana Visualization
Data visualization and dashboard creation.

```python
from buddy.tools.grafana import GrafanaTools

grafana_tools = GrafanaTools(
    url="http://your-grafana-instance.com",
    api_key="your-grafana-api-key"
)
```

**Dashboard Management:**
- `create_dashboard(title: str, panels: List[Dict], tags: List[str] = None) -> Dict` - Create dashboard
- `get_dashboard(dashboard_id: str) -> Dict` - Get dashboard by ID
- `update_dashboard(dashboard_id: str, dashboard_data: Dict) -> Dict` - Update dashboard
- `delete_dashboard(dashboard_id: str) -> bool` - Delete dashboard
- `list_dashboards() -> List[Dict]` - List all dashboards

**Panel Creation:**
- `create_graph_panel(title: str, targets: List[Dict], x_pos: int = 0, y_pos: int = 0) -> Dict` - Create graph panel
- `create_stat_panel(title: str, target: str, unit: str = None) -> Dict` - Create stat panel
- `create_table_panel(title: str, targets: List[Dict]) -> Dict` - Create table panel

**Data Source Management:**
- `add_data_source(name: str, type: str, url: str, access: str = "proxy", database: str = None) -> Dict` - Add data source
- `get_data_sources() -> List[Dict]` - List data sources
- `test_data_source(datasource_id: int) -> Dict` - Test data source connection

**Alert Rules:**
- `create_alert_rule(title: str, condition: Dict, notifications: List[str]) -> Dict` - Create alert rule
- `get_alert_rules() -> List[Dict]` - List alert rules
- `pause_alert_rule(rule_id: int) -> bool` - Pause alert rule

**Example Usage:**
```python
# Create monitoring dashboard
dashboard = grafana_tools.create_dashboard(
    title="System Performance Monitoring",
    panels=[
        grafana_tools.create_graph_panel(
            title="CPU Usage",
            targets=[
                {
                    "expr": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                    "legendFormat": "CPU Usage %"
                }
            ]
        ),
        grafana_tools.create_stat_panel(
            title="Memory Usage",
            target="(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            unit="percent"
        )
    ],
    tags=["monitoring", "infrastructure"]
)

# Add Prometheus data source
prometheus_ds = grafana_tools.add_data_source(
    name="Prometheus",
    type="prometheus", 
    url="http://prometheus:9090",
    access="proxy"
)
```

### New Relic APM
Application performance monitoring and error tracking.

```python
from buddy.tools.newrelic import NewRelicTools

newrelic_tools = NewRelicTools(
    api_key="your-newrelic-api-key",
    account_id="your-account-id"
)
```

**Application Monitoring:**
- `get_applications() -> List[Dict]` - List monitored applications
- `get_application_metrics(app_id: str, metrics: List[str], from_time: str, to_time: str) -> Dict` - Get app metrics
- `get_error_rate(app_id: str, time_range: str = "30 MINUTES AGO") -> float` - Get error rate
- `get_throughput(app_id: str, time_range: str = "30 MINUTES AGO") -> float` - Get request throughput

**Alert Management:**
- `create_alert_policy(name: str, incident_preference: str = "PER_POLICY") -> Dict` - Create alert policy
- `create_alert_condition(policy_id: str, name: str, type: str, entities: List[str], terms: List[Dict]) -> Dict` - Create alert condition
- `get_alert_violations(policy_id: str = None) -> List[Dict]` - Get current violations

**Custom Events:**
- `send_custom_event(event_type: str, attributes: Dict) -> bool` - Send custom event
- `query_nrql(query: str, account_id: str = None) -> Dict` - Execute NRQL query

**Example Usage:**
```python
# Monitor application performance
apps = newrelic_tools.get_applications()
main_app = next(app for app in apps if app["name"] == "production-api")

error_rate = newrelic_tools.get_error_rate(main_app["id"])
throughput = newrelic_tools.get_throughput(main_app["id"])

if error_rate > 5.0:  # Alert if error rate > 5%
    newrelic_tools.send_custom_event(
        event_type="HighErrorRate",
        attributes={
            "application": main_app["name"],
            "error_rate": error_rate,
            "timestamp": int(time.time())
        }
    )

# Create performance alert
policy = newrelic_tools.create_alert_policy("High Response Time Alert")
newrelic_tools.create_alert_condition(
    policy_id=policy["id"],
    name="Response Time Alert",
    type="apm_app_metric",
    entities=[main_app["id"]],
    terms=[{
        "duration": "5",
        "operator": "above",
        "threshold": "500",  # 500ms
        "time_function": "all"
    }]
)
```

## 🏠 IoT & Hardware Integration Tools

### Raspberry Pi Control
Raspberry Pi GPIO control and sensor integration.

```python
from buddy.tools.raspberrypi import RaspberryPiTools

rpi_tools = RaspberryPiTools(
    host="192.168.1.100",  # Pi IP address, or "localhost" if running on Pi
    username="pi",
    password="raspberry",
    # Alternative: use SSH key authentication
    # ssh_key_path="/path/to/private/key"
)
```

**GPIO Operations:**
- `set_pin_mode(pin: int, mode: str) -> bool` - Set pin as input/output
- `digital_write(pin: int, value: bool) -> bool` - Set digital pin high/low
- `digital_read(pin: int) -> bool` - Read digital pin state
- `analog_read(pin: int) -> int` - Read analog pin value (0-1023)
- `pwm_write(pin: int, duty_cycle: float) -> bool` - Set PWM duty cycle (0-100%)

**Sensor Integration:**
- `read_temperature_humidity(sensor_type: str = "DHT22", pin: int = 4) -> Dict` - Read DHT sensor
- `read_ultrasonic_distance(trigger_pin: int, echo_pin: int) -> float` - Ultrasonic sensor distance
- `read_light_sensor(pin: int) -> float` - Light sensor reading
- `read_motion_sensor(pin: int) -> bool` - PIR motion sensor
- `read_accelerometer() -> Dict` - Read accelerometer data (if connected)

**Camera Operations:**
- `capture_photo(filename: str = None, width: int = 1920, height: int = 1080) -> str` - Capture photo
- `start_video_recording(filename: str = None, duration: int = None) -> str` - Start video recording
- `stop_video_recording() -> bool` - Stop ongoing recording
- `capture_timelapse(interval: int, count: int, output_dir: str = None) -> List[str]` - Time-lapse photography

**System Monitoring:**
- `get_cpu_temperature() -> float` - Get CPU temperature
- `get_system_stats() -> Dict` - CPU usage, memory, disk space
- `get_network_info() -> Dict` - Network interface information
- `restart_system() -> bool` - Restart Raspberry Pi
- `shutdown_system() -> bool` - Shutdown Raspberry Pi

**Example Usage:**
```python
# Home automation setup
# Turn on LED when motion is detected
rpi_tools.set_pin_mode(18, "output")  # LED pin
rpi_tools.set_pin_mode(24, "input")   # Motion sensor pin

motion_detected = rpi_tools.read_motion_sensor(24)
if motion_detected:
    rpi_tools.digital_write(18, True)   # Turn on LED
    print("Motion detected! LED turned on.")
    
    # Capture security photo
    photo_path = rpi_tools.capture_photo("security_photo.jpg")
    print(f"Security photo saved: {photo_path}")

# Environmental monitoring
temp_humidity = rpi_tools.read_temperature_humidity("DHT22", 4)
print(f"Temperature: {temp_humidity['temperature']}°C")
print(f"Humidity: {temp_humidity['humidity']}%")

# Send alert if temperature too high
if temp_humidity['temperature'] > 30:
    rpi_tools.digital_write(22, True)  # Turn on cooling fan
    
# Monitor system health
stats = rpi_tools.get_system_stats()
cpu_temp = rpi_tools.get_cpu_temperature()

if cpu_temp > 70:  # CPU overheating
    print(f"Warning: CPU temperature is {cpu_temp}°C")
```

### Arduino Integration
Arduino microcontroller programming and sensor integration.

```python
from buddy.tools.arduino import ArduinoTools

arduino_tools = ArduinoTools(
    port="/dev/ttyUSB0",  # Serial port (varies by system)
    baudrate=9600,
    timeout=5.0
)
```

**Serial Communication:**
- `send_command(command: str) -> str` - Send command to Arduino
- `read_serial_data(timeout: float = 1.0) -> str` - Read from serial port
- `write_serial_data(data: str) -> bool` - Write to serial port
- `reset_connection() -> bool` - Reset serial connection

**Sensor Reading:**
- `read_analog_sensor(pin: int) -> int` - Read analog sensor (0-1023)
- `read_digital_sensor(pin: int) -> bool` - Read digital sensor
- `read_multiple_sensors(pins: List[int]) -> Dict` - Read multiple sensors
- `calibrate_sensor(pin: int, samples: int = 100) -> Dict` - Calibrate sensor

**Actuator Control:**
- `control_servo(pin: int, angle: int) -> bool` - Control servo motor (0-180°)
- `control_motor(pin1: int, pin2: int, speed: int, direction: str) -> bool` - Control DC motor
- `control_stepper(steps: int, direction: str = "clockwise") -> bool` - Control stepper motor
- `control_relay(pin: int, state: bool) -> bool` - Control relay switch

**LED and Display:**
- `control_led(pin: int, state: bool) -> bool` - Control LED
- `led_fade(pin: int, start_brightness: int, end_brightness: int, duration: float) -> bool` - Fade LED
- `display_text(text: str, line: int = 0) -> bool` - Display text on LCD
- `clear_display() -> bool` - Clear LCD display

**Example Usage:**
```python
# Smart garden monitoring system
# Read soil moisture sensor
soil_moisture = arduino_tools.read_analog_sensor(0)  # Pin A0
print(f"Soil moisture: {soil_moisture}")

# If soil is dry, activate water pump
if soil_moisture < 300:  # Threshold for dry soil
    arduino_tools.control_relay(7, True)   # Turn on water pump
    print("Soil is dry. Watering plants...")
    
    time.sleep(5)  # Water for 5 seconds
    
    arduino_tools.control_relay(7, False)  # Turn off water pump
    arduino_tools.display_text("Plants watered!", 0)

# Temperature monitoring with fan control
temp_sensor_value = arduino_tools.read_analog_sensor(1)  # Pin A1
# Convert to temperature (depends on sensor)
temperature = (temp_sensor_value * 5.0 / 1024.0 - 0.5) * 100

if temperature > 25:  # If temperature > 25°C
    arduino_tools.control_motor(5, 6, 255, "clockwise")  # Run cooling fan
    arduino_tools.display_text(f"Temp: {temperature:.1f}C", 1)

# Light-following robot
light_left = arduino_tools.read_analog_sensor(2)   # Left light sensor
light_right = arduino_tools.read_analog_sensor(3)  # Right light sensor

if light_left > light_right + 50:  # Turn towards brighter light
    arduino_tools.control_motor(9, 10, 200, "clockwise")    # Left motor
    arduino_tools.control_motor(11, 12, 100, "clockwise")   # Right motor (slower)
elif light_right > light_left + 50:
    arduino_tools.control_motor(9, 10, 100, "clockwise")    # Left motor (slower)
    arduino_tools.control_motor(11, 12, 200, "clockwise")   # Right motor
else:
    arduino_tools.control_motor(9, 10, 150, "clockwise")    # Both motors same speed
    arduino_tools.control_motor(11, 12, 150, "clockwise")
```

### Home Assistant Integration
Smart home automation and device control.

```python
from buddy.tools.homeassistant import HomeAssistantTools

ha_tools = HomeAssistantTools(
    url="http://your-home-assistant:8123",
    access_token="your-long-lived-access-token"
)
```

**Device Control:**
- `turn_on_device(entity_id: str) -> bool` - Turn on device
- `turn_off_device(entity_id: str) -> bool` - Turn off device  
- `set_device_brightness(entity_id: str, brightness: int) -> bool` - Set light brightness (0-255)
- `set_device_color(entity_id: str, color: str) -> bool` - Set light color
- `toggle_device(entity_id: str) -> bool` - Toggle device state

**State Monitoring:**
- `get_device_state(entity_id: str) -> Dict` - Get device current state
- `get_all_states() -> List[Dict]` - Get all entity states
- `get_devices_by_type(device_type: str) -> List[Dict]` - Get devices by type
- `is_device_on(entity_id: str) -> bool` - Check if device is on

**Automation and Scenes:**
- `trigger_automation(automation_id: str) -> bool` - Trigger automation
- `activate_scene(scene_id: str) -> bool` - Activate scene
- `create_automation(name: str, trigger: Dict, condition: Dict, action: Dict) -> Dict` - Create automation
- `get_automations() -> List[Dict]` - List all automations

**Sensor Data:**
- `get_sensor_value(sensor_id: str) -> float` - Get sensor reading
- `get_weather_data() -> Dict` - Get weather information
- `get_energy_usage() -> Dict` - Get energy consumption data
- `get_security_status() -> Dict` - Get security system status

**Example Usage:**
```python
# Morning routine automation
def morning_routine():
    # Turn on bedroom lights gradually
    ha_tools.turn_on_device("light.bedroom_main")
    ha_tools.set_device_brightness("light.bedroom_main", 100)
    
    # Start coffee maker
    ha_tools.turn_on_device("switch.coffee_maker")
    
    # Check weather and adjust thermostat
    weather = ha_tools.get_weather_data()
    outside_temp = weather.get("temperature", 20)
    
    if outside_temp < 15:  # Cold day
        ha_tools.set_device_temperature("climate.main_thermostat", 22)
    
    # Activate morning scene
    ha_tools.activate_scene("scene.morning_routine")

# Security monitoring
def check_security():
    # Check if any doors/windows are open
    front_door = ha_tools.get_device_state("binary_sensor.front_door")
    back_door = ha_tools.get_device_state("binary_sensor.back_door")
    
    if front_door["state"] == "on" or back_door["state"] == "on":
        # Turn on security lights
        ha_tools.turn_on_device("light.security_front")
        ha_tools.turn_on_device("light.security_back")
        
        # Send notification
        ha_tools.call_service("notify.mobile_app", {
            "message": "Security Alert: Door opened!",
            "title": "Home Security"
        })

# Energy management
def energy_optimization():
    current_usage = ha_tools.get_energy_usage()
    
    if current_usage["total_consumption"] > 5000:  # High usage
        # Turn off non-essential devices
        ha_tools.turn_off_device("switch.outdoor_decorative_lights")
        ha_tools.turn_off_device("media_player.living_room_tv")
        
        # Reduce HVAC
        current_temp = ha_tools.get_device_state("climate.main_thermostat")["attributes"]["temperature"]
        ha_tools.set_device_temperature("climate.main_thermostat", current_temp - 2)

# Adaptive lighting based on occupancy and time
motion_sensor = ha_tools.get_device_state("binary_sensor.living_room_motion")
current_hour = datetime.now().hour

if motion_sensor["state"] == "on":  # Motion detected
    if 6 <= current_hour <= 22:  # Daytime
        ha_tools.set_device_brightness("light.living_room", 180)
        ha_tools.set_device_color("light.living_room", "white")
    else:  # Nighttime
        ha_tools.set_device_brightness("light.living_room", 50)
        ha_tools.set_device_color("light.living_room", "red")
```

## 🔐 Security & Authentication Tools

### OAuth2 Authentication
OAuth2 flow implementation and token management.

```python
from buddy.tools.oauth2 import OAuth2Tools

oauth_tools = OAuth2Tools(
    client_id="your-oauth-client-id",
    client_secret="your-oauth-client-secret",
    redirect_uri="http://localhost:8080/callback",
    authorization_url="https://provider.com/oauth/authorize",
    token_url="https://provider.com/oauth/token"
)
```

**Authorization Flow:**
- `get_authorization_url(scopes: List[str] = None, state: str = None) -> str` - Generate authorization URL
- `exchange_code_for_token(authorization_code: str, state: str = None) -> Dict` - Exchange auth code for tokens
- `refresh_access_token(refresh_token: str) -> Dict` - Refresh expired access token
- `revoke_token(token: str, token_type: str = "access_token") -> bool` - Revoke token

**Token Management:**
- `validate_token(access_token: str) -> Dict` - Validate token and get info
- `get_token_info(access_token: str) -> Dict` - Get token metadata
- `is_token_expired(token_data: Dict) -> bool` - Check if token is expired
- `store_token(token_data: Dict, user_id: str) -> bool` - Store token securely

**API Requests:**
- `authenticated_request(url: str, method: str = "GET", access_token: str = None, data: Dict = None) -> Dict` - Make authenticated API request
- `get_user_info(access_token: str) -> Dict` - Get user profile information

**Example Usage:**
```python
# OAuth2 flow for Google API access
google_oauth = OAuth2Tools(
    client_id="your-google-client-id",
    client_secret="your-google-client-secret",
    redirect_uri="http://localhost:8080/callback",
    authorization_url="https://accounts.google.com/o/oauth2/auth",
    token_url="https://oauth2.googleapis.com/token"
)

# Step 1: Get authorization URL
auth_url = google_oauth.get_authorization_url([
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly"
])

print(f"Visit this URL to authorize: {auth_url}")

# Step 2: Exchange authorization code (received from callback)
authorization_code = "received_from_callback"
token_data = google_oauth.exchange_code_for_token(authorization_code)

# Step 3: Make authenticated API calls
user_info = google_oauth.get_user_info(token_data["access_token"])
print(f"Authenticated user: {user_info['email']}")

# Make API request to Google Calendar
calendar_response = google_oauth.authenticated_request(
    url="https://www.googleapis.com/calendar/v3/calendars/primary/events",
    access_token=token_data["access_token"]
)
```

### JWT Token Management
JSON Web Token creation, validation, and management.

```python
from buddy.tools.jwt import JWTTools

jwt_tools = JWTTools(
    secret_key="your-secret-key",
    algorithm="HS256",
    default_expiration=3600  # 1 hour default
)
```

**Token Creation:**
- `create_token(payload: Dict, expiration: int = None) -> str` - Create JWT token
- `create_refresh_token(user_id: str, expiration: int = None) -> str` - Create refresh token
- `create_access_token(user_id: str, roles: List[str] = None, expiration: int = None) -> str` - Create access token

**Token Validation:**
- `validate_token(token: str) -> Dict` - Validate and decode token
- `is_token_expired(token: str) -> bool` - Check if token is expired
- `get_token_payload(token: str) -> Dict` - Extract payload from token
- `verify_signature(token: str) -> bool` - Verify token signature

**Token Management:**
- `refresh_token(refresh_token: str) -> Dict` - Generate new access token from refresh token
- `blacklist_token(token: str) -> bool` - Add token to blacklist
- `is_token_blacklisted(token: str) -> bool` - Check if token is blacklisted
- `get_token_expiration(token: str) -> datetime` - Get token expiration time

**Example Usage:**
```python
# User authentication system
user_data = {
    "user_id": "12345",
    "username": "john_doe",
    "email": "john@example.com",
    "roles": ["user", "premium"]
}

# Create access and refresh tokens
access_token = jwt_tools.create_access_token(
    user_id=user_data["user_id"],
    roles=user_data["roles"],
    expiration=900  # 15 minutes
)

refresh_token = jwt_tools.create_refresh_token(
    user_id=user_data["user_id"],
    expiration=604800  # 7 days
)

print(f"Access token: {access_token}")
print(f"Refresh token: {refresh_token}")

# Validate tokens in API requests
def authenticate_request(token: str) -> Dict:
    try:
        payload = jwt_tools.validate_token(token)
        return {
            "authenticated": True,
            "user_id": payload["user_id"],
            "roles": payload.get("roles", [])
        }
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

# Token refresh flow
def refresh_user_token(refresh_token: str) -> Dict:
    if jwt_tools.is_token_blacklisted(refresh_token):
        return {"error": "Refresh token is invalid"}
    
    try:
        new_tokens = jwt_tools.refresh_token(refresh_token)
        return {
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"]
        }
    except Exception as e:
        return {"error": str(e)}
```

### YouTube Tools
YouTube video processing.

```python
from buddy.tools.youtube import YouTubeTools

youtube = YouTubeTools()
```

**Methods:**
- `search_videos(query: str, max_results: int = 10) -> List[dict]`
- `get_video_info(video_id: str) -> dict`
- `get_transcript(video_id: str) -> str`
- `download_audio(video_id: str, output_path: str) -> str`

### Wikipedia
Wikipedia article access.

```python
from buddy.tools.wikipedia import WikipediaTools

wiki = WikipediaTools(language="en")
```

**Methods:**
- `search(query: str, results: int = 10) -> List[str]`
- `get_page(title: str) -> str`
- `get_summary(title: str, sentences: int = 3) -> str`

## 💬 Communication Tools

### Email Tools
Send and manage emails.

```python
from buddy.tools.email import EmailTools

email = EmailTools(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-app-password"
)
```

**Methods:**
- `send_email(to: str, subject: str, body: str, html: bool = False) -> bool`
- `send_bulk_email(recipients: List[str], subject: str, body: str) -> dict`

### Slack Integration
Slack workspace communication.

```python
from buddy.tools.slack import SlackTools

slack = SlackTools(
    token="xoxb-your-bot-token",
    default_channel="#general"
)
```

**Methods:**
- `send_message(text: str, channel: str = None) -> dict`
- `upload_file(file_path: str, channel: str, title: str = None) -> dict`
- `get_channel_messages(channel: str, limit: int = 100) -> List[dict]`
- `create_channel(name: str, is_private: bool = False) -> dict`

### Microsoft Teams
Teams integration for enterprise.

```python
from buddy.tools.microsoft_teams import TeamsTools

teams = TeamsTools(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret"
)
```

### SMS Tools
Send SMS messages.

```python
from buddy.tools.sms import SMSTools

sms = SMSTools(
    service="twilio",  # or "aws_sns"
    account_sid="your-twilio-sid",
    auth_token="your-twilio-token",
    from_number="+1234567890"
)
```

### WhatsApp Integration
WhatsApp business messaging.

```python
from buddy.tools.whatsapp import WhatsAppTools

whatsapp = WhatsAppTools(
    api_key="your-whatsapp-api-key",
    phone_number_id="your-phone-id"
)
```

### Social Media Tools

#### Twitter/X
```python
from buddy.tools.twitter import TwitterTools

twitter = TwitterTools(
    bearer_token="your-bearer-token",
    consumer_key="your-consumer-key",
    consumer_secret="your-consumer-secret",
    access_token="your-access-token",
    access_token_secret="your-access-token-secret"
)
```

#### LinkedIn
```python
from buddy.tools.linkedin import LinkedInTools

linkedin = LinkedInTools(
    access_token="your-linkedin-token"
)
```

#### Instagram
```python
from buddy.tools.instagram import InstagramTools

instagram = InstagramTools(
    access_token="your-instagram-token"
)
```

#### Facebook
```python
from buddy.tools.facebook import FacebookTools

facebook = FacebookTools(
    access_token="your-facebook-token"
)
```

## 📁 File & Data Tools

### File System Operations
Local file management.

```python
from buddy.tools.file import FileTools

file_tools = FileTools(
    base_directory="/safe/path",
    allowed_extensions=[".txt", ".md", ".json", ".csv"],
    max_file_size=10*1024*1024  # 10MB
)
```

**Methods:**
- `read_file(file_path: str) -> str`
- `write_file(file_path: str, content: str, append: bool = False) -> bool`
- `list_files(directory: str = None, pattern: str = "*") -> List[str]`
- `delete_file(file_path: str) -> bool`
- `copy_file(source: str, destination: str) -> bool`
- `move_file(source: str, destination: str) -> bool`
- `create_directory(directory: str) -> bool`

### CSV Toolkit
Advanced CSV operations.

```python
from buddy.tools.csv_toolkit import CSVToolkit

csv_tools = CSVToolkit()
```

**Methods:**
- `read_csv(file_path: str) -> List[dict]`
- `write_csv(file_path: str, data: List[dict]) -> bool`
- `filter_csv(file_path: str, filters: dict) -> List[dict]`
- `aggregate_csv(file_path: str, group_by: str, aggregations: dict) -> dict`
- `merge_csv_files(files: List[str], output_file: str) -> bool`

### JSON Processing
JSON data manipulation.

```python
from buddy.tools.json import JSONTools

json_tools = JSONTools()
```

**Methods:**
- `parse_json(json_string: str) -> dict`
- `format_json(data: dict, indent: int = 2) -> str`
- `validate_json_schema(data: dict, schema: dict) -> bool`
- `extract_values(data: dict, path: str) -> List[Any]`

### Pandas Integration
Data analysis and manipulation.

```python
from buddy.tools.pandas import PandasTools

pandas_tools = PandasTools()
```

**Methods:**
- `load_dataframe(file_path: str, file_type: str = "csv") -> str`
- `describe_dataframe(df_id: str) -> dict`
- `filter_dataframe(df_id: str, conditions: str) -> str`
- `aggregate_data(df_id: str, group_by: List[str], agg_funcs: dict) -> dict`
- `create_visualization(df_id: str, chart_type: str, **kwargs) -> str`

### Database Tools

#### PostgreSQL
```python
from buddy.tools.postgres import PostgreSQLTools

postgres = PostgreSQLTools(
    connection_string="postgresql://user:pass@localhost:5432/db"
)
```

#### General SQL
```python
from buddy.tools.sql import SQLTools

sql_tools = SQLTools(
    connection_string="sqlite:///database.db"
)
```

**Methods:**
- `execute_query(query: str) -> List[dict]`
- `execute_command(command: str) -> bool`
- `list_tables() -> List[str]`
- `describe_table(table_name: str) -> List[dict]`

## ☁️ Cloud Services Tools

### AWS Tools
Comprehensive AWS integration.

```python
from buddy.tools.aws_tools import AWSTools

aws = AWSTools(
    aws_access_key_id="your-access-key",
    aws_secret_access_key="your-secret-key",
    region="us-east-1"
)
```

**S3 Operations:**
- `list_s3_buckets() -> List[str]`
- `upload_to_s3(bucket: str, key: str, file_path: str) -> bool`
- `download_from_s3(bucket: str, key: str, local_path: str) -> bool`

**Lambda Operations:**
- `invoke_lambda(function_name: str, payload: dict) -> dict`
- `list_lambda_functions() -> List[str]`

**EC2 Operations:**
- `list_ec2_instances() -> List[dict]`
- `start_ec2_instance(instance_id: str) -> bool`
- `stop_ec2_instance(instance_id: str) -> bool`

### Google Cloud Tools
Google Cloud Platform integration.

```python
from buddy.tools.google_maps import GoogleMapsTools
from buddy.tools.googlecalendar import GoogleCalendarTools
from buddy.tools.googlesheets import GoogleSheetsTools
```

#### Google Maps
```python
google_maps = GoogleMapsTools(api_key="your-google-maps-key")
```

**Methods:**
- `geocode_address(address: str) -> dict`
- `reverse_geocode(lat: float, lng: float) -> dict`
- `get_directions(origin: str, destination: str) -> dict`
- `search_nearby(location: str, radius: int, type: str) -> List[dict]`

#### Google Calendar
```python
calendar = GoogleCalendarTools(credentials_file="credentials.json")
```

**Methods:**
- `list_calendars() -> List[dict]`
- `list_events(calendar_id: str, max_results: int = 10) -> List[dict]`
- `create_event(calendar_id: str, event_data: dict) -> dict`
- `delete_event(calendar_id: str, event_id: str) -> bool`

#### Google Sheets
```python
sheets = GoogleSheetsTools(credentials_file="credentials.json")
```

**Methods:**
- `read_sheet(spreadsheet_id: str, range: str) -> List[List[str]]`
- `write_sheet(spreadsheet_id: str, range: str, values: List[List[str]]) -> bool`
- `create_spreadsheet(title: str) -> str`

## 🛠️ Development Tools

### GitHub Integration
Repository management and operations.

```python
from buddy.tools.github import GitHubTools

github = GitHubTools(
    access_token="your-github-token",
    default_owner="username",
    default_repo="repository"
)
```

**Methods:**
- `list_repositories(owner: str = None) -> List[dict]`
- `get_repository(owner: str, repo: str) -> dict`
- `create_repository(name: str, description: str = "", private: bool = False) -> dict`
- `list_issues(owner: str = None, repo: str = None, state: str = "open") -> List[dict]`
- `create_issue(title: str, body: str, labels: List[str] = None) -> dict`
- `list_pull_requests(owner: str = None, repo: str = None) -> List[dict]`
- `create_pull_request(title: str, body: str, head: str, base: str) -> dict`

### Docker Tools
Container management.

```python
from buddy.tools.docker import DockerTools

docker = DockerTools()
```

**Methods:**
- `list_containers(all: bool = False) -> List[dict]`
- `list_images() -> List[dict]`
- `run_container(image: str, command: str = None, **kwargs) -> str`
- `stop_container(container_id: str) -> bool`
- `remove_container(container_id: str, force: bool = False) -> bool`
- `pull_image(image: str) -> bool`
- `build_image(dockerfile_path: str, tag: str) -> bool`

### Kubernetes Tools
Kubernetes cluster management.

```python
from buddy.tools.kubernetes_tools import KubernetesTools

k8s = KubernetesTools(
    config_file="~/.kube/config",
    namespace="default"
)
```

**Methods:**
- `list_pods(namespace: str = None) -> List[dict]`
- `get_pod(name: str, namespace: str = None) -> dict`
- `create_deployment(manifest: dict) -> dict`
- `delete_deployment(name: str, namespace: str = None) -> bool`
- `list_services(namespace: str = None) -> List[dict]`
- `apply_manifest(manifest: dict) -> dict`

### Code Execution
Safe code execution environment.

```python
from buddy.tools.python import PythonTools

python = PythonTools(
    timeout=30,
    max_execution_time=60,
    allowed_imports=["numpy", "pandas", "matplotlib"]
)
```

**Methods:**
- `execute_python(code: str) -> dict`
- `install_package(package: str) -> bool`
- `list_installed_packages() -> List[str]`

### Shell Commands
System command execution.

```python
from buddy.tools.shell import ShellTools

shell = ShellTools(
    allowed_commands=["ls", "pwd", "cat", "grep"],
    timeout=30
)
```

**Methods:**
- `execute_command(command: str, cwd: str = None) -> dict`
- `execute_script(script_path: str) -> dict`

## 🎨 AI/ML Tools

### Image Generation (DALL-E)
AI image generation.

```python
from buddy.tools.dalle import DALLETools

dalle = DALLETools(
    api_key="your-openai-key",
    model="dall-e-3",
    quality="standard"  # or "hd"
)
```

**Methods:**
- `generate_image(prompt: str, size: str = "1024x1024") -> str`
- `edit_image(image_path: str, mask_path: str, prompt: str) -> str`
- `create_variation(image_path: str) -> str`

### Audio Transcription
Audio processing and transcription.

```python
from buddy.tools.transcription import TranscriptionTools

transcription = TranscriptionTools(
    service="openai",  # or "assembly", "deepgram"
    api_key="your-api-key"
)
```

### Text-to-Speech
Voice synthesis.

```python
from buddy.tools.eleven_labs import ElevenLabsTools

tts = ElevenLabsTools(
    api_key="your-elevenlabs-key",
    voice_id="default-voice-id"
)
```

### Computer Vision
Image analysis with OpenCV.

```python
from buddy.tools.opencv import OpenCVTools

cv_tools = OpenCVTools()
```

## 📊 Business Tools

### CRM Integration

#### Linear (Project Management)
```python
from buddy.tools.linear import LinearTools

linear = LinearTools(api_key="your-linear-key")
```

#### Jira
```python
from buddy.tools.jira import JiraTools

jira = JiraTools(
    server="https://your-domain.atlassian.net",
    email="your-email@example.com",
    api_token="your-api-token"
)
```

#### Confluence
```python
from buddy.tools.confluence import ConfluenceTools

confluence = ConfluenceTools(
    url="https://your-domain.atlassian.net",
    username="your-email",
    api_token="your-token"
)
```

### E-commerce & Payments
Payment processing integrations.

```python
from buddy.tools.payments import PaymentTools

payments = PaymentTools(
    provider="stripe",  # or "paypal", "square"
    api_key="your-payment-api-key"
)
```

## 🔧 Utility Tools

### Calculator
Advanced mathematical operations.

```python
from buddy.tools.calculator import CalculatorTools

calc = CalculatorTools()
```

**Methods:**
- `calculate(expression: str) -> float`
- `solve_equation(equation: str) -> dict`
- `convert_units(value: float, from_unit: str, to_unit: str) -> float`
- `statistical_analysis(data: List[float]) -> dict`

### Date & Time
Time zone and date operations.

```python
from buddy.tools.timezone import TimezoneTools

time_tools = TimezoneTools()
```

**Methods:**
- `get_current_time(timezone: str = "UTC") -> str`
- `convert_timezone(datetime_str: str, from_tz: str, to_tz: str) -> str`
- `calculate_duration(start: str, end: str) -> dict`
- `get_timezone_info(timezone: str) -> dict`

### QR Code Generator
QR code creation and reading.

```python
from buddy.tools.qr_code_generator import QRCodeTools

qr_tools = QRCodeTools()
```

**Methods:**
- `generate_qr_code(data: str, file_path: str = None) -> str`
- `read_qr_code(image_path: str) -> str`

### IP Geolocation
Get location information from IP addresses.

```python
from buddy.tools.ip_geolocation import IPGeolocationTools

ip_tools = IPGeolocationTools(api_key="your-api-key")
```

### Weather Information
Weather data and forecasts.

```python
from buddy.tools.openweather import OpenWeatherTools

weather = OpenWeatherTools(api_key="your-openweather-key")
```

**Methods:**
- `get_current_weather(city: str) -> dict`
- `get_forecast(city: str, days: int = 5) -> dict`
- `get_weather_by_coords(lat: float, lon: float) -> dict`

### Translation
Multi-language translation services.

```python
from buddy.tools.translation import TranslationTools

translator = TranslationTools(
    service="google",  # or "azure", "aws"
    api_key="your-translation-key"
)
```

### Web Browser Automation
Browser control and automation.

```python
from buddy.tools.playwright_tool import PlaywrightTools
from buddy.tools.selenium_tool import SeleniumTools

# Playwright (recommended)
browser = PlaywrightTools(
    headless=True,
    browser_type="chromium"  # or "firefox", "webkit"
)

# Selenium
selenium = SeleniumTools(
    driver="chrome",
    headless=True
)
```

## 🎯 Specialized Tools

### Video Processing
Video editing and processing.

```python
from buddy.tools.moviepy_video import VideoTools

video = VideoTools()
```

### Memory Integration
External memory services.

```python
from buddy.tools.mem0 import Mem0Tools

mem0 = Mem0Tools(api_key="your-mem0-key")
```

### Push Notifications
Mobile and web notifications.

```python
from buddy.tools.push_notifications import PushNotificationTools

push = PushNotificationTools(
    service="firebase",  # or "apns", "onesignal"
    api_key="your-push-key"
)
```

### Elasticsearch
Search and analytics engine.

```python
from buddy.tools.elasticsearch_tool import ElasticsearchTools

elastic = ElasticsearchTools(
    hosts=["localhost:9200"],
    username="elastic",
    password="your-password"
)
```

### GIF Creation
Animated GIF generation.

```python
from buddy.tools.giphy import GiphyTools

giphy = GiphyTools(api_key="your-giphy-key")
```

## 🏗️ Tool Configuration Best Practices

### Security Configuration
```python
# Example secure tool configuration
from buddy.tools.file import FileTools

secure_file_tools = FileTools(
    base_directory="/app/safe_directory",
    allowed_extensions=[".txt", ".md", ".json"],
    max_file_size=5 * 1024 * 1024,  # 5MB limit
    read_only=False,
    create_directories=True
)
```

### Error Handling
```python
from buddy.tools import Toolkit
from buddy.exceptions import ToolExecutionError

class SafeWebTool(Toolkit):
    def fetch_url(self, url: str) -> str:
        try:
            # URL fetching logic
            return content
        except Exception as e:
            raise ToolExecutionError(f"Failed to fetch URL: {e}")
```

### Performance Optimization
```python
# Use connection pooling for database tools
postgres = PostgreSQLTools(
    connection_string="postgresql://...",
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)
```

## 📝 Creating Custom Tool Categories

You can organize custom tools into categories:

```python
from buddy.tools import Toolkit

class EcommerceTools(Toolkit):
    \"\"\"E-commerce specific tools.\"\"\"
    
    def get_product_info(self, product_id: str) -> dict:
        \"\"\"Get product information.\"\"\"
        pass
    
    def update_inventory(self, product_id: str, quantity: int) -> bool:
        \"\"\"Update product inventory.\"\"\"
        pass
    
    def process_order(self, order_data: dict) -> str:
        \"\"\"Process a customer order.\"\"\"
        pass

class MarketingTools(Toolkit):
    \"\"\"Marketing automation tools.\"\"\"
    
    def send_campaign(self, campaign_id: str, recipients: List[str]) -> dict:
        \"\"\"Send marketing campaign.\"\"\"
        pass
    
    def analyze_campaign(self, campaign_id: str) -> dict:
        \"\"\"Analyze campaign performance.\"\"\"
        pass
```

This comprehensive reference covers all 200+ built-in tools available in Buddy AI. Each tool is designed to work seamlessly with agents and can be combined to create powerful automation workflows.