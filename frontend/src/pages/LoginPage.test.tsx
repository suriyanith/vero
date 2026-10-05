import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, test, vi } from 'vitest'
import { LoginPage } from './LoginPage'

afterEach(() => vi.unstubAllGlobals())

function renderLogin() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

test('shows the synthetic-data notice', () => {
  vi.stubGlobal('fetch', vi.fn())
  renderLogin()
  expect(screen.getByText(/Synthetic data only/)).toBeInTheDocument()
})

test('failed login shows the server message', async () => {
  document.cookie = 'csrftoken=t'
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({
        error: { code: 'INVALID_CREDENTIALS', message: 'Wrong username or password.' },
      }),
    }),
  )
  renderLogin()
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Username'), 'coder')
  await user.type(screen.getByLabelText('Password'), 'bad')
  await user.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Wrong username or password.')
})
