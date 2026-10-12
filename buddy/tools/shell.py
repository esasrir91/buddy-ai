from pathlib import Path
from typing import List, Optional, Union

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, log_info, logger


class ShellTools(Toolkit):
    def __init__(self, base_dir: Optional[Union[Path, str]] = None, timeout: float = 30.0, **kwargs):
        self.base_dir: Optional[Path] = None
        if base_dir is not None:
            self.base_dir = Path(base_dir) if isinstance(base_dir, str) else base_dir
        self.timeout = timeout

        tools = []
        tools.append(self.run_shell_command)

        super().__init__(name="shell_tools", tools=tools, **kwargs)

    def run_shell_command(self, args: Union[List[str], str], tail: int = 100) -> str:
        """Runs a shell command and returns the output or error.

        Args:
            args (Union[List[str], str]): A command string for the host shell, or an argument list
                for direct execution without a shell.
            tail (int): The number of lines to return from the output.

        Returns:
            str: The output of the command.
        """
        import subprocess

        try:
            if not args or (isinstance(args, list) and not all(isinstance(arg, str) for arg in args)):
                return "Error: command cannot be empty"
            if tail < 0:
                return "Error: tail must be greater than or equal to 0"

            log_info(f"Running shell command: {args}")
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=isinstance(args, str),
                cwd=str(self.base_dir) if self.base_dir else None,
                timeout=self.timeout,
            )
            log_debug(f"Result: {result}")
            log_debug(f"Return code: {result.returncode}")
            if result.returncode != 0:
                return f"Error: {result.stderr or result.stdout}"
            if tail == 0:
                return ""
            return "\n".join(result.stdout.splitlines()[-tail:])
        except Exception as e:
            logger.warning(f"Failed to run shell command: {e}")
            return f"Error: {e}"
