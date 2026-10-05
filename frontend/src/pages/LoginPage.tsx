import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { Button, Card, inputClass } from '../components/ui'
import { useLogin } from '../features/auth/hooks'

// A miniature of the real product: a suggestion card with its evidence, and
// an audit verdict floating behind it. Pure decoration — hidden from AT.
function EvidenceMock() {
  return (
    <div aria-hidden className="relative mt-12 select-none">
      <div className="anim-drift-slow absolute -top-8 right-0 w-52 rotate-2 rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold text-paper">N18.31</span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#2e8b4a]/25 px-2 py-0.5 text-[11px] font-medium text-[#8fd6a4]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5fbf7d]" />
            SUPPORTED
          </span>
        </div>
        <p className="mt-2 text-xs leading-5 text-paper/60">Chronic kidney disease, stage 3a</p>
      </div>

      <div className="anim-drift relative w-[21rem] max-w-full -rotate-1 rounded-2xl bg-surface p-5 text-ink shadow-[0_30px_70px_-20px_rgba(0,0,0,0.55)]">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-lg font-bold tracking-tight">E11.22</span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#e3f1e5] px-2.5 py-0.5 text-xs font-medium text-[#1b5e2f]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#2e8b4a]" />
            high confidence
          </span>
          <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-xs font-medium text-accent">
            HCC 37
          </span>
        </div>
        <p className="mt-1.5 text-sm text-stone-700">
          Type 2 diabetes mellitus with diabetic chronic kidney disease
        </p>
        <p className="mt-3 border-l-2 border-line-strong pl-3 font-display text-[13px] italic leading-6 text-ink-soft">
          “
          <mark className="rounded-[3px] bg-[#fdeeb8] px-0.5 py-px not-italic">
            Type 2 diabetes with CKD stage 3a — continue metformin
          </mark>
          ”
        </p>
      </div>
    </div>
  )
}

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()
  const navigate = useNavigate()

  return (
    <main className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* Brand panel */}
      <section className="relative m-3 hidden flex-col justify-between overflow-hidden rounded-[2rem] bg-ink p-10 text-paper lg:flex xl:p-14">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -left-24 top-1/4 h-96 w-96 rounded-full bg-[#5247c7] opacity-35 blur-3xl" />
          <div className="absolute -bottom-32 right-0 h-[28rem] w-[28rem] rounded-full bg-[#c77b3f] opacity-25 blur-3xl" />
          <div className="absolute right-16 top-10 h-56 w-56 rounded-full bg-[#b4518a] opacity-20 blur-3xl" />
        </div>

        <div className="anim-in relative">
          <span className="font-display text-2xl font-bold tracking-tight">Vero</span>
        </div>

        <div className="anim-in relative" style={{ animationDelay: '80ms' }}>
          <h1 className="max-w-md font-display text-4xl font-medium leading-[1.15] tracking-tight xl:text-[2.9rem]">
            Every code, backed by <em className="font-light">the exact sentence</em> that supports
            it.
          </h1>
          <EvidenceMock />
        </div>

        <p
          className="anim-in relative max-w-sm text-[13px] leading-5 text-paper/50"
          style={{ animationDelay: '160ms' }}
        >
          Quotes are verified in code, every decision is a human's, and the audit trail is
          append-only.
        </p>
      </section>

      {/* Form side */}
      <section className="relative flex items-center justify-center overflow-hidden p-6">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 lg:hidden"
          style={{
            background:
              'radial-gradient(42rem 22rem at 50% -10%, #ddd8f5 0%, rgba(221,216,245,0) 60%)',
          }}
        />
        <div className="anim-in relative w-full max-w-sm" style={{ animationDelay: '120ms' }}>
          <div className="mb-10 text-center lg:hidden">
            <h1 className="font-display text-5xl font-bold tracking-tight">Vero</h1>
            <p className="mx-auto mt-3 max-w-xs text-sm leading-6 text-ink-soft">
              Every code, backed by the exact sentence that supports it.
            </p>
          </div>

          <div className="hidden lg:block">
            <h2 className="font-display text-3xl font-semibold tracking-tight">Welcome back</h2>
            <p className="mt-1.5 text-sm text-ink-soft">Sign in to review today's queue.</p>
          </div>

          <Card className="mt-0 p-6 sm:p-7 lg:mt-7">
            <form
              className="space-y-5"
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
                  autoFocus
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
                className="w-full py-2.5 text-[15px]"
              >
                {login.isPending ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>
          </Card>

          <p className="mt-7 text-center text-xs leading-5 text-ink-faint">
            Synthetic data only. Never paste real patient notes into Vero.
          </p>
        </div>
      </section>
    </main>
  )
}
