import time

from buddy.tools import Toolkit
from buddy.utils.log import log_info


class SleepTools(Toolkit):
    def __init__(self, max_seconds: float = 300.0, **kwargs):
        if max_seconds < 0:
            raise ValueError("max_seconds must be nonnegative")
        self.max_seconds = max_seconds
        tools = []
        tools.append(self.sleep)

        super().__init__(name="sleep", tools=tools, **kwargs)

    def sleep(self, seconds: int) -> str:
        """Use this function to sleep for a given number of seconds."""
        if seconds < 0:
            return "Error: seconds must be nonnegative"
        if seconds > self.max_seconds:
            return f"Error: seconds cannot exceed {self.max_seconds}"
        log_info(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
        log_info(f"Awake after {seconds} seconds")
        return f"Slept for {seconds} seconds"
