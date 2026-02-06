import React from 'react'

export function Toggle({ checked, onChange, disabled = false }) {
  return (
    <button
      type="button"
      className={`toggle ${checked ? 'on' : ''}`}
      onClick={() => onChange(!checked)}
      disabled={disabled}
      aria-pressed={checked}
    />
  )
}
