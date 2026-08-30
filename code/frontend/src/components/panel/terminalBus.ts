/** Bridge so agent shell events write into the live xterm (one unified terminal). */
type Writer = (data: string) => void

const writers = new Map<string, Writer>()
let activeId: string | null = null

export function registerTerminalWriter(id: string, write: Writer) {
  writers.set(id, write)
  return () => {
    writers.delete(id)
    if (activeId === id) activeId = null
  }
}

export function setActiveTerminalWriter(id: string | null) {
  activeId = id
}

/** Write into the active interactive terminal (Cursor-style — no separate Output channel). */
export function writeToActiveTerminal(data: string) {
  if (!data) return
  const id = activeId
  const w = (id && writers.get(id)) || [...writers.values()][0]
  w?.(data)
}
