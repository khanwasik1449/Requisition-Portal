import { useState } from 'react'
import { useAuth } from '@/auth/hooks'
import { api } from '@/api/axios'

export function Profile() {
  const { user } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'danger'; text: string } | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage(null)
    setIsLoading(true)
    try {
      await api.post('/auth/change-password/', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setMessage({ type: 'success', text: 'Password changed successfully.' })
      setCurrentPassword('')
      setNewPassword('')
    } catch (err: any) {
      setMessage({
        type: 'danger',
        text: err.response?.data?.detail || 'Failed to change password.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">My Profile</h2>
          <p className="text-muted mb-0 small">Manage your account settings</p>
        </div>
      </div>

      <div className="row g-4">
        <div className="col-md-4">
          <div className="card">
            <div className="card-header">
              <i className="bi bi-person-circle me-2" style={{ color: '#2563eb' }}></i>Account Info
            </div>
            <div className="card-body text-center py-4">
              <div
                className="mx-auto mb-3 d-flex align-items-center justify-content-center rounded-circle"
                style={{
                  width: '80px',
                  height: '80px',
                  background: '#eff6ff',
                  color: '#2563eb',
                  fontSize: '2rem',
                  fontWeight: 700,
                }}
              >
                {user?.username?.[0]?.toUpperCase()}
              </div>
              <h5 className="fw-bold mb-1">{user?.username}</h5>
              <p className="text-muted mb-1">{user?.email}</p>
              <span className="badge bg-primary">{user?.role_display || user?.role}</span>
            </div>
          </div>
        </div>

        <div className="col-md-8">
          <div className="card">
            <div className="card-header">
              <i className="bi bi-key me-2" style={{ color: '#2563eb' }}></i>Change Password
            </div>
            <div className="card-body">
              {message && (
                <div className={`alert alert-${message.type} py-2 small`}>{message.text}</div>
              )}
              <form onSubmit={handleChangePassword}>
                <div className="mb-3">
                  <label className="form-label">Current Password</label>
                  <input
                    type="password"
                    className="form-control"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    disabled={isLoading}
                  />
                </div>
                <div className="mb-4">
                  <label className="form-label">New Password</label>
                  <input
                    type="password"
                    className="form-control"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    disabled={isLoading}
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={isLoading}>
                  <i className="bi bi-check-lg me-1"></i>
                  {isLoading ? 'Saving...' : 'Change Password'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
