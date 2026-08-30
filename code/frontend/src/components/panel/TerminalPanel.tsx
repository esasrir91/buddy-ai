import React, { useEffect, useRef, useCallback } from 'react'
import { useStore } from '../../store'
import {
  registerTerminalWriter,
  setActiveTerminalWriter,
} from './terminalBus'

function TerminalInstance({
  id,
  shell,
  active,
  workspace,
  onShellReady,
}: {
  id: string
  shell: string
  active: boolean
  workspace: string
  onShellReady?: (id: string, shellName: string) => void
}) {
  const hostRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<any>(null)
  const fitRef = useRef<any>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let disposed = false
    let ro: ResizeObserver | null = null
    let onDataDisp: { dispose: () => void } | null = null
    let unregister: (() => void) | null = null

    const init = async () => {
      try {
        const { Terminal } = await import('@xterm/xterm')
        const { FitAddon } = await import('@xterm/addon-fit')
        const { WebLinksAddon } = await import('@xterm/addon-web-links')
        // @ts-ignore
        await import('@xterm/xterm/css/xterm.css')

        if (disposed || !hostRef.current) return

        const xterm = new Terminal({
          theme: {
            background: '#1e1e1e',
            foreground: '#cccccc',
            cursor: '#aeafad',
            cursorAccent: '#1e1e1e',
            selectionBackground: '#264f78',
            selectionForeground: '#ffffff',
            black: '#000000',
            red: '#cd3131',
            green: '#0dbc79',
            yellow: '#e5e510',
            blue: '#2472c8',
            magenta: '#bc3fbc',
            cyan: '#11a8cd',
            white: '#e5e5e5',
            brightBlack: '#666666',
            brightRed: '#f14c4c',
            brightGreen: '#23d18b',
            brightYellow: '#f5f543',
            brightBlue: '#3b8eea',
            brightMagenta: '#d670d6',
            brightCyan: '#29b8db',
            brightWhite: '#e5e5e5',
          },
          fontFamily: 'Consolas, "Courier New", monospace',
          fontSize: 14,
          lineHeight: 1.2,
          cursorBlink: true,
          cursorStyle: 'block',
          scrollback: 5000,
          allowTransparency: false,
          convertEol: false,
          macOptionIsMeta: true,
          rightClickSelectsWord: true,
        })

        const fitAddon = new FitAddon()
        xterm.loadAddon(fitAddon)
        xterm.loadAddon(new WebLinksAddon())
        xterm.open(hostRef.current)

        // Wait a frame so layout has real size (avoid 0×0 fit)
        await new Promise(r => requestAnimationFrame(() => r(null)))
        try { fitAddon.fit() } catch { /* */ }

        xtermRef.current = xterm
        fitRef.current = fitAddon

        unregister = registerTerminalWriter(id, (data) => {
          try { xterm.write(data) } catch { /* */ }
        })
        if (active) setActiveTerminalWriter(id)

        const proto = location.protocol === 'https:' ? 'wss' : 'ws'
        const qs = new URLSearchParams({
          shell,
          cols: String(Math.max(20, xterm.cols || 80)),
          rows: String(Math.max(5, xterm.rows || 24)),
        })
        const ws = new WebSocket(`${proto}://${location.host}/ws/terminal?${qs}`)
        wsRef.current = ws

        const sendResize = () => {
          if (ws.readyState !== WebSocket.OPEN) return
          try { fitAddon.fit() } catch { /* */ }
          ws.send(JSON.stringify({
            type: 'resize',
            cols: xterm.cols,
            rows: xterm.rows,
          }))
        }

        ws.onopen = () => {
          sendResize()
          onDataDisp = xterm.onData(data => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'input', data }))
            }
          })
        }

        ws.onmessage = e => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'ready' && msg.shell) {
              onShellReady?.(id, msg.shell)
            } else if (msg.type === 'output') {
              xterm.write(msg.data)
            }
          } catch {
            xterm.write(e.data)
          }
        }

        ws.onerror = () => {
          xterm.writeln('\r\n\x1b[33m[Terminal connection error]\x1b[0m\r\n')
        }

        ws.onclose = (ev) => {
          if (!disposed) {
            if (ev.code === 1006 || ev.code === 1008 || ev.code === 1000) {
              // 403 / rejected handshake often shows as abnormal close
              xterm.writeln(
                '\r\n\x1b[33m[Terminal disconnected]\x1b[0m  ' +
                'Quit Aura fully and relaunch so the backend reloads.\r\n'
              )
            } else {
              xterm.writeln('\r\n\x1b[90m[Terminal session ended — press + for a new one]\x1b[0m\r\n')
            }
          }
        }

        ro = new ResizeObserver(() => sendResize())
        ro.observe(hostRef.current)
      } catch (err: any) {
        if (hostRef.current) {
          hostRef.current.textContent = `Terminal failed to start: ${err?.message || err}`
        }
      }
    }

    init()
    return () => {
      disposed = true
      unregister?.()
      ro?.disconnect()
      onDataDisp?.dispose()
      try { wsRef.current?.close() } catch { /* */ }
      try { xtermRef.current?.dispose() } catch { /* */ }
      xtermRef.current = null
      fitRef.current = null
      wsRef.current = null
    }
  }, [id, shell]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (active) setActiveTerminalWriter(id)
    if (!active) return
    const t = window.setTimeout(() => {
      try {
        fitRef.current?.fit()
        xtermRef.current?.focus()
        const ws = wsRef.current
        const xterm = xtermRef.current
        if (ws && xterm && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'resize', cols: xterm.cols, rows: xterm.rows }))
        }
      } catch { /* */ }
    }, 50)
    return () => clearTimeout(t)
  }, [active, id])

  return (
    <div
      className={`terminal-instance${active ? ' terminal-instance--active' : ''}`}
      data-term-id={id}
      aria-hidden={!active}
    >
      <div className="terminal-xterm-wrap" ref={hostRef} />
    </div>
  )
}

export default function TerminalPanel() {
  const { workspace, terminals, activeTerminalId, renameTerminal } = useStore()

  const onShellReady = useCallback((id: string, shellName: string) => {
    const t = useStore.getState().terminals.find(x => x.id === id)
    if (t && (t.name === t.shell || t.name.startsWith(`${t.shell} (`))) {
      const same = useStore.getState().terminals.filter(
        x => x.id !== id && x.shell === shellName
      ).length
      renameTerminal(id, same === 0 ? shellName : `${shellName} (${same + 1})`)
    }
  }, [renameTerminal])

  return (
    <div className="terminal-container">
      {terminals.map(t => (
        <TerminalInstance
          key={t.id}
          id={t.id}
          shell={t.shell}
          active={t.id === activeTerminalId}
          workspace={workspace}
          onShellReady={onShellReady}
        />
      ))}
    </div>
  )
}
