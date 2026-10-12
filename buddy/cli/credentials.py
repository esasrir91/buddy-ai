from typing import Optional

from buddy.cli.settings import BUDDY_cli_settings
from buddy.utils.json_io import read_json_file, write_json_file


def save_auth_token(auth_token: str) -> None:
    if not isinstance(auth_token, str) or not auth_token.strip():
        raise ValueError("auth_token must be a non-empty string")

    # logger.debug(f"Storing {auth_token} to {str(BUDDY_cli_settings.credentials_path)}")
    BUDDY_cli_settings.credentials_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(BUDDY_cli_settings.credentials_path, {"token": auth_token})


def read_auth_token() -> Optional[str]:
    # logger.debug(f"Reading token from {str(BUDDY_cli_settings.credentials_path)}")
    try:
        data = read_json_file(BUDDY_cli_settings.credentials_path)
    except (OSError, TypeError, ValueError):
        return None

    if not isinstance(data, dict):
        return None
    token = data.get("token")
    return token if isinstance(token, str) and token else None
