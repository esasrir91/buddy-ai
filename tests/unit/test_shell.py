import sys

from buddy.tools.shell import ShellTools


def test_shell_tool_runs_native_command_strings():
    assert ShellTools().run_shell_command("echo shell-ready").strip() == "shell-ready"


def test_shell_tool_preserves_direct_argv_and_tail_behavior():
    shell = ShellTools()
    command = [sys.executable, "-c", "print('first'); print('last')"]
    assert shell.run_shell_command(command, tail=1) == "last"
    assert shell.run_shell_command(command, tail=0) == ""
