const { spawn } = require('child_process')
const http = require('http')
const path = require('path')

const DEFAULT_PORT = 8888
const HEALTH_PATH = '/api/pulse/health'
const STARTUP_TIMEOUT_MS = 120_000
const POLL_INTERVAL_MS = 500

/**
 * Resolve the command used to start the PULSE backend.
 * Override with BUDDY_PYTHON (python exe) or BUDDY_CMD (full buddy executable).
 */
function resolveBackendCommand(port) {
  const args = ['pulse', 'start', '--host', '127.0.0.1', '--port', String(port), '--no-browser']

  if (process.env.BUDDY_CMD) {
    return { command: process.env.BUDDY_CMD, args, shell: false }
  }

  if (process.env.BUDDY_USE_PYTHON !== '1') {
    return { command: 'buddy', args, shell: process.platform === 'win32' }
  }

  const python = process.env.BUDDY_PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
  return {
    command: python,
    args: ['-m', 'buddy.cli.entrypoint', ...args],
    shell: process.platform === 'win32',
  }
}

function checkHealth(port) {
  return new Promise((resolve) => {
    const req = http.get(
      {
        hostname: '127.0.0.1',
        port,
        path: HEALTH_PATH,
        timeout: 2000,
      },
      (res) => {
        res.resume()
        resolve(res.statusCode === 200)
      },
    )
    req.on('error', () => resolve(false))
    req.on('timeout', () => {
      req.destroy()
      resolve(false)
    })
  })
}

async function waitForReady(port, timeoutMs = STARTUP_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await checkHealth(port)) {
      return true
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
  }
  return false
}

function startBackend(port = DEFAULT_PORT) {
  const { command, args, shell } = resolveBackendCommand(port)
  const env = {
    ...process.env,
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8',
  }

  const child = spawn(command, args, {
    env,
    shell,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    cwd: path.resolve(__dirname, '..', '..'),
  })

  const prefix = '[PULSE backend]'
  child.stdout?.on('data', (chunk) => process.stdout.write(`${prefix} ${chunk}`))
  child.stderr?.on('data', (chunk) => process.stderr.write(`${prefix} ${chunk}`))

  child.on('error', (err) => {
    console.error(`${prefix} failed to start:`, err.message)
  })

  return child
}

module.exports = {
  DEFAULT_PORT,
  STARTUP_TIMEOUT_MS,
  checkHealth,
  waitForReady,
  startBackend,
  resolveBackendCommand,
}
