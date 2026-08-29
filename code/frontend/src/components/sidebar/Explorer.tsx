import React, { useEffect, useCallback } from 'react'
import { useStore } from '../../store'
import { fsList, fsRead } from '../../api'
import type { FileNode } from '../../types'

function fileIcon(node: FileNode): string {
  if (node.type === 'dir') return '📁'
  const ext = node.name.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    ts: '🔷', tsx: '⚛️', js: '🟨', jsx: '⚛️',
    py: '🐍', rs: '🦀', go: '🐹',
    json: '📋', yaml: '📋', yml: '📋', toml: '📋',
    md: '📝', txt: '📄', html: '🌐', css: '🎨', scss: '🎨',
    svg: '🖼️', png: '🖼️', jpg: '🖼️', gif: '🖼️', webp: '🖼️',
    sh: '💲', ps1: '💲', bat: '💲',
    sql: '🗄️',
  }
  return map[ext] ?? '📄'
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
        <span className="tree-item__icon">{fileIcon(node)}</span>
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
    setWorkspaceTree, setTreeLoading,
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
            // load children
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

  const ws = workspace.split(/[\\/]/).pop() ?? workspace

  return (
    <>
      <div className="sidebar__header">
        <span title={workspace}>{ws || 'Explorer'}</span>
        <div className="sidebar__header-actions">
          <button className="icon-btn" title="Refresh" onClick={() => loadDir('.').then(n => setWorkspaceTree(n))}>↻</button>
        </div>
      </div>
      <div className="sidebar__body">
        {treeLoading && workspaceTree.length === 0 && (
          <div className="empty-state"><p>Loading…</p></div>
        )}
        {!treeLoading && workspaceTree.length === 0 && (
          <div className="empty-state"><p>No workspace open.</p></div>
        )}
        {workspaceTree.map(node => (
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
