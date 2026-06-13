# CLI Overview

The `buddy` CLI provides commands for workspace management, training, and configuration.

## Installation

```bash
pip install buddy-ai
buddy --version  # buddy-ai version: 2.0.0
buddy --help
```

## Commands

| Command | Description |
|---------|-------------|
| `buddy --version` | Show installed version |
| `buddy setup` | Authenticate with Buddy platform |
| `buddy init` | Initialise Buddy in current directory |
| `buddy init -r` | Reset configuration |
| `buddy config` | Show current configuration |
| `buddy ping` | Test connectivity to Buddy servers |
| `buddy set -ws <name>` | Set active workspace |
| `buddy start [file]` | Start resources from a resources.py file |
| `buddy stop [file]` | Stop resources |
| `buddy patch [file]` | Update/patch running resources |
| `buddy restart [file]` | Restart resources |
| `buddy ws` | Workspace sub-commands |
| `buddy train` | Training sub-commands |

## Workspace Commands

```bash
buddy ws create      # Create a new workspace
buddy ws up          # Start workspace
buddy ws down        # Stop workspace
buddy ws status      # Show workspace status
```

## Training Commands

```bash
buddy train start --data ./data --model microsoft/DialoGPT-small
buddy train status
buddy train stop
```

## Getting Help

```bash
buddy --help
buddy ws --help
buddy train --help
```
