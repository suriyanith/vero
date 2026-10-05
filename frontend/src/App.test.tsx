import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import App from './App'

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  )
}

test('shows backend health when the API responds', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', database: true, code_set_loaded: false }),
    }),
  )
  renderApp()
  expect(await screen.findByTestId('health-status')).toHaveTextContent('ok — database connected')
})

test('shows an error when the API is unreachable', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')))
  renderApp()
  expect(await screen.findByText('API unreachable')).toBeInTheDocument()
})
