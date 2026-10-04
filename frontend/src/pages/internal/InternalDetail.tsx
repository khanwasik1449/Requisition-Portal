import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/axios'

interface InternalDetail {
  id: number
  request_number: string
  status: string
  email_address: string
  full_name: string
  mobile_number: string
  designation: string
  pin: string
  department: string
  equipment_items?: { name: string; quantity: number; purpose: string }[]
  first_approver?: string
  first_approved_at?: string
  second_approver?: string
  second_approved_at?: string
  rejection_reason?: string
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'pending_first')
    return (
      <span className="badge bg-warning">
        <i className="bi bi-hourglass-split me-1"></i>Pending First Approval
      </span>
    )
  if (status === 'pending_second')
    return (
      <span className="badge bg-info">
        <i className="bi bi-hourglass-split me-1"></i>Pending Second Approval
      </span>
    )
  if (status === 'approved')
    return (
      <span className="badge bg-success">
        <i className="bi bi-check-circle me-1"></i>Approved
      </span>
    )
  if (status === 'rejected')
    return (
      <span className="badge bg-danger">
        <i className="bi bi-x-circle me-1"></i>Rejected
      </span>
    )
  return null
}

// Exact replica of templates/internal_requisition/detail.html
export function InternalDetail() {
  const { id } = useParams()
  const { data: r, isLoading } = useQuery({
    queryKey: ['internal', id],
    queryFn: async () => {
      const response = await api.get<InternalDetail>(`/internal/${id}/`)
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

  if (!r) return <p className="text-muted">Requisition not found.</p>

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card">
          <div className="card-header d-flex align-items-center justify-content-between">
            <span>
              <i className="bi bi-info-circle me-2" style={{ color: '#16a34a' }}></i>Requisition
              Details
            </span>
            <span>
              <StatusBadge status={r.status} />
            </span>
          </div>
          <div className="card-body">
            <h6 className="fw-bold mb-3" style={{ color: '#16a34a' }}>
              <i className="bi bi-person me-1"></i> Personal Information
            </h6>
            <div className="row mb-4">
              <div className="col-md-4 mb-3">
                <label className="form-label text-muted small mb-1">Email Address</label>
                <div className="fw-semibold">{r.email_address}</div>
              </div>
              <div className="col-md-4 mb-3">
                <label className="form-label text-muted small mb-1">Full Name</label>
                <div className="fw-semibold">{r.full_name}</div>
              </div>
              <div className="col-md-4 mb-3">
                <label className="form-label text-muted small mb-1">Mobile Number</label>
                <div className="fw-semibold">{r.mobile_number}</div>
              </div>
            </div>
            <div className="row mb-4">
              <div className="col-md-4 mb-3">
                <label className="form-label text-muted small mb-1">Designation</label>
                <div className="fw-semibold">{r.designation}</div>
              </div>
              <div className="col-md-4 mb-3">
                <label className="form-label text-muted small mb-1">PIN</label>
                <div className="fw-semibold">{r.pin}</div>
              </div>
              <div className="col-md-4 mb-3">
                <label className="form-label text-muted small mb-1">Department</label>
                <div>
                  <span className="badge bg-light text-dark border">{r.department}</span>
                </div>
              </div>
            </div>

            <h6 className="fw-bold mb-3" style={{ color: '#16a34a' }}>
              <i className="bi bi-box-seam me-1"></i> Equipment Items
            </h6>
            <div className="table-responsive mb-4">
              <table className="table table-sm table-bordered">
                <thead className="table-light">
                  <tr>
                    <th>#</th>
                    <th>Equipment Name</th>
                    <th>Quantity</th>
                    <th>Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  {r.equipment_items?.length ? (
                    r.equipment_items.map((item, i) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        <td className="fw-semibold">{item.name}</td>
                        <td>{item.quantity}</td>
                        <td>{item.purpose}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="text-muted text-center">
                        No equipment items listed.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {r.first_approver && (
              <div className="mb-2 p-3 bg-light rounded d-flex align-items-center gap-2">
                <i className="bi bi-check-circle-fill text-success"></i>
                <span>
                  <strong>1st Approval:</strong> {r.first_approver} on {r.first_approved_at}
                </span>
              </div>
            )}

            {r.second_approver && (
              <div className="mb-2 p-3 bg-light rounded d-flex align-items-center gap-2">
                <i className="bi bi-check-circle-fill text-success"></i>
                <span>
                  <strong>2nd Approval:</strong> {r.second_approver} on {r.second_approved_at}
                </span>
              </div>
            )}

            {r.rejection_reason && (
              <div className="mb-3 p-3 bg-danger bg-opacity-10 rounded d-flex align-items-start gap-2">
                <i className="bi bi-x-circle-fill text-danger mt-1"></i>
                <div>
                  <strong className="text-danger">Rejected</strong>
                  <p className="mb-0 text-danger">{r.rejection_reason}</p>
                </div>
              </div>
            )}

            <hr />
            <div className="d-flex gap-2">
              <Link to="/internal" className="btn btn-outline-secondary">
                <i className="bi bi-arrow-left me-1"></i> Back
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
