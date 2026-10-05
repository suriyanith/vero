import { Link, Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { useLogout, useMe } from './features/auth/hooks'
import { AuditTrailPage } from './pages/AuditTrailPage'
import { DashboardPage } from './pages/DashboardPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { LoginPage } from './pages/LoginPage'
import { NewRunPage } from './pages/NewRunPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { RunDetailPage } from './pages/RunDetailPage'
import { WorkQueuePage } from './pages/WorkQueuePage'

function NavItem({ to, children }: { to: string; children: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-full px-3 py-1 text-sm transition-colors ${
          isActive ? 'bg-ink text-paper' : 'text-ink-soft hover:text-ink'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

function Layout() {
  const { data: me, isPending, isError } = useMe()
  const logout = useLogout()

  if (isPending) {
    return <p className="p-10 text-center text-ink-faint">Loading…</p>
  }
  if (isError || !me) {
    return <Navigate to="/login" replace />
  }
  const initial = (me.display_name || me.username).slice(0, 1).toUpperCase()
  return (
    <div className="min-h-screen pb-16">
      <header className="sticky top-0 z-40 px-4 pt-4">
        <nav className="mx-auto flex max-w-5xl items-center gap-1 rounded-full border border-line bg-surface/85 py-2 pl-5 pr-2 shadow-[0_2px_12px_rgba(28,25,23,0.06)] backdrop-blur-md">
          <Link to="/" className="mr-4 font-display text-xl font-bold tracking-tight">
            Vero
          </Link>
          <NavItem to="/dashboard">Dashboard</NavItem>
          <NavItem to="/new">New run</NavItem>
          <NavItem to="/queue">Work queue</NavItem>
          <NavItem to="/trail">Audit trail</NavItem>
          {me.role === 'admin' && <NavItem to="/evaluation">Evaluation</NavItem>}
          <span className="ml-auto flex items-center gap-2">
            <span
              className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent"
              title={`${me.display_name || me.username} (${me.role})`}
            >
              {initial}
            </span>
            <button
              className="rounded-full border border-line-strong px-3 py-1 text-sm text-ink-soft transition-colors hover:bg-stone-100 hover:text-ink"
              onClick={() =>
                logout.mutate(undefined, { onSuccess: () => window.location.assign('/login') })
              }
            >
              Sign out
            </button>
          </span>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-10">
        <Outlet />
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
