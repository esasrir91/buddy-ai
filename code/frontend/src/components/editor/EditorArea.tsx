import React, { useRef, useState, useCallback, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { useStore } from '../../store'
import { fsWrite, getCompletion, setWorkspace as apiSetWorkspace, getWorkspace, getRecents } from '../../api'
import InlineEdit from './InlineEdit'
import AuraLogo from '../AuraLogo'
import type { editor as MonacoEditor } from 'monaco-editor'

export default function EditorArea() {
  const {
    openTabs, activeTabId,
    setActiveTab, closeTab, updateTabContent, markTabDirty,
    diagnostics, setDiagnostics, theme,
    bottomPanelVisible, setBottomTab, setBottomPanelVisible,
  } = useStore()

  const activeTab = openTabs.find(t => t.id === activeTabId) ?? null
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null)
  const monacoRef = useRef<any>(null)
  const [showInlineEdit, setShowInlineEdit] = useState(false)
  const ghostDecorations = useRef<string[]>([])
  const completionTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ghost text completion handler
  const requestCompletion = useCallback(async () => {
    const editor = editorRef.current
    if (!editor || !activeTab) return
    const model = editor.getModel()
    if (!model) return
    const pos = editor.getPosition()
    if (!pos) return
    const offset = model.getOffsetAt(pos)
    const full = model.getValue()
    const before = full.slice(0, offset)
    const after = full.slice(offset)

    try {
      const { completion } = await getCompletion({
        file_path: activeTab.path,
        content_before: before.slice(-2000),
        content_after: after.slice(0, 500),
        language: activeTab.language,
      })
      if (!completion || !editorRef.current) return
      // Show as ghost text via inline decoration
      const currentPos = editorRef.current.getPosition()
      if (!currentPos || currentPos.lineNumber !== pos.lineNumber || currentPos.column !== pos.column) return

      const monaco = monacoRef.current
      if (!monaco) return
      const lines = completion.split('\n')
      const firstLine = lines[0]
      const decorations = editorRef.current.deltaDecorations(ghostDecorations.current, [
        {
          range: new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column),
          options: {
            after: {
              content: firstLine,
              inlineClassName: 'ghost-text',
            },
          },
        },
      ])
      ghostDecorations.current = decorations

      // Accept on Tab
      const disposeAccept = editorRef.current.onKeyDown((e: any) => {
        if (e.keyCode === monaco.KeyCode.Tab) {
          e.preventDefault()
          e.stopPropagation()
          const pos2 = editorRef.current!.getPosition()
          if (pos2) {
            editorRef.current!.executeEdits('ghost', [{
              range: new monaco.Range(pos2.lineNumber, pos2.column, pos2.lineNumber, pos2.column),
              text: completion,
              forceMoveMarkers: true,
            }])
          }
          clearGhost()
          disposeAccept.dispose()
        } else if (e.keyCode !== monaco.KeyCode.End) {
          clearGhost()
          disposeAccept.dispose()
        }
      })
    } catch {}
  }, [activeTab])

  const clearGhost = useCallback(() => {
    if (!editorRef.current) return
    ghostDecorations.current = editorRef.current.deltaDecorations(ghostDecorations.current, [])
  }, [])

  const handleEditorMount = (editor: MonacoEditor.IStandaloneCodeEditor, monaco: any) => {
    editorRef.current = editor
    monacoRef.current = monaco

    // ghost text CSS injection
    const style = document.createElement('style')
    style.textContent = '.ghost-text { color: var(--text-faint) !important; opacity: .65; font-style: italic; }'
    document.head.appendChild(style)

    // Cmd+K → inline edit
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyK, () => {
      setShowInlineEdit(true)
    })

    // Cmd+S → save
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      const tab = useStore.getState().openTabs.find(t => t.id === useStore.getState().activeTabId)
      if (tab) {
        fsWrite(tab.path, tab.content)
          .then(() => markTabDirty(tab.id, false))
          .catch(() => {})
      }
    })

    // trigger completion on typing
    editor.onDidChangeModelContent(() => {
      clearGhost()
      if (completionTimer.current) clearTimeout(completionTimer.current)
      completionTimer.current = setTimeout(requestCompletion, 800)
    })

    editor.onDidChangeCursorPosition(() => {
      clearGhost()
      if (completionTimer.current) clearTimeout(completionTimer.current)
    })

    // push diagnostics to Monaco
    syncDiagnostics(editor, monaco)
  }

  // sync diagnostics to Monaco markers
  const syncDiagnostics = (editor: any, monaco: any) => {
    const { diagnostics } = useStore.getState()
    const model = editor.getModel()
    if (!model) return
    const markers = diagnostics
      .filter(d => model.uri.path.endsWith(d.path.replace(/\\/g, '/')))
      .map(d => ({
        severity: d.severity === 'error' ? monaco.MarkerSeverity.Error :
          d.severity === 'warning' ? monaco.MarkerSeverity.Warning :
          d.severity === 'info' ? monaco.MarkerSeverity.Info :
          monaco.MarkerSeverity.Hint,
        message: d.message,
        startLineNumber: d.line,
        startColumn: d.column,
        endLineNumber: d.endLine ?? d.line,
        endColumn: d.endColumn ?? d.column + 1,
        source: d.source ?? 'Aura',
      }))
    monaco.editor.setModelMarkers(model, 'aura', markers)
  }

  useEffect(() => {
    if (editorRef.current && monacoRef.current) {
      syncDiagnostics(editorRef.current, monacoRef.current)
    }
  }, [diagnostics])

  const handleContentChange = useCallback((value: string | undefined) => {
    if (value == null || !activeTabId) return
    updateTabContent(activeTabId, value)
    markTabDirty(activeTabId, true)
  }, [activeTabId, updateTabContent, markTabDirty])

  // Problem count for status bar
  const errCount = diagnostics.filter(d => d.severity === 'error').length
  const warnCount = diagnostics.filter(d => d.severity === 'warning').length

  return (
    <div className="editor-area">
      {/* Tab bar */}
      {openTabs.length > 0 && (
        <div className="tab-bar">
          {openTabs.map(tab => (
            <div
              key={tab.id}
              className={`editor-tab${tab.id === activeTabId ? ' editor-tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.path}
            >
              <span className="editor-tab__icon">{fileIcon(tab.name)}</span>
              <span className="editor-tab__name">{tab.name}</span>
              {tab.dirty && <span className="editor-tab__dirty" title="Unsaved changes" />}
              <button
                className="editor-tab__close"
                onClick={e => { e.stopPropagation(); closeTab(tab.id) }}
                title="Close"
              >×</button>
            </div>
          ))}
        </div>
      )}

      {/* Breadcrumbs */}
      {activeTab && (
        <div className="breadcrumbs">
          {activeTab.path.split(/[\\/]/).filter(Boolean).map((part, i, arr) => (
            <React.Fragment key={i}>
              {i > 0 && <span className="breadcrumbs__sep">›</span>}
              <span className={`breadcrumbs__part${i === arr.length - 1 ? ' breadcrumbs__part--active' : ''}`}>
                {part}
              </span>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Editor */}
      {activeTab ? (
        <div className="editor-body">
          <Editor
            key={activeTab.id}
            path={activeTab.path}
            defaultValue={activeTab.content}
            language={activeTab.language}
            theme={theme === 'dark' ? 'vs-dark' : 'vs'}
            onChange={handleContentChange}
            onMount={handleEditorMount}
            options={{
              fontSize: 14,
              fontFamily: '"JetBrains Mono", "Cascadia Code", "Fira Code", Consolas, monospace',
              fontLigatures: true,
              minimap: { enabled: true, maxColumn: 60 },
              scrollBeyondLastLine: false,
              wordWrap: 'off',
              renderLineHighlight: 'line',
              smoothScrolling: true,
              cursorBlinking: 'smooth',
              cursorSmoothCaretAnimation: 'on',
              renderWhitespace: 'selection',
              bracketPairColorization: { enabled: true },
              'semanticHighlighting.enabled': true,
              tabSize: 2,
              insertSpaces: true,
              suggest: { showStatusBar: true },
              quickSuggestions: { strings: 'on', other: 'on', comments: 'off' },
              parameterHints: { enabled: true },
              autoClosingBrackets: 'always',
              autoClosingQuotes: 'always',
              formatOnType: false,
              formatOnPaste: true,
              padding: { top: 8 },
            }}
          />
          {showInlineEdit && (
            <InlineEdit
              editor={editorRef.current}
              monaco={monacoRef.current}
              filePath={activeTab.path}
              onClose={() => setShowInlineEdit(false)}
            />
          )}
        </div>
      ) : (
        <EditorWelcome />
      )}
    </div>
  )
}

function fileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    ts: '🔷', tsx: '⚛', js: '📜', jsx: '⚛',
    py: '🐍', rs: '🦀', go: '🐹',
    json: '{ }', yaml: '📋', yml: '📋', toml: '⚙',
    md: '📝', txt: '📄', html: '🌐', css: '🎨',
    sh: '$', ps1: '$', bat: '$',
    sql: '🗄',
  }
  return map[ext] ?? '📄'
}

function EditorWelcome() {
  const { setSidebarView, setAgentPaneVisible } = useStore()
  const [recents, setRecents] = React.useState<string[]>([])

  React.useEffect(() => {
    getRecents().then(r => setRecents(r.recent)).catch(() => {})
  }, [])

  const openFolder = () => {
    const path = window.prompt('Enter folder path to open:')
    if (!path) return
    apiSetWorkspace(path).then(() => getWorkspace()).then(({ path: resolved }) => {
      useStore.getState().setWorkspace(resolved)
    }).catch(e => alert(`Cannot open: ${e.message}`))
  }

  return (
    <div className="editor-empty">
      <div className="editor-empty__logo">
        <AuraLogo size={64} />
      </div>
      <div className="editor-empty__title">Aura</div>
      <div className="editor-empty__sub">AI Coding IDE</div>

      <div className="editor-empty__actions">
        <button className="editor-empty__action" onClick={openFolder}>
          <span className="editor-empty__action-label">📂 Open Folder</span>
          <span className="editor-empty__action-kbd">Ctrl+O</span>
        </button>
        <button className="editor-empty__action" onClick={() => {
          useStore.getState().setBottomPanelVisible(true)
          useStore.getState().setBottomTab('terminal')
        }}>
          <span className="editor-empty__action-label">$ Open Terminal</span>
          <span className="editor-empty__action-kbd">Ctrl+`</span>
        </button>
        <button className="editor-empty__action" onClick={() => setAgentPaneVisible(true)}>
          <span className="editor-empty__action-label">✨ Start Agent</span>
          <span className="editor-empty__action-kbd">Ctrl+L</span>
        </button>
        <button className="editor-empty__action" onClick={() => setSidebarView('explorer')}>
          <span className="editor-empty__action-label">🔍 Browse Files</span>
          <span className="editor-empty__action-kbd">Ctrl+P</span>
        </button>
      </div>

      {recents.length > 0 && (
        <div className="editor-empty__recents">
          <div className="editor-empty__recents-title">Recent</div>
          {recents.slice(0, 5).map(p => (
            <div
              key={p}
              className="editor-empty__recent-item"
              onClick={() => {
                apiSetWorkspace(p).then(() => getWorkspace()).then(({ path: resolved }) => {
                  useStore.getState().setWorkspace(resolved)
                }).catch(() => {})
              }}
            >
              <span>📁</span>
              <span style={{ fontWeight: 600 }}>{p.split(/[\\/]/).filter(Boolean).pop()}</span>
              <span style={{ fontSize: 10.5, color: 'var(--text-faint)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}



