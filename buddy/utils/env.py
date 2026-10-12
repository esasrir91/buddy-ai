from os import getenv


def get_from_env(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Get the value for an environment variable. Use default if not found, or raise an error if required is True."""

    value = getenv(key, default)
    if value is None and required:
        raise ValueError(f"Environment variable {key} is required but not found")
    return value
