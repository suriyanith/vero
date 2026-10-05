import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useLogin } from '../features/auth/hooks'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()
  const navigate = useNavigate()

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-2xl font-bold">Vero</h1>
      <p className="mt-1 text-sm text-gray-600">Evidence-first medical coding assistant.</p>
      <p className="mt-3 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800">
        Synthetic data only. Never paste real patient notes into Vero.
      </p>
      <form
        className="mt-6 space-y-4"
        onSubmit={(e) => {
          e.preventDefault()
          login.mutate({ username, password }, { onSuccess: () => navigate('/queue') })
        }}
      >
        <label className="block text-sm">
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
          />
        </label>
        {login.isError && (
          <p role="alert" className="text-sm text-red-700">
            {login.error instanceof ApiError ? login.error.message : 'Login failed.'}
          </p>
        )}
        <button
          type="submit"
          disabled={login.isPending}
          className="w-full rounded bg-blue-600 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  )
}
