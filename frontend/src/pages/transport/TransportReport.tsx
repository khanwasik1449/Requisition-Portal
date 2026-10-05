import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { formatDateDMY } from '@/lib/utils'

interface ReportRow {
  id: number
  request_number: string
  full_name: string
  destination: string
  vehicle_type: string
  vehicle_type_display: string
  vehicle_type_other: string
  pick_up_date: string
  driver_name: string
  status: string
  status_display: string
}

interface Stage {
  key: string
  name: string
}

interface ReportResponse {
  counts: { total: number; approved: number; rejected: number; pending: number }
  stages: Stage[]
  results: ReportRow[]
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

// main's report.html prints `{{ r.pick_up_date|date:"M d, Y" }}`; delegate to
// the shared helper so it lands in Django's timezone like every other stamp.
function fmtDate(d: string) {
  if (!d) return '—'
  const out = formatDateDMY(d)
  return out || '—'
}

const emptyFilters = { date_from: '', date_to: '', status: '' }

// Replica of templates/transport_requisition/report.html
export function TransportReport() {
  const [draft, setDraft] = useState(emptyFilters)
  const [applied, setApplied] = useState(emptyFilters)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['transportReport', applied],
    queryFn: async () => {
      const response = await api.get<ReportResponse>('/transport/report/', {
        params: applied,
      })
      return response.data
    },
  })

  const counts = data?.counts
  const results = data?.results || []
  const stages = data?.stages || []

  // Download through axios so the JWT is attached -- a plain <a href> cannot
  // carry the Authorization header.
  const handleExport = async () => {
    const response = await api.get('/transport/report/export/', {
      params: applied,
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = 'transport_requisitions.xlsx'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <style>{`
        @media print {
          .sidebar, .topbar, .btn, .content-card .card-header, footer, form { display: none !important; }
          .main-wrapper { margin-left: 0 !important; padding: 0 !important; }
          .card { border: none !important; box-shadow: none !important; }
          .badge { border: 1px solid #000 !important; }
        }
      `}</style>

      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Transport Requisition Report</h2>
          <p className="text-muted mb-0 small">View and filter all transport requisitions</p>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-success" onClick={handleExport}>
            <i className="bi bi-file-earmark-excel me-1"></i> Excel
          </button>
          <button className="btn btn-outline-secondary" onClick={() => window.print()}>
            <i className="bi bi-printer me-1"></i> Print
          </button>
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
            <div className="col-md-3">
              <label className="form-label small">Date From</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={draft.date_from}
                onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
              />
            </div>
            <div className="col-md-3">
              <label className="form-label small">Date To</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={draft.date_to}
                onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
              />
            </div>
            <div className="col-md-3">
              <label className="form-label small">Status</label>
              <select
                className="form-select form-select-sm"
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
            <div className="col-md-3 d-flex gap-1">
              <button type="submit" className="btn btn-primary btn-sm flex-fill">
                <i className="bi bi-filter me-1"></i> Filter
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm flex-fill"
                onClick={() => {
                  setDraft(emptyFilters)
                  setApplied(emptyFilters)
                }}
              >
                <i className="bi bi-x me-1"></i> Clear
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <div className="card border-0 shadow-sm" style={{ background: '#f8fafc' }}>
            <div className="card-body text-center">
              <div className="fw-bold fs-3">{counts?.total ?? '—'}</div>
              <div className="text-muted small">Total Requisitions</div>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm" style={{ background: '#f0fdf4' }}>
            <div className="card-body text-center">
              <div className="fw-bold fs-3 text-success">{counts?.approved ?? '—'}</div>
              <div className="text-muted small">Approved</div>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm" style={{ background: '#fef2f2' }}>
            <div className="card-body text-center">
              <div className="fw-bold fs-3 text-danger">{counts?.rejected ?? '—'}</div>
              <div className="text-muted small">Rejected</div>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card border-0 shadow-sm" style={{ background: '#fffbeb' }}>
            <div className="card-body text-center">
              <div className="fw-bold fs-3 text-warning">{counts?.pending ?? '—'}</div>
              <div className="text-muted small">Pending</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Destination</th>
                  <th>Vehicle</th>
                  <th>Pick-up Date</th>
                  <th>Driver</th>
                  <th>Status</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : isError ? (
                  <tr>
                    <td colSpan={8} className="text-center text-danger py-4">
                      Could not load the report.
                    </td>
                  </tr>
                ) : results.length > 0 ? (
                  results.map((r) => (
                    <tr key={r.id}>
                      <td className="fw-semibold">{r.request_number}</td>
                      <td>{r.full_name}</td>
                      <td>{r.destination}</td>
                      <td>
                        <span className="badge bg-light text-dark border">
                          {r.vehicle_type === 'other' && r.vehicle_type_other
                            ? `${r.vehicle_type_display} — ${r.vehicle_type_other}`
                            : r.vehicle_type_display}
                        </span>
                      </td>
                      <td className="small">{fmtDate(r.pick_up_date)}</td>
                      <td>
                        {r.driver_name || <span className="text-muted small">—</span>}
                      </td>
                      <td>
                        <StatusBadge status={r.status} displayName={r.status_display} />
                      </td>
                      <td className="text-end">
                        <Link
                          to={`/transport/${r.id}`}
                          className="btn btn-sm btn-outline-secondary"
                          title="View"
                        >
                          <i className="bi bi-eye"></i>
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="text-center py-4 text-muted">
                      No requisitions match your filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
