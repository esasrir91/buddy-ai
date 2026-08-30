import React, { useEffect, useCallback } from 'react'
import { useStore } from '../../store'
import { fsList, fsRead, setWorkspace as apiSetWorkspace, getWorkspace } from '../../api'
import type { FileNode } from '../../types'

function fileIcon(node: FileNode): React.ReactNode {
  if (node.type === 'dir') {
    return <span style={{ color: '#e8a838', fontSize: 13 }}>▸</span>
  }
  const name = node.name.toLowerCase()
  const ext = name.split('.').pop() ?? ''
  
  // color-coded text badges
  const style = (color: string, text: string) => (
    <span style={{ fontSize: 9, fontWeight: 700, color, fontFamily: 'var(--font-mono)', lineHeight: 1 }}>{text}</span>
  )
  
  if (ext === 'ts' || ext === 'tsx') return style('#3178c6', 'TS')
  if (ext === 'js' || ext === 'jsx') return style('#f7df1e', 'JS')
  if (ext === 'py') return style('#3572A5', 'PY')
  if (ext === 'rs') return style('#dea584', 'RS')
  if (ext === 'go') return style('#00add8', 'GO')
  if (ext === 'json') return style('#fbbf24', '{ }')
  if (ext === 'yaml' || ext === 'yml') return style('#cb171e', 'YML')
  if (ext === 'toml') return style('#9c4221', 'TML')
  if (ext === 'md' || ext === 'mdx') return style('#083fa1', 'MD')
  if (ext === 'html') return style('#e34c26', 'HTM')
  if (ext === 'css' || ext === 'scss' || ext === 'less') return style('#563d7c', 'CSS')
  if (ext === 'sh' || ext === 'bash' || ext === 'ps1' || ext === 'bat') return style('#6b7280', '$_')
  if (ext === 'sql') return style('#e38c00', 'SQL')
  if (ext === 'svg' || ext === 'png' || ext === 'jpg' || ext === 'gif' || ext === 'webp') return style('#22c55e', 'IMG')
  if (name === 'dockerfile') return style('#2496ed', 'DOC')
  if (name.startsWith('.git') || name === '.gitignore') return style('#f05032', 'GIT')
  return style('#9d9d9d', '·')
}

interface NodeProps {
  node: FileNode
  depth: number
  onOpenFile: (node: FileNode) => void
  toggleDir: (path: string) => void
  activePath: string | null
}

function TreeNode({ node, depth, onOpenFile, toggleDir, activePath }: NodeProps) {
  const isDir = node.type === 'dir'
  const isActive = !isDir && activePath === node.path

  const handleClick = () => {
    if (isDir) toggleDir(node.path)
    else onOpenFile(node)
  }

  return (
    <>
      <div
        className={`tree-item${isDir ? ' tree-item--dir' : ''}${node.expanded ? ' tree-item--expanded' : ''}${isActive ? ' tree-item--active' : ''}`}
        style={{ paddingLeft: 8 + depth * 14 }}
        onClick={handleClick}
        title={node.path}
      >
        {isDir && (
          <span className="tree-item__chevron">▶</span>
        )}
        <span className="tree-item__icon" style={{ width: 18, flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
          {fileIcon(node)}
        </span>
        <span className="tree-item__name">{node.name}</span>
      </div>
      {isDir && node.expanded && node.children?.map(child => (
        <TreeNode
          key={child.path}
          node={child}
          depth={depth + 1}
          onOpenFile={onOpenFile}
          toggleDir={toggleDir}
          activePath={activePath}
        />
      ))}
    </>
  )
}

export default function Explorer() {
  const {
    workspace, workspaceTree, treeLoading,
    setWorkspaceTree, setTreeLoading, setWorkspace,
    openTabs, activeTabId, openTab,
  } = useStore()

  const activePath = openTabs.find(t => t.id === activeTabId)?.path ?? null

  const loadDir = useCallback(async (path: string = '.') => {
    setTreeLoading(true)
    try {
      const { children } = await fsList(path)
      return children.map((c): FileNode => ({
        name: c.name,
        path: c.path,
        type: c.type as 'file' | 'dir',
        children: c.type === 'dir' ? [] : undefined,
        expanded: false,
      }))
    } finally {
      setTreeLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!workspace) return
    loadDir('.').then(nodes => setWorkspaceTree(nodes))
  }, [workspace])

  const toggleDir = useCallback(async (path: string) => {
    const updateNode = (nodes: FileNode[]): FileNode[] =>
      nodes.map(n => {
        if (n.path === path) {
          if (!n.expanded && (!n.children || n.children.length === 0)) {
            fsList(n.path).then(({ children }) => {
              const mapped = children.map((c): FileNode => ({
                name: c.name,
                path: c.path,
                type: c.type as 'file' | 'dir',
                children: c.type === 'dir' ? [] : undefined,
                expanded: false,
              }))
              setWorkspaceTree(updateNodeChildren(useStore.getState().workspaceTree, path, mapped, true))
            })
          }
          return { ...n, expanded: !n.expanded }
        }
        if (n.children) return { ...n, children: updateNode(n.children) }
        return n
      })

    setWorkspaceTree(updateNode(useStore.getState().workspaceTree))
  }, [])

  const openFile = useCallback(async (node: FileNode) => {
    const existing = useStore.getState().openTabs.find(t => t.path === node.path)
    if (existing) {
      useStore.getState().setActiveTab(existing.id)
      return
    }
    try {
      const { content } = await fsRead(node.path)
      openTab(node.path, content)
    } catch (e) {
      openTab(node.path, '')
    }
  }, [openTab])

  const handleOpenFolder = useCallback(() => {
    const path = window.prompt('Enter folder path to open:', workspace || '~')
    if (!path) return
    apiSetWorkspace(path).then(() => {
      return getWorkspace()
    }).then(({ path: resolved }) => {
      setWorkspace(resolved)
    }).catch(e => alert(`Cannot open folder: ${e.message}`))
  }, [workspace, setWorkspace])

  const ws = workspace.split(/[\\/]/).pop() ?? workspace
  const isRootOrEmpty = !workspace || workspace === 'C:\\' || workspace === '/'

  return (
    <>
      <div className="sidebar__header">
        <span title={workspace}>{ws || 'Explorer'}</span>
        <div className="sidebar__header-actions">
          <button className="icon-btn" title="Open Folder" onClick={handleOpenFolder}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M2 4h5l1.5-1.5H14v9H2V4z" />
            </svg>
          </button>
          <button className="icon-btn" title="Refresh" onClick={() => loadDir('.').then(n => setWorkspaceTree(n))}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M13 8A5 5 0 013 8a5 5 0 015-5 5 5 0 013.5 1.5" />
              <polyline points="11.5 1 14.5 4.5 11 4.5" />
            </svg>
          </button>
        </div>
      </div>
      <div className="sidebar__body">
        {treeLoading && workspaceTree.length === 0 && (
          <div className="empty-state"><p>Loading…</p></div>
        )}
        {!treeLoading && (isRootOrEmpty || workspaceTree.length === 0) && (
          <div className="empty-state" style={{ padding: '24px 12px' }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>📂</div>
            <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-dim)' }}>No folder open</div>
            <p style={{ fontSize: 12, color: 'var(--text-faint)', marginBottom: 12 }}>
              Open a folder to browse files
            </p>
            <button className="btn btn--sm btn--primary" onClick={handleOpenFolder}>Open Folder</button>
          </div>
        )}
        {!isRootOrEmpty && workspaceTree.map(node => (
          <TreeNode
            key={node.path}
            node={node}
            depth={0}
            onOpenFile={openFile}
            toggleDir={toggleDir}
            activePath={activePath}
          />
        ))}
      </div>
    </>
  )
}

function updateNodeChildren(
  nodes: FileNode[],
  path: string,
  children: FileNode[],
  expanded: boolean,
): FileNode[] {
  return nodes.map(n => {
    if (n.path === path) return { ...n, children, expanded }
    if (n.children) return { ...n, children: updateNodeChildren(n.children, path, children, expanded) }
    return n
  })
}
