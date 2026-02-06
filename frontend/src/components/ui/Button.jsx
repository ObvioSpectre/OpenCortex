import React from 'react'

export function Button({ variant = 'primary', className = '', ...props }) {
  return <button className={`btn btn-${variant} ${className}`.trim()} {...props} />
}
