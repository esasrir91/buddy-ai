const {
  app,
  BrowserWindow,
  Tray,
  Menu,
  nativeImage,
  shell,
  dialog,
} = require('electron')
const path = require('path')
const kill = require('tree-kill')
const {
  DEFAULT_PORT,
  STARTUP_TIMEOUT_MS,
  startBackend,
  waitForReady,
  resolveBackendCommand,
} = require('./backend.cjs')

const PORT = Number(process.env.PULSE_PORT || DEFAULT_PORT)
const APP_URL = `http://127.0.0.1:${PORT}`

let mainWindow = null
let tray = null
let backendProcess = null
let isQuitting = false

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

function postLoadingMessage(type, message) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.executeJavaScript(
      `window.postMessage(${JSON.stringify({ type, message })}, '*')`,
    )
  }
}

function getTrayIcon() {
  const iconPath = path.join(__dirname, '..', 'assets', 'tray-icon.png')
  const fromFile = nativeImage.createFromPath(iconPath)
  if (!fromFile.isEmpty()) {
    return fromFile.resize({ width: 16, height: 16 })
  }

  return nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMElEQVR42mNgGAWjYBSM' +
      'glEwCkbBKBgFo2AUjIJRMApGwSgYBYMRBgYGAAAQBwL0T0Q0AAAAAElFTkSuQmCC',
  )
}

function createTray() {
  const icon = getTrayIcon()
  tray = new Tray(icon)
  tray.setToolTip('Buddy AI — Autonomous Assistant')

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Buddy AI',
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.focus()
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true
        app.quit()
      },
    },
  ])
  tray.setContextMenu(contextMenu)
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    title: 'Buddy AI',
    backgroundColor: '#0f172a',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.loadFile(path.join(__dirname, 'loading.html'))
  mainWindow.once('ready-to-show', () => mainWindow.show())

  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      mainWindow.hide()
    }
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.webContents.on('did-fail-load', (_event, _code, description, validatedURL) => {
    if (validatedURL.startsWith(APP_URL)) {
      postLoadingMessage(
        'buddy-error',
        `Could not load the app UI.<br/><br/>${description}`,
      )
    }
  })
}

function backendStartErrorHtml() {
  const { command, args } = resolveBackendCommand(PORT)
  const cmdLine = [command, ...args].join(' ')
  return (
    'Could not start the PULSE backend.<br/><br/>' +
    'Make sure Buddy AI is installed:<br/>' +
    '<code>pip install buddy-ai[all]</code><br/><br/>' +
    'Then try running manually:<br/>' +
    `<code>${cmdLine}</code><br/><br/>` +
    'You can set <code>BUDDY_PYTHON</code> to your Python executable if needed.'
  )
}

async function bootstrap() {
  createWindow()
  createTray()

  postLoadingMessage('buddy-status', 'Starting PULSE backend…')

  try {
    backendProcess = startBackend(PORT)
  } catch (err) {
    postLoadingMessage('buddy-error', backendStartErrorHtml())
    dialog.showErrorBox('Buddy AI', `Failed to launch backend: ${err.message}`)
    return
  }

  backendProcess.on('exit', (code) => {
    if (!isQuitting && code !== 0) {
      postLoadingMessage(
        'buddy-error',
        `PULSE backend exited unexpectedly (code ${code}).<br/><br/>${backendStartErrorHtml()}`,
      )
    }
  })

  postLoadingMessage('buddy-status', 'Waiting for assistant to come online…')
  const ready = await waitForReady(PORT, STARTUP_TIMEOUT_MS)

  if (!ready) {
    postLoadingMessage(
      'buddy-error',
      `Backend did not respond within ${STARTUP_TIMEOUT_MS / 1000}s.<br/><br/>${backendStartErrorHtml()}`,
    )
    dialog.showErrorBox(
      'Buddy AI',
      'The assistant backend did not start in time. Check that buddy-ai is installed and port 8888 is free.',
    )
    return
  }

  postLoadingMessage('buddy-status', 'Loading dashboard…')
  await mainWindow.loadURL(APP_URL)
}

function stopBackend() {
  if (backendProcess?.pid) {
    kill(backendProcess.pid, 'SIGTERM', () => {
      backendProcess = null
    })
  }
}

app.whenReady().then(bootstrap)

app.on('before-quit', () => {
  isQuitting = true
  stopBackend()
})

app.on('window-all-closed', () => {
  // Keep running in tray on all platforms
})

app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show()
  } else if (BrowserWindow.getAllWindows().length === 0) {
    bootstrap()
  }
})
