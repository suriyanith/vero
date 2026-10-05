import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">Page not found</h1>
      <p className="mt-2 text-gray-600">
        Nothing lives here.{' '}
        <Link to="/queue" className="text-blue-700 underline">
          Back to the work queue
        </Link>
      </p>
    </div>
  )
}
