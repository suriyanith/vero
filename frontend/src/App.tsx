import { Link, Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { useLogout, useMe } from './features/auth/hooks'
import { LoginPage } from './pages/LoginPage'
import { NewRunPage } from './pages/NewRunPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { RunDetailPage } from './pages/RunDetailPage'
import { WorkQueuePage } from './pages/WorkQueuePage'

function Layout() {
  const { data: me, isPending, isError } = useMe()
  const logout = useLogout()

  if (isPending) {
    return <p className="p-8 text-gray-500">Loading…</p>
  }
  if (isError || !me) {
    return <Navigate to="/login" replace />
  }
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
          <Link to="/" className="text-lg font-bold">
            Vero
          </Link>
          <NavLink
            to="/new"
            className={({ isActive }) =>
              `text-sm ${
                isActive ? 'font-semibold text-blue-700' : 'text-gray-600 hover:text-gray-900'
              }`
            }
          >
            New run
          </NavLink>
          <NavLink
            to="/queue"
            className={({ isActive }) =>
              `text-sm ${
                isActive ? 'font-semibold text-blue-700' : 'text-gray-600 hover:text-gray-900'
              }`
            }
          >
            Work queue
          </NavLink>
          <span className="ml-auto text-sm text-gray-500">
            {me.display_name || me.username} ({me.role})
          </span>
          <button
            className="text-sm text-gray-600 underline hover:text-gray-900"
            onClick={() =>
              logout.mutate(undefined, { onSuccess: () => window.location.assign('/login') })
            }
          >
            Log out
          </button>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
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
        <Route path="/" element={<Navigate to="/queue" replace />} />
        <Route path="/new" element={<NewRunPage />} />
        <Route path="/queue" element={<WorkQueuePage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
