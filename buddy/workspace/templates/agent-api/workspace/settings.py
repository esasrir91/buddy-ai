"""Workspace settings for the agent-api."""
from pathlib import Path

ws_root = Path(__file__).parent.parent.resolve()
ws_secrets = ws_root / "workspace" / "secrets"
