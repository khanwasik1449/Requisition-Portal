import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/hooks'

// Exact replica of templates/accounts/login.html
export function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        padding: '20px',
      }}
    >
      <div
        style={{
          border: 'none',
          borderRadius: '20px',
          boxShadow: '0 25px 60px rgba(0,0,0,.3)',
          padding: '40px',
          width: '420px',
          maxWidth: '100%',
          background: '#fff',
        }}
      >
        <div className="text-center mb-4">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <img
              src="http://bracied.com/wp-content/uploads/2025/10/BRAC-IED-Color_PNG.png"
              alt="BRAC IED"
              style={{ height: 'auto', maxHeight: '56px', width: 'auto' }}
            />
          </div>
          <h3 style={{ fontWeight: 700, color: '#0f172a' }}>Welcome Back</h3>
          <p className="text-muted small">Sign in to your account</p>
        </div>

        {error && (
          <div className="alert alert-danger py-2 small">
            <i className="bi bi-exclamation-circle me-1"></i> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label" style={{ fontWeight: 600, fontSize: '.8rem', color: '#0f172a' }}>
              Username
            </label>
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0 rounded-start-2">
                <i className="bi bi-person"></i>
              </span>
              <input
                type="text"
                name="username"
                className="form-control border-start-0"
                placeholder="Enter your username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
                style={{
                  borderRadius: '10px',
                  border: '1.5px solid #e2e8f0',
                  padding: '12px 14px',
                  fontSize: '.875rem',
                }}
              />
            </div>
          </div>
          <div className="mb-4">
            <label className="form-label" style={{ fontWeight: 600, fontSize: '.8rem', color: '#0f172a' }}>
              Password
            </label>
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0 rounded-start-2">
                <i className="bi bi-lock"></i>
              </span>
              <input
                type="password"
                name="password"
                className="form-control border-start-0"
                placeholder="Enter your password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                style={{
                  borderRadius: '10px',
                  border: '1.5px solid #e2e8f0',
                  padding: '12px 14px',
                  fontSize: '.875rem',
                }}
              />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-primary w-100"
            disabled={isLoading}
            style={{
              background: '#2563eb',
              border: 'none',
              padding: '12px',
              borderRadius: '10px',
              fontWeight: 600,
            }}
          >
            <i className="bi bi-box-arrow-in-right me-1"></i>{' '}
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={{ borderTop: '1px solid #e2e8f0', margin: '24px 0' }} />
        <p className="text-center mb-0 text-muted small">
          BRAC Institute of Educational Development
        </p>
      </div>
    </div>
  )
}
