import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { api, ApiError } from './client'

function mockFetch(responses: Array<{ status: number; body?: unknown }>) {
  const calls: Array<{ url: string; init: RequestInit | undefined }> = []
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, init })
    const next = responses.shift() ?? { status: 200, body: {} }
    return {
      ok: next.status < 400,
      status: next.status,
      json: async () => next.body ?? {},
    } as Response
  })
  vi.stubGlobal('fetch', fn)
  return calls
}

beforeEach(() => {
  document.cookie = 'csrftoken=test-token'
})

afterEach(() => {
  vi.unstubAllGlobals()
})

test('GET returns parsed JSON without a CSRF header', async () => {
  const calls = mockFetch([{ status: 200, body: { ok: true } }])
  const result = await api<{ ok: boolean }>('/health')
  expect(result.ok).toBe(true)
  const headers = calls[0].init?.headers as Record<string, string>
  expect(headers['X-CSRFToken']).toBeUndefined()
})

test('POST sends the CSRF token and JSON body', async () => {
  const calls = mockFetch([{ status: 201, body: {} }])
  await api('/suggestions/1/decisions', { method: 'POST', json: { action: 'accept' } })
  const headers = calls[0].init?.headers as Record<string, string>
  expect(headers['X-CSRFToken']).toBe('test-token')
  expect(headers['Content-Type']).toBe('application/json')
  expect(calls[0].init?.body).toBe('{"action":"accept"}')
  expect(calls[0].url).toBe('/api/suggestions/1/decisions')
})

test('error responses throw ApiError with the shared shape', async () => {
  mockFetch([
    { status: 400, body: { error: { code: 'PHI_DETECTED', message: 'Synthetic notes only.' } } },
    { status: 500, body: {} },
  ])
  const failure = api('/runs', { method: 'POST', json: { text: 'x' } })
  await expect(failure).rejects.toMatchObject({
    status: 400,
    code: 'PHI_DETECTED',
    message: 'Synthetic notes only.',
  })
  await expect(api('/runs')).rejects.toBeInstanceOf(ApiError)
})

test('401 redirects to the login page', async () => {
  mockFetch([{ status: 401, body: {} }])
  const assign = vi.fn()
  vi.stubGlobal('location', { ...window.location, pathname: '/queue', assign })
  await expect(api('/runs')).rejects.toMatchObject({ status: 401 })
  expect(assign).toHaveBeenCalledWith('/login')
})
