from dataclasses import asdict
from typing import Any


def isinstanceany(obj: Any, class_list: list[type]) -> bool:
    """Returns True if obj is an instance of the classes in class_list"""
    for cls in class_list:
        if isinstance(obj, cls):
            return True
    return False


def str_to_int(inp: str | None) -> int | None:
    """
    Safely converts a string value to integer.
    Args:
        inp: input string

    Returns: input string as int if possible, None if not
    """
    if inp is None:
        return None

    try:
        val = int(inp)
        return val
    except (TypeError, ValueError):
        return None


def is_empty(val: Any) -> bool:
    """Returns True if val is None or empty"""
    if val is None or val == "":
        return True
    try:
        return len(val) == 0
    except TypeError:
        return False


def get_image_str(repo: str, tag: str) -> str:
    return f"{repo}:{tag}"


def dataclass_to_dict(
    dataclass_object, exclude: set[str] | None = None, exclude_none: bool = False
) -> dict:
    final_dict = asdict(dataclass_object)
    if exclude:
        for key in exclude:
            final_dict.pop(key, None)
    if exclude_none:
        final_dict = {k: v for k, v in final_dict.items() if v is not None}
    return final_dict


def nested_model_dump(value):
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        return value.model_dump()
    elif isinstance(value, dict):
        return {k: nested_model_dump(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [nested_model_dump(item) for item in value]
    return value
