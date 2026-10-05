import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useCreateBatch, useCreateRun, useSamples } from '../features/runs/hooks'

type Tab = 'paste' | 'sample' | 'batch'
type Mode = 'coding' | 'audit'

const CODE_FORMAT = /^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$/

export function NewRunPage() {
  const [tab, setTab] = useState<Tab>('paste')
  const [mode, setMode] = useState<Mode>('coding')
  const [text, setText] = useState('')
  const [sampleId, setSampleId] = useState<string | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [submittedCodes, setSubmittedCodes] = useState<string[]>([])
  const [codeDraft, setCodeDraft] = useState('')
  const [error, setError] = useState<string | null>(null)

  const samples = useSamples()
  const createRun = useCreateRun()
  const createBatch = useCreateBatch()
  const navigate = useNavigate()

  const addCode = () => {
    const code = codeDraft.trim().toUpperCase()
    if (!code) return
    if (!CODE_FORMAT.test(code)) {
      setError(`${code} is not a valid ICD-10-CM code format.`)
      return
    }
    setError(null)
    if (!submittedCodes.includes(code)) setSubmittedCodes([...submittedCodes, code])
    setCodeDraft('')
  }

  const submitRun = (payload: { text?: string; sample_id?: string }) => {
    setError(null)
    if (mode === 'audit' && submittedCodes.length === 0) {
      setError('Audit mode needs at least one submitted code.')
      return
    }
    createRun.mutate(
      { ...payload, mode, submitted_codes: mode === 'audit' ? submittedCodes : [] },
      {
        onSuccess: (created) => navigate(`/runs/${created.run_id}`),
        onError: (e) => setError(e instanceof ApiError ? e.message : 'Something went wrong.'),
      },
    )
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

  const auditControls = tab !== 'batch' && (
    <fieldset className="mb-3">
      <legend className="sr-only">Run mode</legend>
      <div className="flex items-center gap-4 text-sm">
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="mode"
            checked={mode === 'coding'}
            onChange={() => setMode('coding')}
          />
          Coding
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="mode"
            checked={mode === 'audit'}
            onChange={() => setMode('audit')}
          />
          Audit submitted codes
        </label>
      </div>
      {mode === 'audit' && (
        <div className="mt-2">
          <label className="block text-sm">
            Submitted codes
            <span className="ml-1 text-xs text-gray-500">(press Enter to add)</span>
            <input
              value={codeDraft}
              onChange={(e) => setCodeDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  addCode()
                }
              }}
              placeholder="e.g. E11.9"
              className="mt-1 w-48 rounded border border-gray-300 px-2 py-1 font-mono text-sm focus:border-blue-500 focus:outline-none"
            />
          </label>
          {submittedCodes.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1">
              {submittedCodes.map((code) => (
                <li
                  key={code}
                  className="flex items-center gap-1 rounded-full bg-gray-200 px-2 py-0.5 font-mono text-xs"
                >
                  {code}
                  <button
                    aria-label={`Remove ${code}`}
                    className="text-gray-500 hover:text-gray-900"
                    onClick={() => setSubmittedCodes(submittedCodes.filter((c) => c !== code))}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </fieldset>
  )

  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-bold">New run</h1>
      <p className="mt-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800">
        Synthetic notes only — Vero rejects anything that looks like real patient identifiers.
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
            {auditControls}
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
              {createRun.isPending ? 'Submitting…' : mode === 'audit' ? 'Run audit' : 'Run coding'}
            </button>
          </div>
        )}

        {tab === 'sample' && (
          <div>
            {auditControls}
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
              {createRun.isPending ? 'Submitting…' : mode === 'audit' ? 'Run audit' : 'Run coding'}
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
