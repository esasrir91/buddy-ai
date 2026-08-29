import React, { useEffect, useRef, useState } from 'react'
import { useStore } from '../../store'

export default function TerminalPanel() {
  const termRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<any>(null)
  const fitRef = useRef<any>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const { workspace } = useStore()
  const [wsError, setWsError] = useState('')
  const [fallbackMode, setFallbackMode] = useState(false)
  const [cmd, setCmd] = useState('')
  const [history, setHistory] = useState<string[]>([])

  useEffect(() => {
    let disposed = false
    let xterm: any
    let fitAddon: any

    const init = async () => {
      try {
        // Dynamically import xterm to avoid SSR issues
        const { Terminal } = await import('@xterm/xterm')
        const { FitAddon } = await import('@xterm/addon-fit')
        const { WebLinksAddon } = await import('@xterm/addon-web-links')
        await import('@xterm/xterm/css/xterm.css')

        if (disposed || !termRef.current) return

        xterm = new Terminal({
          theme: {
            background: '#1e1e2e',
            foreground: '#cdd6f4',
            cursor: '#cdd6f4',
            black: '#45475a', red: '#f38ba8', green: '#a6e3a1', yellow: '#f9e2af',
            blue: '#89b4fa', magenta: '#cba6f7', cyan: '#89dceb', white: '#bac2de',
            brightBlack: '#585b70', brightRed: '#f38ba8', brightGreen: '#a6e3a1',
            brightYellow: '#f9e2af', brightBlue: '#89b4fa', brightMagenta: '#cba6f7',
            brightCyan: '#89dceb', brightWhite: '#a6adc8',
          },
          fontFamily: '"JetBrains Mono","Cascadia Code","Fira Code",Consolas,monospace',
          fontSize: 13,
          lineHeight: 1.4,
          cursorBlink: true,
          scrollback: 5000,
        })

        fitAddon = new FitAddon()
        xterm.loadAddon(fitAddon)
        xterm.loadAddon(new WebLinksAddon())
        xterm.open(termRef.current)
        fitAddon.fit()

        xtermRef.current = xterm
        fitRef.current = fitAddon

        // Try WebSocket PTY
        const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/terminal`
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          setWsError('')
          ws.send(JSON.stringify({ type: 'resize', cols: xterm.cols, rows: xterm.rows }))
          if (workspace) ws.send(JSON.stringify({ type: 'cwd', path: workspace }))
          xterm.onData((data: string) => {
            ws.send(JSON.stringify({ type: 'input', data }))
          })
        }

        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'output') xterm.write(msg.data)
          } catch {
            xterm.write(e.data)
          }
        }

        ws.onerror = () => {
          setWsError('WebSocket unavailable')
          setFallbackMode(true)
          xterm.writeln('\r\n\x1b[33m[PTY unavailable – using fallback shell]\x1b[0m\r\n')
        }

        ws.onclose = () => {
          if (!disposed) xterm.writeln('\r\n\x1b[31m[Terminal disconnected]\x1b[0m\r\n')
        }

        // Resize observer
        const ro = new ResizeObserver(() => fitAddon?.fit())
        if (termRef.current) ro.observe(termRef.current)

        return () => {
          disposed = true
          ro.disconnect()
          ws.close()
          xterm.dispose()
        }
      } catch (e: any) {
        setFallbackMode(true)
      }
    }

    const cleanup = init()
    return () => {
      disposed = true
      cleanup.then(fn => fn?.())
    }
  }, [])

  // Fallback: simple POST /api/run terminal
  const runCmd = async () => {
    if (!cmd.trim()) return
    const { runCmd: apiRun } = await import('../../api')
    setHistory(prev => [...prev, `$ ${cmd}`])
    setCmd('')
    try {
      const result = await apiRun(cmd, workspace || undefined)
      setHistory(prev => [...prev, result.output ?? ''])
    } catch (e: any) {
      setHistory(prev => [...prev, `Error: ${e.message}`])
    }
  }

  if (fallbackMode) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'var(--font-mono)', fontSize: 12.5, background: '#1e1e2e', color: '#cdd6f4' }}>
        <div style={{ flex: 1, overflow: 'auto', padding: '6px 10px' }}>
          {history.map((line, i) => (
            <div key={i} style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{line}</div>
          ))}
        </div>
        <div style={{ display: 'flex', padding: '4px 8px', borderTop: '1px solid var(--border)', gap: 6 }}>
          <span style={{ color: 'var(--ok)' }}>$</span>
          <input
            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'inherit', fontFamily: 'inherit', fontSize: 'inherit' }}
            value={cmd}
            onChange={e => setCmd(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && runCmd()}
            placeholder="Enter command…"
            autoFocus
          />
          <button className="btn btn--xs btn--ghost" onClick={runCmd}>Run</button>
        </div>
      </div>
    )
  }

  return (
    <div ref={termRef} className="terminal-wrap" style={{ background: '#1e1e2e', overflow: 'hidden' }} />
  )
}
