import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'

interface Booking {
  id: number
  meeting_title: string
  room_number?: string
  date: string
  start_time: string
  end_time: string
  status: string
  status_display?: string
}

// Exact replica of meetspace/templates/meetspace/booking_list.html
export function MeetSpaceList() {
  const { data, isLoading } = useQuery({
    queryKey: ['meetspace'],
    queryFn: async () => {
      const response = await api.get<{ results: Booking[] }>('/meetspace/')
      return response.data
    },
  })

  const getStatusBadge = (status: string, display?: string) => {
    if (status === 'approved') return <span className="badge bg-success">{display || status}</span>
    if (status === 'pending')
      return (
        <span className="badge bg-warning text-dark">{display || status}</span>
      )
    if (status === 'rejected' || status === 'cancelled')
      return <span className="badge bg-danger">{display || status}</span>
    return <span className="badge bg-info">{display || status}</span>
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Bookings</h2>
          <p className="text-muted mb-0 small">Your room booking requests</p>
        </div>
        <Link to="/meetspace/create" className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> New Booking
        </Link>
      </div>

      <div className="card">
        <div className="card-body">
          <form className="row g-2 align-items-end">
            <div className="col-md-4">
              <label className="form-label small">Status</label>
              <select name="status" className="form-select form-select-sm" defaultValue="">
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="cancelled">Cancelled</option>
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
                  <td colSpan={6} className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </td>
                </tr>
              ) : data?.results.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-4">
                    No bookings found.
                  </td>
                </tr>
              ) : (
                data?.results.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <Link to={`/meetspace/${b.id}`}>{b.meeting_title}</Link>
                    </td>
                    <td>{b.room_number || '—'}</td>
                    <td>{b.date}</td>
                    <td>
                      {b.start_time}–{b.end_time}
                    </td>
                    <td>{getStatusBadge(b.status, b.status_display)}</td>
                    <td className="text-end">
                      <Link
                        to={`/meetspace/${b.id}`}
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
