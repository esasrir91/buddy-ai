# CLI Configuration

The `buddy` CLI stores its configuration and credentials on your machine and
manages them through a handful of commands.

## Where config lives

Configuration is kept under `~/.config/buddy/`:

| File | Purpose |
|------|---------|
| `config.json` | User info, active workspace, and workspace map |
| `credentials.json` | Saved auth token |

These paths come from `BuddyCliSettings` (`buddy.cli.settings`) and can be
overridden with `BUDDY_`-prefixed environment variables.

## Setting up

```bash
buddy setup        # set up Buddy and log in to the platform
buddy init         # initialize the Buddy config
buddy init -l      # initialize and log in
```

`buddy setup` runs `initialize_buddy(login=True)`, which prepares the config
and starts the browser login flow. `buddy init` initializes the config;
add `-l`/`--login` to authenticate at the same time.

!!! note "`init` configures Buddy, not a project"
    `buddy init` sets up Buddy's own configuration — it does not create a project
    folder. Use [`buddy ws create`](workspace.md) to scaffold a workspace.

## Authentication

Logging in opens your browser to the Buddy sign-in page; once you approve, a
token is posted back to a short-lived local server and saved to
`credentials.json`. If the browser flow isn't available, set an API key via
environment variable instead:

```bash
export BUDDY_API_KEY=your_api_key   # PowerShell: $env:BUDDY_API_KEY="..."
```

Check connectivity and that you're authenticated:

```bash
buddy ping
```

## Viewing config

```bash
buddy config       # print user, active workspace, and all workspaces
```

## Resetting

```bash
buddy reset        # reset the existing configuration
buddy init -r      # equivalent: reset during init
```

Resetting removes the local Buddy configuration directory so you can start
fresh.

## Environment variables

`buddy` reads `BUDDY_`-prefixed variables (via `pydantic-settings`). Common ones:

| Variable | Effect |
|----------|--------|
| `BUDDY_API_KEY` | Authenticate without the browser flow |
| `BUDDY_API_RUNTIME` | Target runtime: `dev`, `stg`, or `prd` |

Provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …) are read by the model
clients, not the CLI config. See
[`.env.example`](https://github.com/esasrir91/buddy-ai/blob/main/.env.example)
for the full list.

## See also

- [CLI Overview](overview.md) · [Workspace Management](workspace.md)
