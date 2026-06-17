# Workspace Management

The `buddy ws` group (`buddy.cli.ws.ws_cli`) creates workspaces and manages the
resources they declare. A workspace is a directory whose `resources.py` (or
similar) file defines infrastructure across environments and infra types.

## Commands

| Command | Description |
|---------|-------------|
| `buddy ws create` | Create a new workspace in the current directory from a template |
| `buddy ws setup [path]` | Set up a workspace from the current directory or a path |
| `buddy ws up [filter]` | Create resources for the active workspace |
| `buddy ws down [filter]` | Delete resources for the active workspace |
| `buddy ws patch [filter]` | Update resources for the active workspace |
| `buddy ws restart [filter]` | Run `down` then `up` |
| `buddy ws config` | Print the active workspace config |
| `buddy ws delete` | Delete a workspace **record** (no files are removed) |

Run `buddy ws` with no command to print help.

## Creating a workspace

```bash
buddy ws create -t ai-app                # create an `ai-app` in the current dir
buddy ws create -t ai-app -n my-ai-app   # ...named `my-ai-app`
```

`create` accepts `-n/--name`, `-t/--template`, `-u/--url` (URL of a starter
template), and `-d/--debug`.

## Starting and stopping resources

```bash
buddy ws up           # deploy all resources
buddy ws up dev       # deploy all dev resources
buddy ws up prd:aws   # deploy prd resources on aws infra
buddy ws down         # delete all resources
```

`up`, `down`, `patch`, and `restart` accept a positional **resource filter** in
the form `ENV:INFRA:GROUP:NAME:TYPE`, or the equivalent options:

| Option | Filters by |
|--------|-----------|
| `-e`, `--env` | Environment (e.g. `dev`, `stg`, `prd`) |
| `-i`, `--infra` | Infra type (e.g. `docker`, `aws`) |
| `-g`, `--group` | Group name |
| `-n`, `--name` | Resource name |
| `-t`, `--type` | Resource type |

Shared flags include `-dr/--dry-run` (print resources and exit), `-y/--yes`
(skip confirmation), `-f/--force`, `-d/--debug`, and (for `up`/`patch`/`restart`)
`-p/--pull` to pull images where applicable.

```bash
buddy ws up prd:aws --dry-run    # preview without deploying
buddy ws down -e dev -y          # tear down dev, no prompt
```

## Inspecting and removing

```bash
buddy ws config            # print active workspace config
buddy ws delete            # remove the active workspace record
buddy ws delete -ws idata  # remove a named workspace record
buddy ws delete -a         # remove all workspace records
```

!!! warning "`delete` only removes the record"
    `buddy ws delete` removes Buddy's record of the workspace. It does **not**
    delete any files on disk or resources in the cloud — clean those up
    separately.

## Top-level equivalents

`buddy start`, `buddy stop`, `buddy patch`, and `buddy restart` operate on a
`resources.py` path directly (defaulting to `resources.py` in the current
directory) and share the same filter flags. See the [CLI Overview](overview.md).

## See also

- [CLI Overview](overview.md) · [Configuration](configuration.md)
- [Cloud Platforms](../deployment/cloud.md)
