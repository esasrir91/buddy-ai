import { useState, useEffect, useCallback } from 'react'
import { usePulseStore } from '../hooks/usePulseStore'
import { listWorkspaceFiles, getWorkspaceFile, deleteWorkspaceFile } from '../api/pulse'
import type { WorkspaceFile } from '../types/pulse'

const EXT_ICON: Record<string, string> = {
  py: '🐍', js: '🟨', ts: '🔷', sql: '🗄️', md: '📝', json: '{}', yaml: '⚙️',
  yml: '⚙️', html: '🌐', sh: '💻', csv: '📊', txt: '📄',
}

const EXT_LANG: Record<string, string> = {
  py: 'python', js: 'javascript', ts: 'typescript', sql: 'sql', md: 'markdown',
  json: 'json', yaml: 'yaml', yml: 'yaml', html: 'html', sh: 'bash', csv: 'csv', txt: 'text',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

export default function Workspace() {
  const { employee } = usePulseStore()
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [wsPath, setWsPath] = useState('')
  const [selected, setSelected] = useState<WorkspaceFile | null>(null)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [fileLoading, setFileLoading] = useState(false)
  const [error, setError] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [filterExt, setFilterExt] = useState('all')
  const [search, setSearch] = useState('')

  const refresh = useCallback(async () => {
    if (!employee) return
    setLoading(true)
    try {
      const data = await listWorkspaceFiles(employee.employee_id)
      setFiles(data.files)
      setWsPath(data.workspace_path)
    } catch {
      setError('Failed to load workspace files.')
    } finally {
      setLoading(false)
    }
  }, [employee])

  useEffect(() => { refresh() }, [refresh])

  const openFile = async (file: WorkspaceFile) => {
    if (!employee) return
    setSelected(file)
    setContent('')
    setFileLoading(true)
    try {
      const data = await getWorkspaceFile(employee.employee_id, file.filename)
      setContent(data.content)
    } catch {
      setContent('Error loading file content.')
    } finally {
      setFileLoading(false)
    }
  }

  const handleDelete = async (filename: string) => {
    if (!employee) return
    try {
      await deleteWorkspaceFile(employee.employee_id, filename)
      if (selected?.filename === filename) {
        setSelected(null)
        setContent('')
      }
      setDeleteConfirm(null)
      refresh()
    } catch {
      setError('Failed to delete file.')
    }
  }

  const extensions = Array.from(new Set(files.map((f) => f.extension))).sort()
  const filteredFiles = files.filter((f) => {
    if (filterExt !== 'all' && f.extension !== filterExt) return false
    if (search && !f.filename.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  if (!employee) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500">
        No employee selected.
      </div>
    )
  }

  return (
    <div className="flex h-full gap-0">
      {/* Left panel — file list */}
      <div className="w-72 shrink-0 flex flex-col border-r border-zinc-800 bg-zinc-950">
        {/* Header */}
        <div className="px-4 py-3 border-b border-zinc-800">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <span>🗂️</span> Workspace
            </h2>
            <button
              onClick={refresh}
              className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
              title="Refresh"
            >
              ↻
            </button>
          </div>
          <input
            type="text"
            placeholder="Search files…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-2 py-1 rounded text-xs bg-zinc-800 border border-zinc-700 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
          />
          {extensions.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              <button
                onClick={() => setFilterExt('all')}
                className={`px-2 py-0.5 rounded-full text-[10px] border transition-colors ${filterExt === 'all' ? 'bg-blue-600 border-blue-500 text-white' : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}`}
              >
                all
              </button>
              {extensions.map((ext) => (
                <button
                  key={ext}
                  onClick={() => setFilterExt(ext)}
                  className={`px-2 py-0.5 rounded-full text-[10px] border transition-colors ${filterExt === ext ? 'bg-blue-600 border-blue-500 text-white' : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}`}
                >
                  .{ext}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* File list */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center h-20 text-zinc-500 text-sm">
              Loading…
            </div>
          )}
          {!loading && filteredFiles.length === 0 && (
            <div className="px-4 py-8 text-center text-zinc-500 text-xs">
              {files.length === 0 ? (
                <>
                  <p className="text-3xl mb-2">🗂️</p>
                  <p className="font-medium mb-1">No files yet</p>
                  <p>PULSE will create files here as it completes tasks.</p>
                </>
              ) : (
                'No files match your filter.'
              )}
            </div>
          )}
          {filteredFiles.map((file) => (
            <div
              key={file.filename}
              onClick={() => openFile(file)}
              className={`group px-4 py-2.5 cursor-pointer border-b border-zinc-800/50 transition-colors ${
                selected?.filename === file.filename
                  ? 'bg-blue-600/10 border-l-2 border-l-blue-500'
                  : 'hover:bg-zinc-800/50'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 min-w-0">
                  <span className="text-base shrink-0 mt-0.5">
                    {EXT_ICON[file.extension] || '📄'}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-zinc-200 truncate" title={file.filename}>
                      {file.filename}
                    </p>
                    <p className="text-[10px] text-zinc-500 mt-0.5">
                      {formatBytes(file.size_bytes)} · {formatDate(file.modified_at)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteConfirm(file.filename) }}
                  className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all shrink-0 text-xs mt-0.5"
                  title="Delete"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Footer with path */}
        {wsPath && (
          <div className="px-3 py-2 border-t border-zinc-800">
            <p className="text-[9px] text-zinc-600 break-all font-mono" title={wsPath}>
              {wsPath}
            </p>
          </div>
        )}
      </div>

      {/* Right panel — file viewer */}
      <div className="flex-1 flex flex-col bg-zinc-950 min-w-0">
        {selected ? (
          <>
            {/* File header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-900">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-lg shrink-0">{EXT_ICON[selected.extension] || '📄'}</span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-zinc-200 truncate">{selected.filename}</p>
                  <p className="text-xs text-zinc-500">
                    {formatBytes(selected.size_bytes)} · {EXT_LANG[selected.extension] || selected.extension} · modified {formatDate(selected.modified_at)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-4">
                <button
                  onClick={() => {
                    const blob = new Blob([content], { type: 'text/plain' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = selected.filename
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  className="px-3 py-1 text-xs rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 transition-colors"
                >
                  ⬇ Download
                </button>
                <button
                  onClick={() => { setSelected(null); setContent('') }}
                  className="text-zinc-500 hover:text-zinc-300 transition-colors text-sm"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {fileLoading ? (
                <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">
                  Loading…
                </div>
              ) : selected.extension === 'md' ? (
                <div
                  className="prose prose-invert prose-sm max-w-none"
                  dangerouslySetInnerHTML={{
                    __html: content
                      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
                      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
                      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
                      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                      .replace(/\*(.+?)\*/g, '<em>$1</em>')
                      .replace(/`(.+?)`/g, '<code class="bg-zinc-800 px-1 rounded text-xs">$1</code>')
                      .replace(/^- (.+)$/gm, '<li>$1</li>')
                      .replace(/\n\n/g, '<br/><br/>')
                  }}
                />
              ) : (
                <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed bg-zinc-900 rounded-lg p-4 border border-zinc-800">
                  {content}
                </pre>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-zinc-600">
            <div className="text-5xl mb-4">🗂️</div>
            <p className="text-sm font-medium text-zinc-500 mb-1">Select a file to view</p>
            <p className="text-xs text-zinc-600">
              PULSE saves generated files here as it completes tasks
            </p>
          </div>
        )}
      </div>

      {/* Delete confirm overlay */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setDeleteConfirm(null)}>
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-6 max-w-sm w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-zinc-200 mb-2">Delete file?</h3>
            <p className="text-xs text-zinc-400 mb-4 font-mono break-all">{deleteConfirm}</p>
            <div className="flex gap-3">
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="flex-1 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors"
              >
                Delete
              </button>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="fixed bottom-4 right-4 bg-red-900/80 text-red-200 text-xs px-4 py-2 rounded-lg border border-red-700">
          {error}
          <button onClick={() => setError('')} className="ml-3 text-red-400 hover:text-red-200">✕</button>
        </div>
      )}
    </div>
  )
}
