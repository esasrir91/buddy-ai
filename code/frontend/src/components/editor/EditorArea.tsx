import React, { useRef, useState, useCallback, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { useStore } from '../../store'
import { fsWrite, getCompletion } from '../../api'
import InlineEdit from './InlineEdit'
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
      {/* Tabs */}
      {openTabs.length > 0 && (
        <div className="tabs-bar">
          {openTabs.map(tab => (
            <div
              key={tab.id}
              className={`editor-tab${tab.id === activeTabId ? ' editor-tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.path}
            >
              {tab.dirty && <span className="editor-tab__dot" />}
              <span>{tab.name}</span>
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
          {activeTab.path.split(/[\\/]/).map((part, i, arr) => (
            <React.Fragment key={i}>
              {i > 0 && <span>/</span>}
              <a title={part}>{part}</a>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Editor */}
      {activeTab ? (
        <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
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
        <div className="editor-welcome">
          <h2>Aura</h2>
          <p>Open a file from the Explorer,<br />or start a conversation with the Agent.</p>
          <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            <span><kbd>Ctrl+P</kbd> Open file</span>
            <span><kbd>Ctrl+L</kbd> Agent chat</span>
            <span><kbd>Ctrl+K</kbd> Inline edit</span>
            <span><kbd>Ctrl+`</kbd> Terminal</span>
          </div>
        </div>
      )}
    </div>
  )
}
