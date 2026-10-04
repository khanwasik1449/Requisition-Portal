import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/axios'

interface BookingDetail {
  id: number
  meeting_title: string
  status: string
  status_display?: string
  requester_name?: string
  room_number?: string
  room_floor?: number
  date: string
  start_time: string
  end_time: string
  number_of_participants: number
  requirements?: string
  cancellation_reason?: string
}

// Exact replica of meetspace/templates/meetspace/booking_detail.html
export function MeetSpaceDetail() {
  const { id } = useParams()
  const { data: b, isLoading } = useQuery({
    queryKey: ['meetspace', id],
    queryFn: async () => {
      const response = await api.get<BookingDetail>(`/meetspace/${id}/`)
      return response.data
    },
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

  if (!b) return <p className="text-muted">Booking not found.</p>

  const statusBadgeClass =
    b.status === 'approved'
      ? 'bg-success'
      : b.status === 'pending'
        ? 'bg-warning text-dark'
        : b.status === 'rejected' || b.status === 'cancelled'
          ? 'bg-danger'
          : 'bg-info'

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card">
          <div className="card-header d-flex align-items-center justify-content-between">
            <span>
              <i className="bi bi-calendar3 me-1"></i>
              {b.meeting_title}
            </span>
            <span className={`badge ${statusBadgeClass}`}>
              {b.status_display || b.status}
            </span>
          </div>
          <div className="card-body">
            <div className="row g-3 mb-3">
              <div className="col-md-6">
                <label className="form-label text-muted small">Requester</label>
                <div className="fw-semibold">{b.requester_name || '—'}</div>
              </div>
              <div className="col-md-6">
                <label className="form-label text-muted small">Room</label>
                <div className="fw-semibold">
                  Room {b.room_number || '—'}
                  {b.room_floor ? ` (Floor ${b.room_floor})` : ''}
                </div>
              </div>
              <div className="col-md-4">
                <label className="form-label text-muted small">Date</label>
                <div>{b.date}</div>
              </div>
              <div className="col-md-4">
                <label className="form-label text-muted small">Time</label>
                <div>
                  {b.start_time} – {b.end_time}
                </div>
              </div>
              <div className="col-md-4">
                <label className="form-label text-muted small">Participants</label>
                <div>{b.number_of_participants}</div>
              </div>
              {b.requirements && (
                <div className="col-12">
                  <label className="form-label text-muted small">Requirements</label>
                  <div className="bg-light rounded p-2">{b.requirements}</div>
                </div>
              )}
            </div>

            {b.cancellation_reason && (
              <div className="alert alert-danger">
                <strong>Reason:</strong> {b.cancellation_reason}
              </div>
            )}

            <hr />
            <div className="d-flex flex-wrap gap-2">
              <Link to="/meetspace" className="btn btn-outline-secondary">
                <i className="bi bi-arrow-left me-1"></i> Back
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
