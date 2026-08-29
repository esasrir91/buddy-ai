import React from 'react'
import type { Todo } from '../../types'

interface Props {
  todos: Todo[]
}

const statusIcons: Record<string, string> = {
  pending: '○',
  in_progress: '◎',
  completed: '✓',
  cancelled: '✕',
}

const statusColors: Record<string, string> = {
  pending: 'var(--text-faint)',
  in_progress: 'var(--accent-2)',
  completed: 'var(--ok)',
  cancelled: 'var(--err)',
}

export default function TodoList({ todos }: Props) {
  return (
    <div className="todo-list">
      {todos.map(todo => (
        <div
          key={todo.id}
          className={`todo-item todo-item--${todo.status}`}
        >
          <div
            className={`todo-item__status todo-status--${todo.status}`}
            style={{ background: ['in_progress', 'completed', 'cancelled'].includes(todo.status) ? statusColors[todo.status] : undefined }}
            title={todo.status}
          />
          <span style={{ flex: 1 }}>
            {typeof todo.content === 'string' ? todo.content : (todo.content as any)?.[0]?.text ?? String(todo.content)}
          </span>
        </div>
      ))}
    </div>
  )
}
