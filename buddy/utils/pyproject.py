from pathlib import Path

from buddy.utils.log import log_debug, logger


def read_pyproject_buddy(pyproject_file: Path) -> dict | None:
    log_debug(f"Reading {pyproject_file}")
    try:
        import tomli

        pyproject_dict = tomli.loads(pyproject_file.read_text())
        BUDDY_conf = pyproject_dict.get("tool", {}).get("buddy", None)
        if BUDDY_conf is not None and isinstance(BUDDY_conf, dict):
            return BUDDY_conf
    except (OSError, UnicodeError, ValueError) as e:
        logger.error(f"Could not read {pyproject_file}: {e}")
    return None
