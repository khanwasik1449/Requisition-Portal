import { Link } from 'react-router-dom'
import { formatDateDMY, formatTimeHM } from '@/lib/utils'
import type { BookingRow } from '@/lib/meetspace'

interface BookingSubmittedProps {
  booking: BookingRow
  /** `booking_create`'s "Book another room" points back at itself. */
  onReset: () => void
}

/**
 * Exact replica of meetspace/templates/meetspace/booking_submitted.html.
 *
 * main does not redirect here — `booking_create` renders this template at
 * `meetingspace/bookings/new/` for the same request — so the caller stays on
 * the form URL and swaps the form out for this panel.
 */
export function BookingSubmitted({ booking, onReset }: BookingSubmittedProps) {
  return (
    <div className="text-center py-5">
      <div className="mb-3" style={{ fontSize: '3rem', color: '#16A34A' }}>
        <i className="bi bi-check-circle-fill"></i>
      </div>
      <h2 className="pub-title mb-2">Booking Submitted</h2>
      <p className="pub-sub mb-4">
        Your meeting room request has been received. The HR admin will review it.
      </p>

      <div className="card mx-auto" style={{ maxWidth: '520px' }}>
        <div className="card-body text-start">
          <table className="table table-sm align-middle mb-0">
            <tbody>
              <tr>
                <td className="text-muted" style={{ width: '35%' }}>
                  Meeting
                </td>
                <td className="fw-semibold">{booking.meeting_title}</td>
              </tr>
              <tr>
                <td className="text-muted">Room</td>
                <td>
                  {booking.room?.room_number} (Floor {booking.room?.floor})
                </td>
              </tr>
              <tr>
                <td className="text-muted">Date</td>
                <td>{formatDateDMY(booking.date)}</td>
              </tr>
              <tr>
                <td className="text-muted">Time</td>
                <td>
                  {formatTimeHM(booking.start_time)} – {formatTimeHM(booking.end_time)}
                </td>
              </tr>
              <tr>
                <td className="text-muted">Status</td>
                <td>
                  <span className="badge bg-warning text-dark">
                    {booking.status_display || 'Pending'}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="d-flex gap-2 justify-content-center mt-4">
        <Link to="/meetspace/track" className="pub-btn pub-btn-primary">
          <i className="bi bi-search me-1"></i> Track this booking
        </Link>
        {/* main's `pub-btn-outline` has no rule in base_public.html, so the
            anchor keeps the class it ships with rather than being "fixed". */}
        <button type="button" className="pub-btn pub-btn-outline" onClick={onReset}>
          <i className="bi bi-plus-lg me-1"></i> Book another room
        </button>
      </div>
    </div>
  )
}
