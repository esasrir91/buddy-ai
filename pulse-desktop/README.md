# Buddy AI Desktop

Cross-platform desktop app for the **Buddy AI autonomous assistant** (PULSE). Runs on **Windows** and **macOS**.

The desktop app wraps the existing PULSE stack:

- **Electron shell** — native window, system tray, runs in background
- **PULSE backend** — FastAPI + autonomous worker (`buddy pulse start`)
- **React UI** — full dashboard (tasks, chat, KT, memory, settings)

## Prerequisites

1. **Python 3.10+**
2. **Buddy AI installed** with PULSE dependencies:

```bash
pip install buddy-ai[all]
```

3. **Built UI** (first time only, from repo root):

```bash
cd pulse-ui
npm install
npm run build
```

Copy the build into the Python package if needed:

```bash
# From repo root — optional if running from editable install
cp -r pulse-ui/dist buddy/pulse/ui
```

4. **Node.js 18+** (for the desktop app itself)

## Run in development

```bash
cd pulse-desktop
npm install
npm start
```

The app will:

1. Start `buddy pulse start --no-browser --host 127.0.0.1 --port 8888`
2. Show a loading screen until the backend is healthy
3. Open the PULSE dashboard in a native window
4. Minimize to the **system tray** when you close the window (keeps the autonomous worker running)

## Configure LLM

On first launch, open **Settings** in the app and add your LLM provider + API key. The assistant runs tasks autonomously in the background once configured.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `PULSE_PORT` | Backend port (default `8888`) |
| `BUDDY_PYTHON` | Python executable if `buddy` is not on PATH |
| `BUDDY_USE_PYTHON=1` | Force `python -m buddy.cli.entrypoint` instead of `buddy` CLI |
| `BUDDY_CMD` | Full path to a custom launcher executable |
| `PULSE_DATA_DIR` | Where PULSE stores employee data (default `~/.pulse_data`) |

## Build installers

| Platform | File you get | Extension |
|----------|--------------|-----------|
| **Windows** | `Buddy AI Setup 2.1.0.exe` | `.exe` — double-click to install |
| **macOS** | `Buddy AI-2.1.0.dmg` | `.dmg` — open, drag app to Applications |

```bash
cd pulse-desktop
npm install

# Windows (.exe installer) — run on a Windows PC
npm run build:win

# macOS (.dmg installer) — must run on a Mac
npm run build:mac
```

Output folder: `pulse-desktop/dist/`

**Windows build tip:** If you see a symlink / privilege error, the project already disables code signing for local builds. You can also run:

```powershell
$env:CSC_IDENTITY_AUTO_DISCOVERY="false"
npm run build:win
```

**Mac builds cannot be created from Windows.** Use a Mac (or GitHub Actions with `macos-latest`) for the `.dmg`.

**Note:** Installers bundle the Electron desktop shell. Users still need Python + `buddy-ai` installed (`pip install buddy-ai[all]`), unless you add a bundled Python sidecar later.

## Architecture

```
┌─────────────────────────────────────┐
│  Electron (pulse-desktop)           │
│  ┌───────────────────────────────┐  │
│  │  BrowserWindow → :8888 UI     │  │
│  └───────────────────────────────┘  │
│  System tray — close hides, not quit│
│           │ spawn on startup        │
│  ┌───────────────────────────────┐  │
│  │  buddy pulse start            │  │
│  │  (PULSE API + autonomous loop)│  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         Data: ~/.pulse_data/
```

## Troubleshooting

**Backend won't start**

- Run manually: `buddy pulse start --no-browser`
- Ensure port 8888 is free
- Set `BUDDY_PYTHON=C:\Path\To\python.exe` on Windows if `buddy` is not found

**Blank UI after loading**

- Build the React UI: `cd pulse-ui && npm run build`
- Restart the desktop app

**WebSocket chat fails**

- Use the bundled UI served from the backend (same origin). The desktop app loads `http://127.0.0.1:8888` directly.
