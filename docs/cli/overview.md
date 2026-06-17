# CLI Overview

Installing `buddy-ai` adds the `buddy` command (a [Typer](https://typer.tiangolo.com/)
app, entry point `buddy.cli.entrypoint:main`). Run it with no arguments to see
help.

## Installation

```bash
pip install buddy-ai
buddy --version   # buddy-ai version: 2.2.0
buddy --help
```

`--version` / `-v` prints the installed version and exits.

## Top-level commands

These operate on your Buddy configuration and on a `resources.py` workspace file.

| Command | Description |
|---------|-------------|
| `buddy setup` | Set up Buddy and log in to the platform |
| `buddy init` | Initialize the Buddy **config** (use `-r`/`--reset` to reset, `-l`/`--login` to log in) |
| `buddy reset` | Reset the existing Buddy configuration |
| `buddy ping` | Test connectivity and authentication |
| `buddy config` | Print your current Buddy config |
| `buddy set -ws <name>` | Set the current directory (or named workspace) as active |
| `buddy start [file]` | Start resources defined in a `resources.py` file |
| `buddy stop [file]` | Stop those resources |
| `buddy patch [file]` | Update/patch those resources |
| `buddy restart [file]` | Stop then start those resources |

!!! note "`buddy init` initializes config, not a project"
    `buddy init` sets up Buddy's own configuration on your machine — it does
    **not** scaffold a new project directory. To create a workspace project, use
    [`buddy ws create`](workspace.md).

Most commands accept `-d`/`--debug` to print debug logs. The `start`/`stop`/
`patch`/`restart` commands share resource filters (`-e/--env`, `-i/--infra`,
`-g/--group`, `-n/--name`, `-t/--type`), plus `-dr/--dry-run`, `-y/--yes`, and
`-f/--force`.

## Command groups

| Group | Purpose | Reference |
|-------|---------|-----------|
| `buddy ws` | Create and manage workspaces & their resources | [Workspace Management](workspace.md) |
| `buddy train` | Train, test, and manage local models | [Training Commands](training.md) |
| `buddy pulse` | Run and manage the PULSE virtual employee | [PULSE Commands](pulse.md) |

!!! info "Optional groups load if available"
    The `train` and `pulse` groups are registered only when their dependencies
    import successfully. If `buddy train` isn't listed, install the training
    extra: `pip install "buddy-ai[training]"`.

## Getting help

```bash
buddy --help
buddy ws --help
buddy train --help
buddy <command> --help
```

## See also

- [Workspace Management](workspace.md)
- [Agent Commands](agents.md)
- [Training Commands](training.md)
- [Configuration](configuration.md)
