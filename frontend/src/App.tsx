import { useState } from 'react'
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useLogout, useMe } from './features/auth/hooks'
import { AuditTrailPage } from './pages/AuditTrailPage'
import { DashboardPage } from './pages/DashboardPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { LoginPage } from './pages/LoginPage'
import { NewRunPage } from './pages/NewRunPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { RunDetailPage } from './pages/RunDetailPage'
import { WorkQueuePage } from './pages/WorkQueuePage'

function navItemClass(isActive: boolean) {
  return `rounded-full px-3.5 py-1.5 text-sm font-medium transition-all duration-150 ${
    isActive ? 'bg-ink text-paper shadow-sm' : 'text-ink-soft hover:bg-stone-200/60 hover:text-ink'
  }`
}

function Layout() {
  const { data: me, isPending, isError } = useMe()
  const logout = useLogout()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  if (isPending) {
    return <p className="p-10 text-center text-ink-faint">Loading…</p>
  }
  if (isError || !me) {
    return <Navigate to="/login" replace />
  }

  const links = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/new', label: 'New run' },
    { to: '/queue', label: 'Work queue' },
    { to: '/trail', label: 'Audit trail' },
    ...(me.role === 'admin' ? [{ to: '/evaluation', label: 'Evaluation' }] : []),
  ]
  const initial = (me.display_name || me.username).slice(0, 1).toUpperCase()

  return (
    <div className="min-h-screen pb-20">
      <header className="sticky top-0 z-40 px-3 pt-3 sm:px-4 sm:pt-4">
        <nav className="mx-auto max-w-5xl rounded-[1.75rem] border border-line bg-surface/85 shadow-[0_2px_16px_rgba(28,25,23,0.07)] backdrop-blur-md">
          <div className="flex items-center gap-1 py-2 pl-5 pr-2">
            <Link
              to="/"
              className="mr-4 font-display text-[1.45rem] font-bold tracking-tight"
              onClick={() => setMenuOpen(false)}
            >
              Vero
            </Link>
            <div className="hidden items-center gap-1 md:flex">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) => navItemClass(isActive)}
                >
                  {link.label}
                </NavLink>
              ))}
            </div>
            <span className="ml-auto flex items-center gap-2">
              <span
                className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent"
                title={`${me.display_name || me.username} (${me.role})`}
              >
                {initial}
              </span>
              <button
                className="hidden rounded-full border border-line-strong px-3.5 py-1.5 text-sm font-medium text-ink-soft transition-colors hover:bg-stone-100 hover:text-ink md:block"
                onClick={() =>
                  logout.mutate(undefined, { onSuccess: () => window.location.assign('/login') })
                }
              >
                Sign out
              </button>
              <button
                className="flex h-8 w-8 flex-col items-center justify-center gap-[5px] rounded-full md:hidden"
                aria-label="Menu"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((v) => !v)}
              >
                <span
                  className={`h-[1.5px] w-4 bg-ink transition-transform ${
                    menuOpen ? 'translate-y-[3.5px] rotate-45' : ''
                  }`}
                />
                <span
                  className={`h-[1.5px] w-4 bg-ink transition-transform ${
                    menuOpen ? '-translate-y-[3px] -rotate-45' : ''
                  }`}
                />
              </button>
            </span>
          </div>
          {menuOpen && (
            <div className="anim-pop border-t border-line px-3 py-3 md:hidden">
              <div className="flex flex-col gap-1">
                {links.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      `rounded-xl px-3 py-2 text-sm font-medium ${
                        isActive ? 'bg-ink text-paper' : 'text-ink-soft hover:bg-stone-100'
                      }`
                    }
                  >
                    {link.label}
                  </NavLink>
                ))}
                <button
                  className="mt-1 rounded-xl border border-line-strong px-3 py-2 text-left text-sm font-medium text-ink-soft"
                  onClick={() =>
                    logout.mutate(undefined, { onSuccess: () => window.location.assign('/login') })
                  }
                >
                  Sign out
                </button>
              </div>
            </div>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-5 sm:py-10">
        <div key={location.pathname} className="anim-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/new" element={<NewRunPage />} />
        <Route path="/queue" element={<WorkQueuePage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/trail" element={<AuditTrailPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
