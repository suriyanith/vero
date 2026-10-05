import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="py-24 text-center">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-3 text-sm text-ink-soft">
        Nothing lives here.{' '}
        <Link to="/dashboard" className="font-medium text-accent hover:underline">
          Back to the dashboard
        </Link>
      </p>
    </div>
  )
}
