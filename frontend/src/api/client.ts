// One typed fetch wrapper for the whole app: CSRF, the shared error shape,
// and redirect-to-login on 401. No component calls fetch directly.

export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

let csrfFetched = false

async function csrfToken(): Promise<string> {
  if (!readCookie('csrftoken') && !csrfFetched) {
    csrfFetched = true
    await fetch('/api/auth/csrf', { credentials: 'same-origin' })
  }
  return readCookie('csrftoken') ?? ''
}

export function redirectToLogin(): void {
  if (!window.location.pathname.startsWith('/login')) {
    window.location.assign('/login')
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  json?: unknown
  form?: FormData
  // 401 normally redirects to login; auth probes opt out.
  allowUnauthorized?: boolean
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = {}
  let body: BodyInit | undefined

  if (method !== 'GET') {
    headers['X-CSRFToken'] = await csrfToken()
  }
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  } else if (options.form) {
    body = options.form
  }

  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body,
    credentials: 'same-origin',
  })

  if (response.status === 401 && !options.allowUnauthorized) {
    redirectToLogin()
    throw new ApiError(401, 'UNAUTHORIZED', 'You need to log in.')
  }
  if (!response.ok) {
    let code = 'UNKNOWN'
    let message = `Request failed (${response.status})`
    try {
      const data = (await response.json()) as { error?: { code?: string; message?: string } }
      code = data.error?.code ?? code
      message = data.error?.message ?? message
    } catch {
      // non-JSON error body; keep the fallback message
    }
    throw new ApiError(response.status, code, message)
  }
  return response.json() as Promise<T>
}
