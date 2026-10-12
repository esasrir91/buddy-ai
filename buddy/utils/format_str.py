def remove_indent(s: str | None) -> str | None:
    """
    Remove the indent from a string.

    Args:
        s (str): String to remove indent from

    Returns:
        str: String with indent removed
    """
    if s is not None and isinstance(s, str):
        return "\n".join([line.strip() for line in s.split("\n")])
    return None
