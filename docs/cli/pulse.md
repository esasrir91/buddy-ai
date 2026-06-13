# PULSE CLI Commands

The `buddy pulse` sub-command group manages PULSE virtual employees.

## Start the Web UI

```bash
buddy pulse start [--port 8888] [--host 0.0.0.0] [--reload]
```

Launches the PULSE FastAPI backend and serves the React dashboard.
Open `http://localhost:8888` in your browser to access the UI.

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8888` | HTTP port |
| `--host` | `127.0.0.1` | Bind address |
| `--reload` | off | Auto-reload on file changes (dev mode) |

## Create an Employee (interactive)

```bash
buddy pulse create
```

Interactive wizard that prompts for name, role, department, skills, and model settings,
then writes a `pulse_employee.json` config file.

## Run a Document KT Session

```bash
buddy pulse kt --employee <id> --source <path_or_url> --name "Session Name" --giver "Alice"
```

Runs an asynchronous knowledge transfer from a file, URL, or raw text.
Prints the KT summary (mental model, key concepts, confidence score) to the terminal.

## Show Module Status

```bash
buddy pulse status
```

Prints a table showing which PULSE sub-modules are available in the current environment.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `PULSE_HOST` | Default host for `buddy pulse start` |
| `PULSE_PORT` | Default port for `buddy pulse start` |

!!! tip "Setting Keys via the UI"
    API keys can also be configured directly in the PULSE web UI under **Settings → AI Model & API Keys**,
    without needing to set environment variables manually.
