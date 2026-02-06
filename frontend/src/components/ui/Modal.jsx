import React from 'react'
import { Button } from './Button'

export function Modal({ open, title, children, onClose, footer }) {
  if (!open) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="card-head" style={{ marginBottom: 10 }}>
          <h3 className="card-title">{title}</h3>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </div>
        <div className="section-stack">{children}</div>
        {footer && <div style={{ marginTop: 14 }}>{footer}</div>}
      </div>
    </div>
  )
}
