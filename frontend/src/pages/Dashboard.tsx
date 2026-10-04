import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/hooks'
import { api } from '@/api/axios'

interface DashboardStats {
  transport?: { total: number; pending: number }
  meetspace?: { total: number; pending: number }
  ict?: { total: number; pending: number }
  internal?: { total: number; pending: number }
  pending_users?: number
  my_requests?: {
    transport: number
    ict: number
    internal: number
    bookings: number
  }
}

// Exact replica of templates/admin_dashboard.html
export function Dashboard() {
  const { user } = useAuth()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      const response = await api.get<DashboardStats>('/dashboard/stats/')
      return response.data
    },
    enabled: !!user,
  })

  if (isLoading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  const isAdmin = user?.role === 'admin'
  const isRequester = user?.role === 'requester'
  const pendingUsers = stats?.pending_users || 0

  return (
    <>
      {/* Pending Users Alert */}
      {isAdmin && pendingUsers > 0 && (
        <div
          className="alert alert-warning d-flex align-items-center justify-content-between py-3 px-4 mb-4"
          style={{ borderRadius: '12px', borderLeft: '5px solid #d97706' }}
        >
          <div>
            <i className="bi bi-people-fill me-2 fs-5"></i>
            <strong>{pendingUsers}</strong> user{pendingUsers > 1 ? 's' : ''} pending approval.
            <span className="text-muted ms-2">New users are waiting for you to activate their accounts.</span>
          </div>
          <Link to="/admin/users" className="btn btn-warning btn-sm">
            <i className="bi bi-arrow-right me-1"></i> Review
          </Link>
        </div>
      )}

      {/* Requisition Stats */}
      <div className="row g-4 mb-4">
        {(isAdmin || user?.role === 'ict_admin' || isRequester) && (
          <div className="col-md-4">
            <div className="stat-card">
              <div className="stat-icon" style={{ background: '#eff6ff', color: '#2563eb' }}>
                <i className="bi bi-pc-display"></i>
              </div>
              <div className="stat-label">ICT Requisitions</div>
              <div className="stat-value">
                {isAdmin ? stats?.ict?.total || 0 : stats?.my_requests?.ict || 0}
              </div>
              <div className="stat-footer">
                {isAdmin && (
                  <span className="text-warning fw-semibold">{stats?.ict?.pending || 0} pending</span>
                )}{' '}
                approval
              </div>
            </div>
          </div>
        )}

        {(isAdmin || user?.role === 'transport_admin' || isRequester) && (
          <div className="col-md-4">
            <div className="stat-card">
              <div className="stat-icon" style={{ background: '#fef3c7', color: '#d97706' }}>
                <i className="bi bi-truck"></i>
              </div>
              <div className="stat-label">Transport Requisitions</div>
              <div className="stat-value">
                {isAdmin ? stats?.transport?.total || 0 : stats?.my_requests?.transport || 0}
              </div>
              <div className="stat-footer">
                {isAdmin && (
                  <span className="text-warning fw-semibold">
                    {stats?.transport?.pending || 0} pending
                  </span>
                )}{' '}
                approval
              </div>
            </div>
          </div>
        )}

        {(isAdmin || user?.role === 'internal_admin' || isRequester) && (
          <div className="col-md-4">
            <div className="stat-card">
              <div className="stat-icon" style={{ background: '#dcfce7', color: '#16a34a' }}>
                <i className="bi bi-clipboard-check"></i>
              </div>
              <div className="stat-label">Internal Requisitions</div>
              <div className="stat-value">
                {isAdmin ? stats?.internal?.total || 0 : stats?.my_requests?.internal || 0}
              </div>
              <div className="stat-footer">
                {isAdmin && (
                  <span className="text-warning fw-semibold">
                    {stats?.internal?.pending || 0} pending
                  </span>
                )}{' '}
                approval
              </div>
            </div>
          </div>
        )}

        {(isAdmin || user?.role === 'hr_admin') && (
          <div className="col-md-4">
            <div className="stat-card">
              <div className="stat-icon" style={{ background: '#e0e7ff', color: '#4338ca' }}>
                <i className="bi bi-door-open"></i>
              </div>
              <div className="stat-label">Meeting Room Bookings</div>
              <div className="stat-value">{stats?.meetspace?.total || 0}</div>
              <div className="stat-footer">
                <span className="text-warning fw-semibold">{stats?.meetspace?.pending || 0} pending</span>{' '}
                approval
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="row g-4">
        {(isAdmin || user?.role === 'ict_admin') && (
          <div className="col-md-4">
            <div className="card">
              <div className="card-header d-flex align-items-center gap-2">
                <i className="bi bi-pc-display" style={{ color: '#2563eb' }}></i> ICT Requisition
              </div>
              <div className="card-body text-center py-4">
                <p className="text-muted mb-3">Manage IT equipment and software requests</p>
                <Link to="/ict" className="btn btn-primary">
                  <i className="bi bi-arrow-right-circle me-1"></i> Manage
                </Link>
              </div>
            </div>
          </div>
        )}

        {(isAdmin || user?.role === 'transport_admin') && (
          <div className="col-md-4">
            <div className="card">
              <div className="card-header d-flex align-items-center gap-2">
                <i className="bi bi-truck" style={{ color: '#d97706' }}></i> Transport Requisition
              </div>
              <div className="card-body text-center py-4">
                <p className="text-muted mb-3">Manage vehicle transport requests</p>
                <Link to="/transport" className="btn btn-primary">
                  <i className="bi bi-arrow-right-circle me-1"></i> Manage
                </Link>
              </div>
            </div>
          </div>
        )}

        {(isAdmin || user?.role === 'internal_admin') && (
          <div className="col-md-4">
            <div className="card">
              <div className="card-header d-flex align-items-center gap-2">
                <i className="bi bi-clipboard-check" style={{ color: '#16a34a' }}></i> Internal
                Requisition
              </div>
              <div className="card-body text-center py-4">
                <p className="text-muted mb-3">Manage office supplies and resource requests</p>
                <Link to="/internal" className="btn btn-primary">
                  <i className="bi bi-arrow-right-circle me-1"></i> Manage
                </Link>
              </div>
            </div>
          </div>
        )}

        {(isAdmin || user?.role === 'hr_admin') && (
          <div className="col-md-4">
            <div className="card">
              <div className="card-header d-flex align-items-center gap-2">
                <i className="bi bi-door-open" style={{ color: '#4338ca' }}></i> Meeting Room Booking
              </div>
              <div className="card-body text-center py-4">
                <p className="text-muted mb-3">Manage meeting room bookings</p>
                <Link to="/meetspace" className="btn btn-primary">
                  <i className="bi bi-arrow-right-circle me-1"></i> Manage
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* User Management (admin only) */}
      {isAdmin && (
        <div className="row mt-4">
          <div className="col-12">
            <div className="card">
              <div className="card-header d-flex align-items-center justify-content-between">
                <span>
                  <i className="bi bi-people-fill me-2" style={{ color: '#2563eb' }}></i> User
                  Management
                </span>
                {pendingUsers > 0 && (
                  <span className="badge bg-warning">
                    <i className="bi bi-clock me-1"></i>
                    {pendingUsers} pending approval
                  </span>
                )}
              </div>
              <div className="card-body text-center py-4">
                <p className="text-muted mb-3">
                  Manage users, approve pending accounts, and assign roles
                </p>
                <Link to="/admin/users" className="btn btn-primary">
                  <i className="bi bi-arrow-right-circle me-1"></i> Manage Users
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
