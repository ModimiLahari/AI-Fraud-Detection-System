import React from 'react'
import { X } from 'lucide-react'

export default function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-base-950/70 backdrop-blur-sm" onClick={onClose} />
      <div className="panel relative w-full max-w-lg p-6 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-display text-base font-semibold text-ink-100">{title}</h3>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-100 p-1 rounded-lg hover:bg-base-700">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
