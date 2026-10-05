import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { CodeHit } from '../api/types'

// Search the real code set and pick a billable replacement code.
export function CodeSearchModal({
  title,
  onSelect,
  onClose,
}: {
  title: string
  onSelect: (code: CodeHit) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    const timer = setTimeout(() => setDebounced(query), 250)
    return () => clearTimeout(timer)
  }, [query])

  const { data: results, isFetching } = useQuery({
    queryKey: ['code-search', debounced],
    queryFn: () => api<CodeHit[]>(`/codes/search?q=${encodeURIComponent(debounced)}&limit=15`),
    enabled: debounced.trim().length >= 2,
  })

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-8"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div
        className="w-full max-w-2xl rounded-lg bg-white p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">{title}</h2>
          <button
            className="text-gray-500 hover:text-gray-900"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <label className="block">
          <span className="sr-only">Search codes</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by description or code, e.g. “type 2 diabetes CKD”"
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </label>
        <ul className="mt-3 max-h-80 divide-y divide-gray-100 overflow-y-auto">
          {isFetching && <li className="p-2 text-sm text-gray-500">Searching…</li>}
          {results?.map((hit) => (
            <li key={hit.display_code}>
              <button
                className="flex w-full items-baseline gap-3 p-2 text-left text-sm hover:bg-blue-50"
                onClick={() => onSelect(hit)}
              >
                <span className="font-mono font-semibold">{hit.display_code}</span>
                <span className="flex-1 text-gray-700">{hit.description}</span>
                {hit.hcc_number != null && (
                  <span className="text-xs text-purple-700">HCC {hit.hcc_number}</span>
                )}
              </button>
            </li>
          ))}
          {results && results.length === 0 && (
            <li className="p-2 text-sm text-gray-500">No billable codes match.</li>
          )}
        </ul>
      </div>
    </div>
  )
}
