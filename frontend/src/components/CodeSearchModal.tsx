import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { CodeHit } from '../api/types'
import { Dialog, SearchInput } from './ui'

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
    <Dialog label={title} onClose={onClose} wide>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-lg font-semibold tracking-tight">{title}</h2>
        <button
          className="flex h-7 w-7 items-center justify-center rounded-full text-ink-faint hover:bg-stone-100 hover:text-ink"
          onClick={onClose}
          aria-label="Close"
        >
          ✕
        </button>
      </div>
      <label className="block">
        <span className="sr-only">Search codes</span>
        <SearchInput
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by description or code, e.g. “type 2 diabetes CKD”"
        />
      </label>
      <ul className="mt-3 max-h-80 divide-y divide-line overflow-y-auto">
        {isFetching && <li className="p-3 text-sm text-ink-faint">Searching…</li>}
        {results?.map((hit) => (
          <li key={hit.display_code}>
            <button
              className="flex w-full items-baseline gap-3 rounded-lg p-3 text-left text-sm transition-colors hover:bg-accent-soft/40"
              onClick={() => onSelect(hit)}
            >
              <span className="font-mono font-semibold">{hit.display_code}</span>
              <span className="flex-1 text-stone-700">{hit.description}</span>
              {hit.hcc_number != null && (
                <span className="text-xs font-medium text-accent">HCC {hit.hcc_number}</span>
              )}
            </button>
          </li>
        ))}
        {results && results.length === 0 && (
          <li className="p-3 text-sm text-ink-faint">No billable codes match.</li>
        )}
      </ul>
    </Dialog>
  )
}
