from typing import Any


def merge_dictionaries(a: dict[str, Any], b: dict[str, Any]) -> None:
    """
    Recursively merges two dictionaries.
    If there are conflicting keys, values from 'b' will take precedence.

    Args:
        a (Dict[str, Any]): The first dictionary to be merged.
        b (Dict[str, Any]): The second dictionary, whose values will take precedence.

    Returns:
        None: The function modifies the first dictionary in place.
    """
    for key, value in b.items():
        if key in a and isinstance(a[key], dict) and isinstance(value, dict):
            merge_dictionaries(a[key], value)
        else:
            a[key] = value
