from datetime import datetime, timezone


def current_datetime() -> datetime:
    return datetime.now().astimezone().replace(tzinfo=None)


def current_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


def current_datetime_utc_str() -> str:
    return current_datetime_utc().strftime("%Y-%m-%dT%H:%M:%S")
