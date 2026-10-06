import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { djangoTitle, formatDateDMY, formatDateMD, formatTimeHM } from '@/lib/utils'
import { statusBadgeClass, type BookingRow } from '@/lib/meetspace'

interface Announcement {
  id: number
  message: string
  created_by_name: string
  created_at: string
}

interface DashboardData {
  stats: Record<string, number>
  recent: BookingRow[]
  announcements: Announcement[]
  is_hr_admin: boolean
}

// Exact replica of meetspace/templates/meetspace/dashboard.html
export function MeetSpaceDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['meetspaceDashboard'],
    queryFn: async () => (await api.get<DashboardData>('/meetspace/dashboard/')).data,
  })

  const hrAdmin = data?.is_hr_admin ?? false
  const recent = data?.recent ?? []
  const announcements = data?.announcements ?? []

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">MeetSpace</h2>
          <p className="text-muted mb-0 small">Meeting room bookings</p>
        </div>
        <div className="d-flex gap-2">
          <Link to="/meetspace/availability" className="btn btn-outline-secondary">
            <i className="bi bi-search me-1"></i> Find a room
          </Link>
          {hrAdmin && (
            <Link to="/meetspace/rooms" className="btn btn-outline-primary">
              <i className="bi bi-door-open me-1"></i> Manage Rooms
            </Link>
          )}
          <Link to="/meetspace/bookings/new" className="btn btn-primary">
            <i className="bi bi-plus-lg me-1"></i> New Booking
          </Link>
        </div>
      </div>

      <div className="row g-3 mb-4">
        {Object.entries(data?.stats ?? {}).map(([label, value]) => (
          <div className="col-6 col-lg-3" key={label}>
            <div className="card">
              <div className="card-body text-center">
                <div className="text-muted small">{djangoTitle(label)}</div>
                <div className="fs-3 fw-bold">{value}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card">
            <div className="card-header d-flex align-items-center justify-content-between">
              <span>
                <i className="bi bi-calendar3 me-1"></i> Recent bookings
              </span>
              <Link to="/meetspace/bookings" className="small">
                View all
              </Link>
            </div>
            <div className="table-responsive">
              <table className="table table-sm mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th>Meeting</th>
                    <th>Room</th>
                    <th>When</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={4} className="text-center py-4">
                        <div className="spinner-border text-primary" role="status">
                          <span className="visually-hidden">Loading...</span>
                        </div>
                      </td>
                    </tr>
                  ) : recent.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="text-center text-muted py-4">
                        No bookings yet.
                      </td>
                    </tr>
                  ) : (
                    recent.map((b) => (
                      <tr key={b.id}>
                        <td>
                          <Link to={`/meetspace/bookings/${b.id}`}>{b.meeting_title}</Link>
                          <div className="small text-muted">{b.user_name || ''}</div>
                        </td>
                        <td>{b.room_number || b.room?.room_number || '—'}</td>
                        <td className="small">
                          {formatDateMD(b.date)} {formatTimeHM(b.start_time)}–
                          {formatTimeHM(b.end_time)}
                        </td>
                        <td>
                          <span className={`badge ${statusBadgeClass(b.status)}`}>
                            {b.status_display || b.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="card">
            <div className="card-header d-flex align-items-center justify-content-between">
              <span>
                <i className="bi bi-megaphone me-1"></i> Announcements
              </span>
              {hrAdmin && (
                <Link to="/meetspace/announcements/new" className="small">
                  Post one
                </Link>
              )}
            </div>
            <div className="card-body">
              {announcements.length === 0 ? (
                <p className="text-muted mb-0">No announcements.</p>
              ) : (
                announcements.map((a) => (
                  <div className="mb-3 pb-3 border-bottom" key={a.id}>
                    <p className="mb-1">{a.message}</p>
                    <div className="small text-muted">
                      {a.created_by_name} · {formatDateDMY(a.created_at)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
