import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useCreateBatch, useCreateRun, useSamples } from '../features/runs/hooks'

type Tab = 'paste' | 'sample' | 'batch'

export function NewRunPage() {
  const [tab, setTab] = useState<Tab>('paste')
  const [text, setText] = useState('')
  const [sampleId, setSampleId] = useState<string | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState<string | null>(null)

  const samples = useSamples()
  const createRun = useCreateRun()
  const createBatch = useCreateBatch()
  const navigate = useNavigate()

  const submitRun = (payload: { text?: string; sample_id?: string }) => {
    setError(null)
    createRun.mutate(payload, {
      onSuccess: (created) => navigate(`/runs/${created.run_id}`),
      onError: (e) => setError(e instanceof ApiError ? e.message : 'Something went wrong.'),
    })
  }

  const submitBatch = () => {
    setError(null)
    createBatch.mutate(files, {
      onSuccess: (created) => {
        if (created.rejected.length > 0) {
          setError(
            `Submitted ${created.run_ids.length} note(s). Rejected: ` +
              created.rejected.map((r) => `${r.filename} (${r.reason})`).join('; '),
          )
        } else {
          navigate('/queue')
        }
      },
      onError: (e) => setError(e instanceof ApiError ? e.message : 'Something went wrong.'),
    })
  }

  const tabClass = (t: Tab) =>
    `rounded-t px-4 py-2 text-sm font-medium ${
      tab === t
        ? 'bg-white border border-b-white border-gray-200 text-blue-700'
        : 'text-gray-600 hover:text-gray-900'
    }`

  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-bold">New coding run</h1>
      <p className="mt-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800">
        Synthetic notes only — Vero rejects anything that looks like real patient identifiers. Audit
        mode arrives in a later phase.
      </p>

      <div className="mt-4 flex gap-1 border-b border-gray-200" role="tablist">
        <button
          role="tab"
          aria-selected={tab === 'paste'}
          className={tabClass('paste')}
          onClick={() => setTab('paste')}
        >
          Paste a note
        </button>
        <button
          role="tab"
          aria-selected={tab === 'sample'}
          className={tabClass('sample')}
          onClick={() => setTab('sample')}
        >
          Pick a sample
        </button>
        <button
          role="tab"
          aria-selected={tab === 'batch'}
          className={tabClass('batch')}
          onClick={() => setTab('batch')}
        >
          Upload a batch
        </button>
      </div>

      <div className="rounded-b border border-t-0 border-gray-200 bg-white p-4">
        {tab === 'paste' && (
          <div>
            <label className="block text-sm font-medium">
              Clinical note
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={14}
                placeholder="Paste a synthetic outpatient note…"
                className="mt-1 w-full rounded border border-gray-300 p-3 font-mono text-sm focus:border-blue-500 focus:outline-none"
              />
            </label>
            <button
              className="mt-3 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              disabled={!text.trim() || createRun.isPending}
              onClick={() => submitRun({ text })}
            >
              {createRun.isPending ? 'Submitting…' : 'Run coding'}
            </button>
          </div>
        )}

        {tab === 'sample' && (
          <div>
            {samples.isPending && <p className="text-sm text-gray-500">Loading samples…</p>}
            {samples.isError && <p className="text-sm text-red-700">Could not load samples.</p>}
            {samples.data?.length === 0 && (
              <p className="text-sm text-gray-500">No samples loaded. Run `make init`.</p>
            )}
            <ul className="space-y-2">
              {samples.data?.map((sample) => (
                <li key={sample.id}>
                  <label className="flex cursor-pointer items-start gap-2 rounded border border-gray-200 p-2 hover:bg-blue-50">
                    <input
                      type="radio"
                      name="sample"
                      checked={sampleId === sample.id}
                      onChange={() => setSampleId(sample.id)}
                      className="mt-1"
                    />
                    <span>
                      <span className="block text-sm font-medium">{sample.title}</span>
                      <span className="block text-xs text-gray-500">{sample.preview}…</span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <button
              className="mt-3 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              disabled={!sampleId || createRun.isPending}
              onClick={() => sampleId && submitRun({ sample_id: sampleId })}
            >
              {createRun.isPending ? 'Submitting…' : 'Run coding'}
            </button>
          </div>
        )}

        {tab === 'batch' && (
          <div>
            <label className="block text-sm font-medium">
              Up to 25 .txt files
              <input
                type="file"
                multiple
                accept=".txt"
                onChange={(e) => setFiles([...(e.target.files ?? [])])}
                className="mt-2 block text-sm"
              />
            </label>
            {files.length > 0 && (
              <p className="mt-2 text-xs text-gray-500">{files.length} file(s) selected</p>
            )}
            <button
              className="mt-3 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              disabled={files.length === 0 || createBatch.isPending}
              onClick={submitBatch}
            >
              {createBatch.isPending ? 'Uploading…' : `Submit ${files.length || ''} note(s)`}
            </button>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
