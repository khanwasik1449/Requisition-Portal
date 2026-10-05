import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { formatDateDMY, formatTimeHM } from '@/lib/utils'

interface TrailEntry {
  id: number
  action_display: string
  created_at: string
  /** Null when the action came from the public form -- see `fallback` below. */
  performed_by_display: string | null
  details: string
}

interface HistoryRow {
  id: number
  request_number: string
  full_name: string
  email_address: string
  mobile_number: string
  designation: string
  pin: string
  destination: string
  num_passengers: number
  pick_up_date: string
  pick_up_time: string
  drop_off_date: string
  drop_off_time: string
  travelling_reason: string
  status: string
  status_display: string
  is_public: boolean
  driver_name: string
  trail: TrailEntry[]
}

interface Stage {
  key: string
  name: string
}

interface HistoryResponse {
  counts: {
    total: number
    pending: number
    approved: number
    rejected: number
    public: number
  }
  stages: Stage[]
  results: HistoryRow[]
}

function StatusBadge({ status, displayName }: { status: string; displayName?: string }) {
  if (status === 'rejected') {
    return (
      <span className="badge bg-danger text-nowrap">
        <i className="bi bi-x-circle me-1"></i>Declined
      </span>
    )
  }
  if (status === 'approved' || status === 'assigned') {
    return (
      <span className="badge bg-success text-nowrap">
        <i className="bi bi-check-circle me-1"></i>
        {displayName || status}
      </span>
    )
  }
  return (
    <span className="badge bg-warning text-nowrap">
      <i className="bi bi-hourglass-split me-1"></i>
      {displayName || status}
    </span>
  )
}

/** `d M Y, H:i`, matching the template's `{{ e.created_at|date:"d M Y, H:i" }}`. */
function fmtDateTime(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())} ${months[d.getMonth()]} ${d.getFullYear()}, ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const emptyFilters = { q: '', status: '', date_from: '', date_to: '' }

// Replica of templates/transport_requisition/history.html
export function TransportHistory() {
  const [draft, setDraft] = useState(emptyFilters)
  const [applied, setApplied] = useState(emptyFilters)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['transportHistory', applied],
    queryFn: async () => {
      const response = await api.get<HistoryResponse>('/transport/history/', {
        params: applied,
      })
      return response.data
    },
  })

  const counts = data?.counts
  const results = data?.results || []
  const stages = data?.stages || []

  return (
    <>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
        <div>
          <h2 className="page-title mb-1">Tracking History</h2>
          <p className="text-muted mb-0">Every transport request with its full audit trail. Admin only.</p>
        </div>
        <Link to="/transport/report" className="btn btn-outline-secondary">
          <i className="bi bi-bar-chart me-1"></i> Report
        </Link>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-6 col-lg">
          <div className="stat-card">
            <div className="stat-label">Total</div>
            <div className="stat-value">{counts?.total ?? '—'}</div>
          </div>
        </div>
        <div className="col-6 col-lg">
          <div className="stat-card">
            <div className="stat-label">Pending</div>
            <div className="stat-value">{counts?.pending ?? '—'}</div>
          </div>
        </div>
        <div className="col-6 col-lg">
          <div className="stat-card">
            <div className="stat-label">Approved</div>
            <div className="stat-value">{counts?.approved ?? '—'}</div>
          </div>
        </div>
        <div className="col-6 col-lg">
          <div className="stat-card">
            <div className="stat-label">Rejected</div>
            <div className="stat-value">{counts?.rejected ?? '—'}</div>
          </div>
        </div>
        <div className="col-6 col-lg">
          <div className="stat-card">
            <div className="stat-label">Public Form</div>
            <div className="stat-value">{counts?.public ?? '—'}</div>
          </div>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-body">
          <form
            className="row g-2 align-items-end"
            onSubmit={(e) => {
              e.preventDefault()
              setApplied(draft)
            }}
          >
            <div className="col-md-4">
              <label className="form-label small">Search</label>
              <input
                type="text"
                className="form-control"
                value={draft.q}
                placeholder="Email, name, request #, PIN, destination"
                onChange={(e) => setDraft({ ...draft, q: e.target.value })}
              />
            </div>
            <div className="col-md-2">
              <label className="form-label small">Status</label>
              <select
                className="form-select"
                value={draft.status}
                onChange={(e) => setDraft({ ...draft, status: e.target.value })}
              >
                <option value="">All</option>
                {stages.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.name}
                  </option>
                ))}
                <option value="rejected">Declined</option>
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label small">From</label>
              <input
                type="date"
                className="form-control"
                value={draft.date_from}
                onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
              />
            </div>
            <div className="col-md-2">
              <label className="form-label small">To</label>
              <input
                type="date"
                className="form-control"
                value={draft.date_to}
                onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
              />
            </div>
            <div className="col-md-2 d-flex gap-2">
              <button type="submit" className="btn btn-primary">
                Filter
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={() => {
                  setDraft(emptyFilters)
                  setApplied(emptyFilters)
                }}
              >
                Clear
              </button>
            </div>
          </form>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      ) : isError ? (
        <div className="alert alert-danger">Could not load the tracking history.</div>
      ) : results.length > 0 ? (
        <>
          <p className="text-muted small">
            {results.length} result{results.length === 1 ? '' : 's'}.
          </p>
          {results.map((r) => (
            <div className="card mb-3" key={r.id}>
              <div className="card-header bg-white d-flex justify-content-between align-items-center flex-wrap gap-2">
                <div>
                  <Link to={`/transport/${r.id}`} className="fw-semibold text-decoration-none">
                    {r.request_number}
                  </Link>
                  <span className="text-muted small"> — {r.full_name}</span>
                  {r.is_public && <span className="badge bg-secondary ms-1">Public</span>}
                </div>
                <StatusBadge status={r.status} displayName={r.status_display} />
              </div>
              <div className="card-body">
                <table className="table table-sm mb-3">
                  <tbody>
                    <tr>
                      <td className="text-muted" style={{ width: '22%' }}>
                        Email
                      </td>
                      <td>{r.email_address}</td>
                      <td className="text-muted" style={{ width: '22%' }}>
                        Mobile
                      </td>
                      <td>{r.mobile_number}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Designation</td>
                      <td>{r.designation}</td>
                      <td className="text-muted">PIN</td>
                      <td>{r.pin}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Destination</td>
                      <td>{r.destination}</td>
                      <td className="text-muted">Passengers</td>
                      <td>{r.num_passengers}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Pick-up</td>
                      <td>
                        {formatDateDMY(r.pick_up_date)} {formatTimeHM(r.pick_up_time)}
                      </td>
                      <td className="text-muted">Drop-off</td>
                      <td>
                        {formatDateDMY(r.drop_off_date)} {formatTimeHM(r.drop_off_time)}
                      </td>
                    </tr>
                    <tr>
                      <td className="text-muted">Reason</td>
                      <td colSpan={3}>
                        {r.travelling_reason?.length > 120
                          ? `${r.travelling_reason.slice(0, 120)}…`
                          : r.travelling_reason}
                      </td>
                    </tr>
                  </tbody>
                </table>

                {r.trail && r.trail.length > 0 && (
                  <div className="border-top pt-3">
                    <div className="small fw-semibold text-muted mb-2">AUDIT TRAIL</div>
                    <ul className="list-unstyled small mb-0">
                      {r.trail.map((e) => (
                        <li className="mb-1" key={e.id}>
                          <span className="badge bg-light text-dark border me-2">
                            {e.action_display}
                          </span>
                          <span className="text-muted">{fmtDateTime(e.created_at)}</span>
                          — {e.performed_by_display || 'Public submitter'}
                          {e.details && <span className="text-muted"> ({e.details})</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      ) : (
        <div className="alert alert-warning">No transport requests match these filters.</div>
      )}
    </>
  )
}
