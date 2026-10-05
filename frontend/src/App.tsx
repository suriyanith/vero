import { useQuery } from '@tanstack/react-query'

interface HealthResponse {
  status: string
  database: boolean
  code_set_loaded: boolean
}

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error(`API returned ${response.status}`)
  return response.json() as Promise<HealthResponse>
}

export default function App() {
  const { data, isPending, isError } = useQuery({ queryKey: ['health'], queryFn: fetchHealth })

  return (
    <main className="mx-auto max-w-xl p-8 font-sans">
      <h1 className="text-3xl font-bold">Vero</h1>
      <p className="mt-2 text-gray-600">
        Evidence-first medical coding assistant. Synthetic data only — never paste real patient
        notes.
      </p>
      <section className="mt-6 rounded border border-gray-200 p-4">
        <h2 className="font-semibold">Backend status</h2>
        {isPending && <p className="mt-1 text-gray-500">Checking…</p>}
        {isError && <p className="mt-1 text-red-700">API unreachable</p>}
        {data && (
          <p className="mt-1 text-green-700" data-testid="health-status">
            {data.status} — database {data.database ? 'connected' : 'down'}
          </p>
        )}
      </section>
    </main>
  )
}
