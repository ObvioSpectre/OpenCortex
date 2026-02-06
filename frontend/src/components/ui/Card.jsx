import React from 'react'

export function Card({ title, subtitle, right, children }) {
  return (
    <section className="card">
      {(title || subtitle || right) && (
        <div className="card-head">
          <div>
            {title && <h3 className="card-title">{title}</h3>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  )
}
