import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { Button, Card, inputClass } from '../components/ui'
import { useLogin } from '../features/auth/hooks'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()
  const navigate = useNavigate()

  return (
    <main
      className="flex min-h-screen items-center justify-center p-6"
      style={{
        background:
          'radial-gradient(80rem 40rem at 50% -10%, #ece7f8 0%, rgba(236,231,248,0) 55%), var(--color-paper)',
      }}
    >
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="font-display text-5xl font-bold tracking-tight">Vero</h1>
          <p className="mt-2 text-sm text-ink-soft">
            Every code, backed by the exact sentence that supports it.
          </p>
        </div>
        <Card className="p-6">
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              login.mutate({ username, password }, { onSuccess: () => navigate('/dashboard') })
            }}
          >
            <label className="block text-sm font-medium">
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                className={`mt-1.5 w-full ${inputClass}`}
              />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className={`mt-1.5 w-full ${inputClass}`}
              />
            </label>
            {login.isError && (
              <p role="alert" className="text-sm text-[#9a2c21]">
                {login.error instanceof ApiError ? login.error.message : 'Login failed.'}
              </p>
            )}
            <Button
              type="submit"
              variant="primary"
              disabled={login.isPending}
              className="w-full py-2.5"
            >
              {login.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </Card>
        <p className="mt-6 text-center text-xs leading-5 text-ink-faint">
          Synthetic data only. Never paste real patient notes into Vero.
        </p>
      </div>
    </main>
  )
}
