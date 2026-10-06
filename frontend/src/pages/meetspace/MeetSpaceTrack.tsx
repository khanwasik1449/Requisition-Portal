import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { apiErrorMessages, formatDateDMY, formatTimeHM } from '@/lib/utils'
import type { BookingRow } from '@/lib/meetspace'

interface TrackData {
  searched: boolean
  email: string
  bookings: BookingRow[]
}

/**
 * Exact replica of meetspace/templates/meetspace/track.html, which extends
 * base_public.html — the route wraps this in PublicLayout.
 */
export function MeetSpaceTrack() {
  const [email, setEmail] = useState('')
  const [searched, setSearched] = useState<string | null>(null)
  const [formError, setFormError] = useState('')

  const { data, isFetching, error } = useQuery({
    queryKey: ['meetSpaceTrack', searched],
    queryFn: async () =>
      (await api.get<TrackData>(`/meetspace/track/?email=${encodeURIComponent(searched!)}`)).data,
    enabled: searched !== null,
    // The lookup is a plain answer from the view, not a transient failure.
    retry: false,
  })

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    // track_view validates before it searches: an empty address gets its own
    // sentence and the form re-renders untouched.
    if (!email.trim()) {
      setFormError('Please enter the email address you used.')
      setSearched(null)
      return
    }
    setFormError('')
    setSearched(email.trim())
  }

  const serverError = error
    ? apiErrorMessages((error as any)?.response?.data, 'Unable to look up that address.')
    : []
  const bookings = data?.searched ? data.bookings : []

  return (
    <>
      <div className="mb-4">
        <h2 className="pub-title mb-1">Track Your Booking</h2>
        <p className="pub-sub">Enter the email address you used when booking.</p>
      </div>

      {formError && <div className="alert alert-danger py-2 small">{formError}</div>}
      {serverError.length > 0 && (
        <div className="alert alert-danger py-2 small">{serverError.join(' ')}</div>
      )}

      <div className="mb-4">
        <form onSubmit={onSubmit} noValidate>
          <label className="form-label" htmlFor="email">
            Email address
          </label>
          <div className="input-group">
            <input
              type="email"
              name="email"
              id="email"
              className="form-control"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
            <button type="submit" className="pub-btn pub-btn-primary" disabled={isFetching}>
              <i className="bi bi-search"></i> Track
            </button>
          </div>
          <div className="form-text">
            Only bookings submitted with this exact email address are shown.
          </div>
        </form>
      </div>

      {data?.searched && (
        <>
          {bookings.length > 0 ? (
            <>
              <div className="alert alert-success d-flex align-items-center py-2 px-3 small mb-3">
                <i className="bi bi-check-circle me-2"></i>
                {bookings.length} booking{bookings.length === 1 ? '' : 's'} found for{' '}
                <strong className="ms-1">{data.email}</strong>
              </div>

              {bookings.map((b) => (
                <div className="card mb-3" key={b.id}>
                  <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <span className="fw-semibold">{b.meeting_title}</span>
                    <TrackBadge status={b.status} />
                  </div>
                  <div className="card-body">
                    <table className="table table-sm align-middle">
                      <tbody>
                        <tr>
                          <td className="text-muted" style={{ width: '30%' }}>
                            Room
                          </td>
                          <td>
                            {b.room?.room_number} (Floor {b.room?.floor})
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">Date</td>
                          <td>{formatDateDMY(b.date)}</td>
                        </tr>
                        <tr>
                          <td className="text-muted">Time</td>
                          <td>
                            {formatTimeHM(b.start_time)} – {formatTimeHM(b.end_time)}
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">Participants</td>
                          <td>{b.number_of_participants}</td>
                        </tr>
                        {b.requirements && (
                          <tr>
                            <td className="text-muted">Requirements</td>
                            <td>{b.requirements}</td>
                          </tr>
                        )}
                        {b.cancellation_reason && (
                          <tr>
                            <td className="text-muted">Reason</td>
                            <td className="text-danger">{b.cancellation_reason}</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="alert alert-warning">
              <i className="bi bi-exclamation-triangle me-2"></i>
              No bookings found for <strong>{data.email}</strong>.
            </div>
          )}
        </>
      )}
    </>
  )
}

/**
 * transport_requisition/_status_badge.html as track.html's include resolves it.
 *
 * The include expects `stage_by_key`, which `track_view` never passes, so the
 * stage branch is always empty: only `rejected` gets a coloured badge ("Declined"),
 * and every other status falls through to a bare secondary badge showing the raw
 * value — exactly what the template prints.
 */
function TrackBadge({ status }: { status: string }) {
  if (status === 'rejected') {
    return (
      <span className="badge bg-danger text-nowrap">
        <i className="bi bi-x-circle me-1"></i>Declined
      </span>
    )
  }
  return <span className="badge bg-secondary text-nowrap">{status}</span>
}
