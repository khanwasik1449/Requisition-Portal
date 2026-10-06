import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getAllResults } from '@/lib/paginate'
import { formatDateDMY, formatTimeHM } from '@/lib/utils'
import { TransportRequisition } from '@/types'

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

// Exact replica of templates/transport_requisition/list.html
export function TransportList() {
  const { data, isLoading } = useQuery({
    queryKey: ['transport'],
    queryFn: async () => {
      return getAllResults<TransportRequisition>('/transport/')
    },
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Transport Requisitions</h2>
          <p className="text-muted mb-0 small">Manage vehicle transport and trip requests</p>
        </div>
        <Link to="/transport/create" className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> New Request
        </Link>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Destination</th>
                  <th>Vehicle</th>
                  <th>Pick-up</th>
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
                ) : data?.results.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5">
                      <i
                        className="bi bi-truck"
                        style={{ fontSize: '2.5rem', color: '#cbd5e1' }}
                      ></i>
                      <p className="text-muted mt-2 mb-0">No transport requisitions found.</p>
                      <Link to="/transport/create" className="btn btn-primary mt-2">
                        Create One
                      </Link>
                    </td>
                  </tr>
                ) : (
                  data?.results.map((r) => (
                    <tr key={r.id}>
                      <td className="fw-semibold">{r.request_number}</td>
                      <td>{(r as any).full_name || r.user_name}</td>
                      <td>{r.destination}</td>
                      <td>
                        <span className="badge bg-light text-dark border">
                          {(r as any).vehicle_type || '—'}
                        </span>
                      </td>
                      <td className="text-muted small">
                        {formatDateDMY((r as any).pick_up_date)}{' '}
                        {formatTimeHM((r as any).pick_up_time)}
                      </td>
                      <td>
                        {r.driver_name ? (
                          r.driver_name
                        ) : (
                          <span className="text-muted small">—</span>
                        )}
                      </td>
                      <td>
                        <StatusBadge status={r.status} displayName={r.status_display} />
                      </td>
                      <td className="text-end">
                        <div className="d-flex gap-1 justify-content-end">
                          <Link
                            to={`/transport/${r.id}`}
                            className="btn btn-sm btn-outline-secondary"
                            title="View"
                          >
                            <i className="bi bi-eye"></i>
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
