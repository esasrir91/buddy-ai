from pathlib import Path
from typing import Any

from buddy.utils.log import log_debug, logger


def read_yaml_file(file_path: Path | None) -> dict[str, Any] | None:
    if file_path is not None and file_path.exists() and file_path.is_file():
        import yaml

        log_debug(f"Reading {file_path}")
        data_from_file = yaml.safe_load(file_path.read_text())
        if data_from_file is not None and isinstance(data_from_file, dict):
            return data_from_file
        else:
            logger.error(f"Invalid file: {file_path}")
    return None


def write_yaml_file(file_path: Path | None, data: dict[str, Any] | None, **kwargs) -> None:
    if file_path is not None and data is not None:
        import yaml

        log_debug(f"Writing {file_path}")
        file_path.write_text(yaml.safe_dump(data, **kwargs))
