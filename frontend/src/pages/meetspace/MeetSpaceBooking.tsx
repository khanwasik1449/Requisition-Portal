import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/api/axios'

// Exact replica of meetspace/templates/meetspace/booking_form.html
export function MeetSpaceBooking() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const form = e.currentTarget
      const data = {
        meeting_title: (form.meeting_title as HTMLInputElement).value,
        room: (form.room as HTMLSelectElement).value,
        number_of_participants: Number((form.number_of_participants as HTMLInputElement).value),
        date: (form.date as HTMLInputElement).value,
        start_time: (form.start_time as HTMLInputElement).value,
        end_time: (form.end_time as HTMLInputElement).value,
        email_address: (form.email_address as HTMLInputElement).value,
        requirements: (form.requirements as HTMLTextAreaElement).value,
      }
      await api.post('/meetspace/', data)
      navigate('/meetspace')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit booking request.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-7">
        <div className="card">
          <div className="card-header">
            <i className="bi bi-calendar-plus me-1"></i> Request a room
          </div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="alert alert-danger py-2 small">{error}</div>}
              <div className="row g-3">
                <div className="col-12">
                  <label className="form-label">Meeting title</label>
                  <input
                    type="text"
                    name="meeting_title"
                    className="form-control"
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Room</label>
                  <select name="room" className="form-select" required>
                    <option value="">— Select —</option>
                  </select>
                </div>
                <div className="col-md-6">
                  <label className="form-label">Participants</label>
                  <input
                    type="number"
                    name="number_of_participants"
                    className="form-control"
                    min={1}
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">Date</label>
                  <input type="date" name="date" className="form-control" required />
                </div>
                <div className="col-md-4">
                  <label className="form-label">Start time</label>
                  <input type="time" name="start_time" className="form-control" required />
                </div>
                <div className="col-md-4">
                  <label className="form-label">End time</label>
                  <input type="time" name="end_time" className="form-control" required />
                </div>
                <div className="col-12">
                  <label className="form-label">Email address</label>
                  <input type="email" name="email_address" className="form-control" required />
                  <div className="form-text">
                    Used to track your booking and receive notifications.
                  </div>
                </div>
                <div className="col-12">
                  <label className="form-label">
                    Requirements <span className="text-muted">(optional)</span>
                  </label>
                  <textarea
                    name="requirements"
                    rows={2}
                    className="form-control"
                    placeholder="Projector, video conferencing, whiteboard…"
                  />
                </div>
              </div>
              <div className="d-flex gap-2 mt-4">
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  <i className="bi bi-check-lg me-1"></i>{' '}
                  {isSubmitting ? 'Submitting...' : 'Submit request'}
                </button>
                <Link to="/meetspace" className="btn btn-outline-secondary">
                  Cancel
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
