import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { getAllResults } from '@/lib/paginate'
import { apiErrorMessages } from '@/lib/utils'
import { useStaffDefaults } from '@/lib/staffDefaults'
import type { BookingRow, Room } from '@/lib/meetspace'
import { BookingSubmitted } from './BookingSubmitted'

// Exact replica of meetspace/templates/meetspace/booking_form.html
export function MeetSpaceBooking() {
  const navigate = useNavigate()
  const [errors, setErrors] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  // booking_create renders booking_submitted.html for the *same* request, so
  // success swaps this form out rather than routing away.
  const [submitted, setSubmitted] = useState<BookingRow | null>(null)
  const staffDefaults = useStaffDefaults()
  const emailRef = useRef<HTMLInputElement>(null)

  const { data: rooms } = useQuery({
    queryKey: ['rooms', 'public'],
    // booking_create builds its picker from active rooms with no session, so
    // RoomViewSet.read stays open to anonymous callers for exactly this.
    queryFn: async () => getAllResults<Room>('/rooms/'),
  })

  // This route is public, so the signed-in account may only arrive after the
  // first render. Fill the address in then, if the applicant left it blank.
  useEffect(() => {
    if (emailRef.current && !emailRef.current.value) {
      emailRef.current.value = staffDefaults.email_address
    }
  }, [staffDefaults.email_address])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setErrors([])
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
      const created = await api.post<BookingRow>('/meetspace/', data)
      // The create response already carries the saved booking (nested room
      // included), exactly as booking_create renders booking_submitted.html
      // from the instance it just saved -- so there is no second request for
      // an anonymous caller to be bounced to /login over.
      setSubmitted(created.data)
    } catch (err: any) {
      setErrors(
        apiErrorMessages(err.response?.data, 'Failed to submit booking request.'),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitted) {
    return <BookingSubmitted booking={submitted} onReset={() => setSubmitted(null)} />
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-7">
        <div className="card">
          <div className="card-header">
            <i className="bi bi-calendar-plus me-1"></i> Request a room
          </div>
          <div className="card-body">
            {/* booking_create collects every guard it finds and shows them all,
                so one alert lists the same sentences rather than one field slot. */}
            {errors.length > 0 && (
              <div className="alert alert-danger py-2 small">
                {errors.map((message, i) => (
                  <div key={i}>{message}</div>
                ))}
              </div>
            )}
            <form onSubmit={handleSubmit}>
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
                    {(rooms?.results ?? []).map((room) => (
                      <option key={room.id} value={room.id}>
                        Room {room.room_number} (Floor {room.floor},{' '}
                        {room.min_occupancy}–{room.max_occupancy})
                      </option>
                    ))}
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
                  <input
                    type="email"
                    name="email_address"
                    className="form-control"
                    ref={emailRef}
                    defaultValue={staffDefaults.email_address}
                    required
                  />
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
                <Link to="/meetspace/bookings" className="btn btn-outline-secondary">
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
