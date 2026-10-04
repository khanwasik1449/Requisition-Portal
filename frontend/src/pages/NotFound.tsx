import { Link } from 'react-router-dom'

// Exact replica of Django 404 page style
export function NotFound() {
  return (
    <div
      className="d-flex flex-column justify-content-center align-items-center text-center"
      style={{ minHeight: '60vh', padding: '40px 20px' }}
    >
      <div style={{ fontSize: '5rem', fontWeight: 700, color: '#e2e8f0', lineHeight: 1 }}>404</div>
      <h3 style={{ fontWeight: 700, color: '#0f172a' }}>Page Not Found</h3>
      <p className="text-muted mb-4">The page you are looking for doesn't exist or was moved.</p>
      <Link to="/dashboard" className="btn btn-primary">
        <i className="bi bi-house me-1"></i> Back to Dashboard
      </Link>
    </div>
  )
}
