import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { Button, Card, MicroLabel, PageTitle, Segmented, inputClass } from '../components/ui'
import { useCreateBatch, useCreateRun, useSamples } from '../features/runs/hooks'

type Tab = 'paste' | 'sample' | 'batch'
type Mode = 'coding' | 'audit'

const CODE_FORMAT = /^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$/

const TABS: { id: Tab; label: string }[] = [
  { id: 'paste', label: 'Paste a note' },
  { id: 'sample', label: 'Pick a sample' },
  { id: 'batch', label: 'Upload a batch' },
]

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

  const submitLabel = createRun.isPending
    ? 'Submitting…'
    : mode === 'audit'
      ? 'Run audit'
      : 'Run coding'

  const auditControls = tab !== 'batch' && (
    <fieldset className="mb-5">
      <legend className="sr-only">Run mode</legend>
      <Segmented<Mode>
        options={[
          { id: 'coding', label: 'Coding' },
          { id: 'audit', label: 'Audit submitted codes' },
        ]}
        value={mode}
        onChange={setMode}
      />
      {mode === 'audit' && (
        <div className="mt-4">
          <label className="block text-sm font-medium">
            Submitted codes
            <span className="ml-1.5 font-normal text-ink-faint">press Enter to add</span>
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
              className={`mt-1.5 block w-44 font-mono ${inputClass}`}
            />
          </label>
          {submittedCodes.length > 0 && (
            <ul className="mt-2.5 flex flex-wrap gap-1.5">
              {submittedCodes.map((code) => (
                <li
                  key={code}
                  className="flex items-center gap-1.5 rounded-full bg-stone-200/70 py-1 pl-3 pr-2 font-mono text-xs font-medium"
                >
                  {code}
                  <button
                    aria-label={`Remove ${code}`}
                    className="flex h-4 w-4 items-center justify-center rounded-full text-ink-faint hover:bg-stone-300 hover:text-ink"
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
      <PageTitle title="New run" />
      <p className="mt-2 text-sm text-ink-soft">
        Synthetic notes only — Vero rejects anything that looks like real patient identifiers.
      </p>

      <div className="mt-6">
        <Segmented<Tab> options={TABS} value={tab} onChange={setTab} />
      </div>

      <Card className="mt-4 p-4 sm:p-6">
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
                className={`mt-1.5 w-full font-mono text-[13px] leading-6 ${inputClass}`}
              />
            </label>
            <Button
              variant="primary"
              className="mt-4"
              disabled={!text.trim() || createRun.isPending}
              onClick={() => submitRun({ text })}
            >
              {submitLabel}
            </Button>
          </div>
        )}

        {tab === 'sample' && (
          <div>
            {auditControls}
            {samples.isPending && <p className="text-sm text-ink-faint">Loading samples…</p>}
            {samples.isError && <p className="text-sm text-[#9a2c21]">Could not load samples.</p>}
            {samples.data?.length === 0 && (
              <p className="text-sm text-ink-faint">No samples loaded. Run `make init`.</p>
            )}
            <ul className="grid gap-2 sm:grid-cols-2">
              {samples.data?.map((sample) => (
                <li key={sample.id}>
                  <label
                    className={`block h-full cursor-pointer rounded-xl border p-3 transition-colors ${
                      sampleId === sample.id
                        ? 'border-accent bg-accent-soft/40'
                        : 'border-line hover:border-line-strong hover:bg-stone-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="sample"
                      checked={sampleId === sample.id}
                      onChange={() => setSampleId(sample.id)}
                      className="sr-only"
                    />
                    <span className="block text-sm font-medium">{sample.title}</span>
                    <span className="mt-1 line-clamp-2 block text-xs leading-5 text-ink-faint">
                      {sample.preview}…
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <Button
              variant="primary"
              className="mt-4"
              disabled={!sampleId || createRun.isPending}
              onClick={() => sampleId && submitRun({ sample_id: sampleId })}
            >
              {submitLabel}
            </Button>
          </div>
        )}

        {tab === 'batch' && (
          <div>
            <MicroLabel>Up to 25 .txt files · coding mode</MicroLabel>
            <label className="mt-2 block cursor-pointer rounded-xl border border-dashed border-line-strong p-8 text-center transition-colors hover:border-accent hover:bg-accent-soft/20">
              <input
                type="file"
                multiple
                accept=".txt"
                onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                className="sr-only"
              />
              <span className="block text-sm font-medium">
                {files.length > 0 ? `${files.length} file(s) selected` : 'Choose .txt files'}
              </span>
              <span className="mt-1 block text-xs text-ink-faint">
                Each file becomes its own note and run.
              </span>
            </label>
            <Button
              variant="primary"
              className="mt-4"
              disabled={files.length === 0 || createBatch.isPending}
              onClick={submitBatch}
            >
              {createBatch.isPending ? 'Uploading…' : `Submit ${files.length || ''} note(s)`}
            </Button>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-4 text-sm text-[#9a2c21]">
            {error}
          </p>
        )}
      </Card>
    </div>
  )
}
