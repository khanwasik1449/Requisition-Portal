import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { useStaffDefaults } from '@/lib/staffDefaults'

// Replica of templates/transport_requisition/track.html

interface TrackRow {
  id: number
  request_number: string
  status: string
  status_display: string
  destination: string
  pick_up_date: string
  pick_up_time: string
  pick_up_location: string
  drop_off_date: string
  drop_off_time: string
  drop_off_location: string
  vehicle_type_display: string
  num_passengers: number
  rejection_reason: string
  driver_name: string
  driver_car_no: string
  driver_cell_number: string
  created_at: string
}

interface Stage {
  key: string
  name: string
  is_terminal: boolean
}

// Django renders `created_at|date:"d M Y, H:i"`.
function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())} ${months[d.getMonth()]} ${d.getFullYear()}, ${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}`
}

export function TransportTrack() {
  const staffDefaults = useStaffDefaults()
  const [email, setEmail] = useState(staffDefaults.email_address)
  const [searched, setSearched] = useState(false)
  const [results, setResults] = useState<TrackRow[]>([])
  const [queryEmail, setQueryEmail] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Stage names/terminal flags drive the badge exactly like
  // templates/transport_requisition/_status_badge.html.
  const { data: stages } = useQuery({
    queryKey: ['moduleWorkflow', 'transport'],
    queryFn: async () => (await api.get<Stage[]>('/public/modules/transport/workflow/')).data,
    staleTime: 5 * 60 * 1000,
  })

  const stageByKey = new Map((stages || []).map((s) => [s.key, s]))

  const statusBadge = (row: TrackRow) => {
    const stage = stageByKey.get(row.status)
    if (stage) {
      return stage.is_terminal ? (
        <span className="badge bg-success text-nowrap">
          <i className="bi bi-check-circle me-1"></i>
          {stage.name}
        </span>
      ) : (
        <span className="badge bg-warning text-nowrap">
          <i className="bi bi-hourglass-split me-1"></i>
          {stage.name}
        </span>
      )
    }
    if (row.status === 'rejected') {
      return (
        <span className="badge bg-danger text-nowrap">
          <i className="bi bi-x-circle me-1"></i>Declined
        </span>
      )
    }
    return <span className="badge bg-secondary text-nowrap">{row.status}</span>
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      const response = await api.get<TrackRow[]>('/transport/track/', {
        params: { email: email.trim() },
      })
      setResults(response.data)
      setQueryEmail(email.trim())
      setSearched(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to look up that address.')
      setSearched(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-10">
        <div className="mb-4">
          <h2 className="fw-bold mb-1" style={{ fontSize: '1.4rem', letterSpacing: '-.02em' }}>
            Track Your Transport Request
          </h2>
          <p className="text-muted mb-0">Enter the email address you used when submitting.</p>
        </div>

        <div className="mb-4">
          <form onSubmit={handleSubmit} noValidate>
            <label className="form-label" htmlFor="track-email">
              Email address
            </label>
            <div className="input-group">
              <input
                type="email"
                name="email"
                id="track-email"
                className="form-control"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                <i className="bi bi-search"></i>{' '}
                {isSubmitting ? 'Tracking…' : 'Track'}
              </button>
            </div>
            <div className="form-text">
              Only requests submitted with this exact email address are shown.
            </div>
          </form>
          {error && (
            <div className="alert alert-danger py-2 small mt-2 mb-0" role="alert">
              <i className="bi bi-exclamation-circle me-1"></i> {error}
            </div>
          )}
        </div>

        {searched &&
          (results.length > 0 ? (
            <>
              <div className="alert alert-success d-flex align-items-center py-2 px-3 small mb-3">
                <i className="bi bi-check-circle me-2"></i>
                {results.length} request{results.length === 1 ? '' : 's'} found for{' '}
                <strong className="ms-1">{queryEmail}</strong>
              </div>

              {results.map((r) => (
                <div className="card mb-3" key={r.id}>
                  <div className="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <span className="fw-semibold">{r.request_number}</span>
                    {statusBadge(r)}
                  </div>
                  <div className="card-body">
                    <table className="table table-sm align-middle mb-0">
                      <tbody>
                        <tr>
                          <td className="text-muted" style={{ width: '34%' }}>
                            Destination
                          </td>
                          <td>{r.destination}</td>
                        </tr>
                        <tr>
                          <td className="text-muted">Pick-up</td>
                          <td>
                            {r.pick_up_date} at {r.pick_up_time} &mdash; {r.pick_up_location}
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">Drop-off</td>
                          <td>
                            {r.drop_off_date} at {r.drop_off_time} &mdash; {r.drop_off_location}
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">Vehicle</td>
                          <td>
                            {r.vehicle_type_display} &middot; {r.num_passengers} passenger
                            {r.num_passengers === 1 ? '' : 's'}
                          </td>
                        </tr>
                        <tr>
                          <td className="text-muted">Submitted</td>
                          <td>{formatDateTime(r.created_at)}</td>
                        </tr>
                        {r.driver_name && (
                          <tr>
                            <td className="text-muted">Driver</td>
                            <td>
                              {r.driver_name} &mdash; {r.driver_car_no} ({r.driver_cell_number})
                            </td>
                          </tr>
                        )}
                        {r.status === 'rejected' && r.rejection_reason && (
                          <tr>
                            <td className="text-muted">Reason</td>
                            <td className="text-danger">{r.rejection_reason}</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="alert alert-warning d-flex align-items-start py-2 px-3 small">
              <i className="bi bi-exclamation-triangle me-2 mt-1"></i>
              <div>
                No requests found for <strong>{queryEmail}</strong>. Check the spelling, or contact
                the transport office if you used a different address.
              </div>
            </div>
          ))}

        <div className="text-center pt-3 border-top">
          <Link to="/transport/create" className="btn btn-outline-primary">
            <i className="bi bi-truck"></i> Submit a new request
          </Link>
        </div>
      </div>
    </div>
  )
}
