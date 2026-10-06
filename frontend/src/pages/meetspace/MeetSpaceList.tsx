import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { getAllResults } from '@/lib/paginate'
import { formatDateDMY, formatTimeHM } from '@/lib/utils'
import { isHrAdmin, statusBadgeClass, type BookingRow } from '@/lib/meetspace'
import { useAuth } from '@/auth/hooks'

// meetspace.views.booking_list passes Booking.Status.choices straight through,
// so the filter offers all five rather than a hand-typed subset.
const STATUS_CHOICES: [string, string][] = [
  ['pending', 'Pending'],
  ['approved', 'Approved'],
  ['rejected', 'Rejected'],
  ['cancelled', 'Cancelled'],
  ['alternatives', 'Alternatives offered'],
]

// Exact replica of meetspace/templates/meetspace/booking_list.html
export function MeetSpaceList() {
  const { user } = useAuth()
  const hrAdmin = isHrAdmin(user?.role)
  const [status, setStatus] = useState('')
  const [applied, setApplied] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['meetspace', applied],
    queryFn: async () =>
      getAllResults<BookingRow>('/meetspace/', applied ? { status: applied } : undefined),
  })

  const bookings = data?.results ?? []
  // main's `{% empty %}` block spans however many columns the header drew.
  const colSpan = hrAdmin ? 7 : 6

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Bookings</h2>
          <p className="text-muted mb-0 small">
            {hrAdmin ? 'All room booking requests' : 'Your room booking requests'}
          </p>
        </div>
        <Link to="/meetspace/bookings/new" className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> New Booking
        </Link>
      </div>

      <div className="card">
        <div className="card-body">
          <form
            className="row g-2 align-items-end"
            onSubmit={(e) => {
              e.preventDefault()
              setApplied(status)
            }}
          >
            <div className="col-md-4">
              <label className="form-label small">Status</label>
              <select
                name="status"
                className="form-select form-select-sm"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="">All</option>
                {STATUS_CHOICES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <button type="submit" className="btn btn-sm btn-outline-secondary">
                Filter
              </button>
            </div>
          </form>
        </div>
        <div className="table-responsive">
          <table className="table align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Meeting</th>
                {hrAdmin && <th>Requester</th>}
                <th>Room</th>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
                <th className="text-end"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={colSpan} className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </td>
                </tr>
              ) : bookings.length === 0 ? (
                <tr>
                  <td colSpan={colSpan} className="text-center text-muted py-4">
                    No bookings found.
                  </td>
                </tr>
              ) : (
                bookings.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <Link to={`/meetspace/bookings/${b.id}`}>{b.meeting_title}</Link>
                    </td>
                    {hrAdmin && <td>{b.user_name || ''}</td>}
                    <td>{b.room_number || '—'}</td>
                    <td>{formatDateDMY(b.date)}</td>
                    <td>
                      {formatTimeHM(b.start_time)}–{formatTimeHM(b.end_time)}
                    </td>
                    <td>
                      <span className={`badge ${statusBadgeClass(b.status)}`}>
                        {b.status_display || b.status}
                      </span>
                    </td>
                    <td className="text-end">
                      <Link
                        to={`/meetspace/bookings/${b.id}`}
                        className="btn btn-sm btn-outline-secondary"
                      >
                        <i className="bi bi-eye"></i>
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
