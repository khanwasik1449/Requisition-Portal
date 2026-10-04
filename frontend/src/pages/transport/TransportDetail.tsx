import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/axios'

interface TransportDetail {
  id: number
  request_number: string
  status: string
  email_address: string
  full_name: string
  mobile_number: string
  designation: string
  pin: string
  num_passengers: number
  vehicle_type: string
  vehicle_type_display?: string
  vehicle_type_other?: string
  pick_up_date: string
  pick_up_time: string
  pick_up_location: string
  destination: string
  drop_off_date: string
  drop_off_time: string
  drop_off_location: string
  travelling_reason: string
  project_name_code: string
  budget_code: string
  supervisor_acknowledged: boolean
  comments_remarks?: string
  driver_name?: string
  driver_cell?: string
  vehicle_registration?: string
  rejection_reason?: string
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'rejected')
    return (
      <span className="badge bg-danger text-nowrap">
        <i className="bi bi-x-circle me-1"></i>Declined
      </span>
    )
  if (status === 'approved' || status === 'assigned' || status === 'completed')
    return (
      <span className="badge bg-success text-nowrap">
        <i className="bi bi-check-circle me-1"></i>
        {status}
      </span>
    )
  return (
    <span className="badge bg-warning text-nowrap">
      <i className="bi bi-hourglass-split me-1"></i>
      {status}
    </span>
  )
}

// Exact replica of templates/transport_requisition/detail.html
export function TransportDetail() {
  const { id } = useParams()
  const { data: r, isLoading } = useQuery({
    queryKey: ['transport', id],
    queryFn: async () => {
      const response = await api.get<TransportDetail>(`/transport/${id}/`)
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
      <div className="col-lg-10">
        <div className="card">
          <div className="card-header d-flex align-items-center justify-content-between">
            <span>
              <i className="bi bi-info-circle me-2" style={{ color: '#d97706' }}></i>Transport
              Requisition {r.request_number}
            </span>
            <span>
              <StatusBadge status={r.status} />
            </span>
          </div>
          <div className="card-body">
            <h6 className="fw-bold mb-3" style={{ color: '#d97706' }}>
              <i className="bi bi-person me-1"></i> Personal Information
            </h6>
            <div className="row mb-3">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Email Address</label>
                <div className="fw-semibold">{r.email_address}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Full Name</label>
                <div className="fw-semibold">{r.full_name}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Mobile Number</label>
                <div className="fw-semibold">{r.mobile_number}</div>
              </div>
            </div>
            <div className="row mb-4">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Designation</label>
                <div className="fw-semibold">{r.designation}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">PIN</label>
                <div className="fw-semibold">{r.pin}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Passengers</label>
                <div className="fw-semibold">{r.num_passengers}</div>
              </div>
            </div>

            <h6 className="fw-bold mb-3" style={{ color: '#d97706' }}>
              <i className="bi bi-truck me-1"></i> Trip Details
            </h6>
            <div className="row mb-3">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Vehicle Type</label>
                <div>
                  <span className="badge bg-light text-dark border">
                    {r.vehicle_type_display || r.vehicle_type}
                    {r.vehicle_type === 'other' && r.vehicle_type_other
                      ? ` — ${r.vehicle_type_other}`
                      : ''}
                  </span>
                </div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Pick-up Date</label>
                <div className="fw-semibold">{r.pick_up_date}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Pick-up Time</label>
                <div className="fw-semibold">{r.pick_up_time}</div>
              </div>
            </div>
            <div className="row mb-3">
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Pick-up Location</label>
                <div className="fw-semibold">{r.pick_up_location}</div>
              </div>
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Destination</label>
                <div className="fw-semibold">{r.destination}</div>
              </div>
            </div>
            <div className="row mb-4">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Drop-off Date</label>
                <div className="fw-semibold">{r.drop_off_date}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Drop-off Time</label>
                <div className="fw-semibold">{r.drop_off_time}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Drop-off Location</label>
                <div className="fw-semibold">{r.drop_off_location}</div>
              </div>
            </div>

            <h6 className="fw-bold mb-3" style={{ color: '#d97706' }}>
              <i className="bi bi-journal-text me-1"></i> Additional Information
            </h6>
            <div className="row mb-3">
              <div className="col-12 mb-2">
                <label className="form-label text-muted small mb-1">Travelling Reason</label>
                <div className="bg-light rounded p-3">{r.travelling_reason}</div>
              </div>
            </div>
            <div className="row mb-3">
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Project Name & Code</label>
                <div className="fw-semibold">{r.project_name_code}</div>
              </div>
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Budget Code</label>
                <div className="fw-semibold">{r.budget_code}</div>
              </div>
            </div>
            <div className="row mb-3">
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Supervisor Acknowledged</label>
                <div className="fw-semibold">
                  {r.supervisor_acknowledged ? (
                    <span className="badge bg-success">
                      <i className="bi bi-check-circle me-1"></i>Yes
                    </span>
                  ) : (
                    <span className="badge bg-warning">
                      <i className="bi bi-x-circle me-1"></i>No
                    </span>
                  )}
                </div>
              </div>
            </div>
            {r.comments_remarks && (
              <div className="mb-4">
                <label className="form-label text-muted small mb-1">Comments / Remarks</label>
                <div className="bg-light rounded p-3">{r.comments_remarks}</div>
              </div>
            )}

            <h6 className="fw-bold mb-3" style={{ color: '#d97706' }}>
              <i className="bi bi-check2-circle me-1"></i> Approval Status
            </h6>
            <div className="mb-2 p-3 bg-light rounded text-muted">
              <i className="bi bi-clock me-1"></i> Awaiting approval
            </div>

            {r.rejection_reason && (
              <div className="mb-3 p-3 bg-danger bg-opacity-10 rounded d-flex align-items-start gap-2">
                <i className="bi bi-x-circle-fill text-danger mt-1"></i>
                <div>
                  <strong className="text-danger">Rejected</strong>
                  <p className="mb-0 text-danger">{r.rejection_reason}</p>
                </div>
              </div>
            )}

            <h6 className="fw-bold mb-3" style={{ color: '#198754' }}>
              <i className="bi bi-person-badge me-1"></i> Vehicle &amp; Driver Assignment
            </h6>
            {r.driver_name || r.vehicle_registration ? (
              <div className="mb-3 p-3 bg-light rounded">
                <div className="row">
                  <div className="col-md-4 mb-2">
                    <label className="form-label text-muted small mb-1">Vehicle</label>
                    <div className="fw-semibold">{r.vehicle_registration || '—'}</div>
                  </div>
                  <div className="col-md-4 mb-2">
                    <label className="form-label text-muted small mb-1">Driver Name</label>
                    <div className="fw-semibold">{r.driver_name || '—'}</div>
                  </div>
                  <div className="col-md-4 mb-2">
                    <label className="form-label text-muted small mb-1">Cell Number</label>
                    <div className="fw-semibold">{r.driver_cell || '—'}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mb-3 p-3 bg-light rounded text-muted">
                <i className="bi bi-clock me-1"></i> No vehicle or driver assigned yet
              </div>
            )}

            <hr />
            <div className="d-flex gap-2">
              <Link to="/transport" className="btn btn-outline-secondary">
                <i className="bi bi-arrow-left me-1"></i> Back
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
