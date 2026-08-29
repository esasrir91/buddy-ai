import React, { useState, useRef, useEffect, useCallback } from 'react'
import { streamInlineEdit, fsWrite } from '../../api'
import { useStore } from '../../store'

interface Props {
  editor: any
  monaco: any
  filePath: string
  onClose: () => void
}

type Phase = 'input' | 'generating' | 'review'

export default function InlineEdit({ editor, monaco, filePath, onClose }: Props) {
  const { updateTabContent, markTabDirty, openTabs, activeTabId } = useStore()
  const [instruction, setInstruction] = useState('')
  const [phase, setPhase] = useState<Phase>('input')
  const [generated, setGenerated] = useState('')
  const [selectionText, setSelectionText] = useState('')
  const [selectionRange, setSelectionRange] = useState<any>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!editor || !monaco) return
    const sel = editor.getSelection()
    const model = editor.getModel()
    if (sel && model && !sel.isEmpty()) {
      setSelectionText(model.getValueInRange(sel))
      setSelectionRange(sel)
    } else {
      // use full visible range or current line
      const pos = editor.getPosition()
      if (pos) {
        const model = editor.getModel()
        const lineText = model?.getLineContent(pos.lineNumber) ?? ''
        setSelectionText(lineText)
        const range = new monaco.Range(pos.lineNumber, 1, pos.lineNumber, lineText.length + 1)
        setSelectionRange(range)
      }
    }
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [editor, monaco])

  const doGenerate = useCallback(async () => {
    if (!instruction.trim() || !editor) return
    setPhase('generating')
    setGenerated('')
    abortRef.current = new AbortController()

    try {
      await streamInlineEdit(
        {
          file_path: filePath,
          selection: selectionText,
          instruction,
          start_line: selectionRange?.startLineNumber ?? 1,
        },
        (ev) => {
          if (ev.type === 'text' && typeof ev.content === 'string') {
            setGenerated(prev => prev + ev.content)
          } else if (ev.type === 'done') {
            setPhase('review')
          }
        },
        abortRef.current.signal,
      )
      setPhase('review')
    } catch (e: any) {
      if (e.name === 'AbortError') return
      setGenerated(String(e.message ?? e))
      setPhase('review')
    }
  }, [instruction, selectionText, selectionRange, filePath, editor])

  const apply = useCallback(() => {
    if (!editor || !monaco || !selectionRange) return
    editor.executeEdits('inline-edit', [{
      range: selectionRange,
      text: generated,
      forceMoveMarkers: true,
    }])
    // update store
    const tab = openTabs.find(t => t.id === activeTabId)
    if (tab) {
      const model = editor.getModel()
      if (model) {
        updateTabContent(tab.id, model.getValue())
        markTabDirty(tab.id, true)
      }
    }
    onClose()
  }, [editor, monaco, selectionRange, generated, openTabs, activeTabId])

  const reject = useCallback(() => {
    abortRef.current?.abort()
    onClose()
  }, [onClose])

  const style: React.CSSProperties = {
    position: 'absolute',
    top: '12%',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 100,
    width: 'min(600px, 90%)',
  }

  return (
    <div className="inline-edit-widget" style={style}>
      <div className="inline-edit-widget__header">
        <span>✨ Inline Edit — {filePath.split(/[\\/]/).pop()}</span>
        <button className="icon-btn" onClick={reject}>✕</button>
      </div>

      {phase === 'input' && (
        <>
          {selectionText && (
            <div className="inline-edit-widget__preview">{selectionText.slice(0, 300)}{selectionText.length > 300 ? '…' : ''}</div>
          )}
          <div className="inline-edit-widget__input-row">
            <input
              ref={inputRef}
              className="inline-edit-widget__input"
              placeholder="Describe the change… (Enter to generate)"
              value={instruction}
              onChange={e => setInstruction(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') doGenerate()
                if (e.key === 'Escape') reject()
              }}
            />
            <button className="btn btn--primary btn--sm" onClick={doGenerate} disabled={!instruction.trim()}>
              Generate
            </button>
          </div>
        </>
      )}

      {phase === 'generating' && (
        <>
          <div className="inline-edit-widget__header" style={{ borderTop: '1px solid var(--border)' }}>
            <span style={{ color: 'var(--accent-ai)' }}>⟳ Generating…</span>
            <button className="btn btn--xs btn--ghost" onClick={() => { abortRef.current?.abort(); setPhase('input') }}>Cancel</button>
          </div>
          <div className="inline-edit-widget__generating">{generated || ' '}</div>
        </>
      )}

      {phase === 'review' && (
        <>
          <div className="inline-edit-widget__diff">
            <div className="diff-old">
              <div style={{ fontSize: 10, color: 'var(--err)', marginBottom: 4, fontWeight: 600 }}>− Original</div>
              <pre>{selectionText}</pre>
            </div>
            <div className="diff-new">
              <div style={{ fontSize: 10, color: 'var(--ok)', marginBottom: 4, fontWeight: 600 }}>+ Generated</div>
              <pre>{generated}</pre>
            </div>
          </div>
          <div className="inline-edit-widget__accept-row">
            <button className="btn btn--sm btn--accept" onClick={apply}>✓ Accept</button>
            <button className="btn btn--sm btn--ghost" onClick={reject}>✕ Reject</button>
            <button className="btn btn--sm btn--ghost" onClick={() => setPhase('input')}>✏ Edit instruction</button>
          </div>
        </>
      )}
    </div>
  )
}
