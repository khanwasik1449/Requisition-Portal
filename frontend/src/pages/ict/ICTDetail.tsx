import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { ReasonModal } from '@/components/workflow/WorkflowModals'
import { formatDateDMY, formatStamp } from '@/lib/utils'

interface ICTDetail {
  id: number
  request_number: string
  status: string
  full_name: string
  email_address: string
  designation: string
  pin_number: string
  contact_number: string
  requisition_date: string
  requirement_date: string
  return_date?: string
  equipment_list?: string[]
  equipment_specification?: string
  purpose: string
  supervisor_name?: string
  // detail.html prints "{{ r.first_approver.username }} on ...|date:"M d, Y H:i""
  first_approver?: number
  first_approver_name?: string
  first_approved_at?: string
  second_approver?: number
  second_approver_name?: string
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

// Exact replica of templates/ict_requisition/detail.html
export function ICTDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [showReject, setShowReject] = useState(false)
  const { data: r, isLoading } = useQuery({
    queryKey: ['ict', id],
    queryFn: async () => {
      const response = await api.get<ICTDetail>(`/ict/${id}/`)
      return response.data
    },
  })

  const { data: act } = useQuery({
    queryKey: ['ict-actions', id],
    queryFn: async () => {
      const response = await api.get<{ can_act: boolean }>(`/ict/${id}/actions/`)
      return response.data
    },
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['ict', id] })
    queryClient.invalidateQueries({ queryKey: ['ict'] })
  }
  const approveMutation = useMutation({
    mutationFn: () => api.post(`/ict/${id}/approve/`, {}),
    onSuccess: refresh,
  })
  const rejectMutation = useMutation({
    mutationFn: (reason: string) => api.post(`/ict/${id}/decline/`, { reason }),
    onSuccess: refresh,
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
              <i className="bi bi-info-circle me-2" style={{ color: '#2563eb' }}></i>ICT Requisition{' '}
              {r.request_number}
            </span>
            <span>
              <StatusBadge status={r.status} />
            </span>
          </div>
          <div className="card-body">
            <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
              <i className="bi bi-person me-1"></i> Personal Information
            </h6>
            <div className="row mb-3">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Full Name</label>
                <div className="fw-semibold">{r.full_name}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">ICT Email Address</label>
                <div className="fw-semibold">{r.email_address}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Designation</label>
                <div className="fw-semibold">{r.designation}</div>
              </div>
            </div>
            <div className="row mb-4">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">PIN Number</label>
                <div className="fw-semibold">{r.pin_number}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Contact Number</label>
                <div className="fw-semibold">{r.contact_number}</div>
              </div>
            </div>

            <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
              <i className="bi bi-calendar me-1"></i> Dates
            </h6>
            <div className="row mb-4">
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Requisition Date</label>
                <div className="fw-semibold">{formatDateDMY(r.requisition_date)}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Requirement Date</label>
                <div className="fw-semibold">{formatDateDMY(r.requirement_date)}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Return Date</label>
                <div className="fw-semibold">
                  {r.return_date || <span className="text-muted">N/A</span>}
                </div>
              </div>
            </div>

            <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
              <i className="bi bi-device-ssd me-1"></i> Equipment Details
            </h6>
            <div className="row mb-3">
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Device / Equipment</label>
                <div className="fw-semibold">
                  <ul className="mb-0 ps-3" style={{ listStyleType: 'disc' }}>
                    {r.equipment_list?.map((item, i) => <li key={i}>{item}</li>)}
                  </ul>
                </div>
              </div>
              <div className="col-md-6 mb-2">
                <label className="form-label text-muted small mb-1">Supervisor</label>
                <div className="fw-semibold">
                  {r.supervisor_name || <span className="text-muted">N/A</span>}
                </div>
              </div>
            </div>
            <div className="mb-3">
              <label className="form-label text-muted small mb-1">
                Equipment Specification / Configuration
              </label>
              <div className="bg-light rounded p-3">
                {r.equipment_specification || <span className="text-muted">None provided</span>}
              </div>
            </div>
            <div className="mb-4">
              <label className="form-label text-muted small mb-1">Purpose</label>
              <div className="bg-light rounded p-3">{r.purpose}</div>
            </div>

            <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
              <i className="bi bi-check2-circle me-1"></i> Approval Status
            </h6>
            {r.first_approver && (
              <div className="mb-2 p-3 bg-light rounded d-flex align-items-center gap-2">
                <i className="bi bi-check-circle-fill text-success"></i>
                <span>
                  <strong>1st Approval:</strong> {r.first_approver_name} on{' '}
                  {formatStamp(r.first_approved_at)}
                </span>
              </div>
            )}
            {r.second_approver && (
              <div className="mb-2 p-3 bg-light rounded d-flex align-items-center gap-2">
                <i className="bi bi-check-circle-fill text-success"></i>
                <span>
                  <strong>2nd Approval:</strong> {r.second_approver_name} on{' '}
                  {formatStamp(r.second_approved_at)}
                </span>
              </div>
            )}
            {!r.first_approver && !r.second_approver && r.status !== 'rejected' && (
              <div className="mb-2 p-3 bg-light rounded text-muted">
                <i className="bi bi-clock me-1"></i> Awaiting approval
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
            <div className="d-flex gap-2 flex-wrap">
              <Link to="/ict" className="btn btn-outline-secondary">
                <i className="bi bi-arrow-left me-1"></i> Back
              </Link>
              {act?.can_act && (
                <>
                  <button
                    type="button"
                    className="btn btn-success"
                    onClick={() => approveMutation.mutate()}
                    disabled={approveMutation.isPending}
                  >
                    <i className="bi bi-check-lg me-1"></i> Approve
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => setShowReject(true)}
                  >
                    <i className="bi bi-x-lg me-1"></i> Reject
                  </button>
                </>
              )}
              {approveMutation.isError && (
                <div className="w-100 alert alert-danger py-2 mb-0">
                  <i className="bi bi-exclamation-triangle me-1"></i>
                  {(
                    approveMutation.error as { response?: { data?: { error?: string } } }
                  )?.response?.data?.error || 'Could not approve this requisition.'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <ReasonModal
        open={showReject}
        title="Reject Requisition"
        label="Reason"
        placeholder="What does the requester need to fix?"
        helpText="The requester is emailed this reason."
        confirmLabel="Reject"
        confirmClassName="btn-danger"
        onSubmit={async (reason) => {
          await rejectMutation.mutateAsync(reason)
        }}
        onClose={() => setShowReject(false)}
      />
    </div>
  )
}
