"""Workspace settings for the agent-app."""
from pathlib import Path

# Root directory of this workspace
ws_root = Path(__file__).parent.parent.resolve()

# Secrets directory (copy example_secrets to secrets and fill in API keys)
ws_secrets = ws_root / "workspace" / "secrets"
