import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { ReasonModal, AssignDriverModal } from '@/components/workflow/WorkflowModals'
import { formatDateDMY, formatStamp, formatTimeHM } from '@/lib/utils'

interface Vehicle {
  id: number
  registration_number: string
  vehicle_type: string
  vehicle_type_display?: string
  make_model?: string
}
interface Driver {
  id: number
  name: string
  cell_number?: string
  car_no?: string
}

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
  // Nested, exactly as the Django template reads them (r.vehicle / r.driver).
  vehicle?: Vehicle | null
  driver?: Driver | null
  assigned_by?: string | null
  assigned_at?: string | null
  grants_amended?: boolean
  grants_remarks?: string
  rejection_reason?: string
}

interface StageInfo {
  key: string
  name: string
  can_approve: boolean
  can_decline: boolean
  can_assign: boolean
  can_amend: boolean
  require_reason_on_decline: boolean
  is_terminal: boolean
}
interface TrailStep {
  key: string
  name: string
  done: boolean
  current: boolean
  at: string | null
  by: string | null
}
interface AmendField {
  key: string
  label: string
  input_type: string
  required: boolean
  placeholder?: string
  options: Array<{ value: string; label: string }>
  value: string | number | null
}
interface TransportActions {
  can_view: boolean
  can_act: boolean
  stage: StageInfo | null
  amendable_fields: AmendField[]
  trail: TrailStep[]
  vehicles?: Array<{
    id: number
    registration_number: string
    vehicle_type_display?: string
    make_model?: string
  }>
  drivers?: Array<{ id: number; name: string; cell_number?: string }>
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

// Django's `date:"M d, Y H:i"` — shared so every detail page stamps identically.
const fmt = formatStamp

// Exact replica of templates/transport_requisition/detail.html
export function TransportDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [showDecline, setShowDecline] = useState(false)
  const [showAssign, setShowAssign] = useState(false)
  const [amendValues, setAmendValues] = useState<Record<string, string>>({})
  const [remarks, setRemarks] = useState('')
  const [amendError, setAmendError] = useState('')

  const { data: r, isLoading } = useQuery({
    queryKey: ['transport', id],
    queryFn: async () => {
      const response = await api.get<TransportDetail>(`/transport/${id}/`)
      return response.data
    },
  })

  const { data: act } = useQuery({
    queryKey: ['transport-actions', id],
    queryFn: async () => {
      const response = await api.get<TransportActions>(`/transport/${id}/actions/`)
      return response.data
    },
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['transport', id] })
    queryClient.invalidateQueries({ queryKey: ['transport-actions', id] })
    queryClient.invalidateQueries({ queryKey: ['transport'] })
  }

  const approveMutation = useMutation({
    mutationFn: (body: { changes?: Record<string, string>; remarks?: string }) =>
      api.post(`/transport/${id}/approve/`, body),
    onSuccess: refresh,
  })
  const declineMutation = useMutation({
    mutationFn: (reason: string) => api.post(`/transport/${id}/decline/`, { reason }),
    onSuccess: refresh,
  })
  const assignMutation = useMutation({
    mutationFn: ({ vehicleId, driverId }: { vehicleId: number; driverId: number }) =>
      api.post(`/transport/${id}/assign/`, { vehicle_id: vehicleId, driver_id: driverId }),
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

  const stage = act?.stage ?? null
  const canAct = act?.can_act ?? false
  const amendable = act?.amendable_fields ?? []
  const showAmendForm = canAct && !!stage?.can_amend && amendable.length > 0
  // A stage that can approve but has nothing to amend needs a plain Approve
  // button, otherwise the chain can never leave its first stage.
  const showPlainApprove = canAct && !!stage?.can_approve && !showAmendForm
  const trail = act?.trail ?? []

  const onAmendChange = (key: string, value: string) =>
    setAmendValues((prev) => ({ ...prev, [key]: value }))

  const submitAmendApprove = async () => {
    setAmendError('')
    const changes: Record<string, string> = {}
    amendable.forEach((f) => {
      const v = amendValues[f.key]
      if (v !== undefined) changes[f.key] = v
    })
    try {
      await approveMutation.mutateAsync({ changes, remarks })
      setAmendValues({})
      setRemarks('')
    } catch (err) {
      const data = (err as { response?: { data?: { error?: string } } })?.response?.data
      setAmendError(data?.error || 'Could not approve this requisition.')
    }
  }

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
                <div className="fw-semibold">{formatDateDMY(r.pick_up_date)}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Pick-up Time</label>
                <div className="fw-semibold">{formatTimeHM(r.pick_up_time)}</div>
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
                <div className="fw-semibold">{formatDateDMY(r.drop_off_date)}</div>
              </div>
              <div className="col-md-4 mb-2">
                <label className="form-label text-muted small mb-1">Drop-off Time</label>
                <div className="fw-semibold">{formatTimeHM(r.drop_off_time)}</div>
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
            {trail.length > 0 ? (
              trail.map((step) => (
                <div
                  key={step.key}
                  className="mb-2 p-3 bg-light rounded d-flex align-items-center gap-2"
                >
                  {step.done && !step.current ? (
                    <>
                      <i className="bi bi-check-circle-fill text-success"></i>
                      <span>
                        <strong>{step.name}:</strong> {step.by || 'approved'}
                        {step.at ? ` on ${fmt(step.at)}` : ''}
                      </span>
                    </>
                  ) : step.current ? (
                    <>
                      <i className="bi bi-hourglass-split text-warning"></i>
                      <span className="text-muted">
                        <strong>{step.name}:</strong> awaiting a decision
                      </span>
                    </>
                  ) : (
                    <>
                      <i className="bi bi-circle text-muted"></i>
                      <span className="text-muted">{step.name}</span>
                    </>
                  )}
                </div>
              ))
            ) : (
              <div className="mb-2 p-3 bg-light rounded text-muted">
                <i className="bi bi-clock me-1"></i> Awaiting approval
              </div>
            )}

            {r.grants_amended && (
              <div className="mb-2 p-3 bg-info bg-opacity-10 rounded small">
                <i className="bi bi-pencil-square me-1"></i>
                <strong>Funding codes corrected by Grants.</strong>
                <ul className="mb-0 mt-1">
                  <li>
                    Project: <code>{r.project_name_code}</code>
                  </li>
                  <li>
                    Budget: <code>{r.budget_code}</code>
                  </li>
                  {r.grants_remarks && <li>Remark: {r.grants_remarks}</li>}
                </ul>
              </div>
            )}

            {r.status === 'rejected' && !r.grants_amended && (
              <div className="mb-2 p-3 bg-light rounded text-muted">
                <i className="bi bi-clock me-1"></i> This requisition was declined before
                completing the chain.
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

            <h6 className="fw-bold mb-3" style={{ color: '#198754' }}>
              <i className="bi bi-person-badge me-1"></i> Vehicle &amp; Driver Assignment
            </h6>
            {r.vehicle || r.driver ? (
              <div className="mb-3 p-3 bg-light rounded">
                <div className="row">
                  <div className="col-md-4 mb-2">
                    <label className="form-label text-muted small mb-1">Vehicle</label>
                    <div className="fw-semibold">
                      {r.vehicle ? r.vehicle.registration_number : <span className="text-muted">—</span>}
                    </div>
                    {r.vehicle && (
                      <div className="small text-muted">
                        {r.vehicle.vehicle_type_display || r.vehicle.vehicle_type}
                        {r.vehicle.make_model ? ` · ${r.vehicle.make_model}` : ''}
                      </div>
                    )}
                  </div>
                  <div className="col-md-4 mb-2">
                    <label className="form-label text-muted small mb-1">Driver Name</label>
                    <div className="fw-semibold">
                      {r.driver ? r.driver.name : <span className="text-muted">—</span>}
                    </div>
                  </div>
                  <div className="col-md-4 mb-2">
                    <label className="form-label text-muted small mb-1">Cell Number</label>
                    <div className="fw-semibold">
                      {r.driver ? r.driver.cell_number : <span className="text-muted">—</span>}
                    </div>
                  </div>
                </div>
                {r.assigned_by && (
                  <div className="mt-2 small text-muted">
                    Assigned by {r.assigned_by}
                    {r.assigned_at ? ` on ${fmt(r.assigned_at)}` : ''}
                  </div>
                )}
              </div>
            ) : (
              <div className="mb-3 p-3 bg-light rounded text-muted">
                <i className="bi bi-clock me-1"></i> No vehicle or driver assigned yet
              </div>
            )}

            <hr />
            <div className="d-flex gap-2 flex-wrap">
              <Link to="/transport" className="btn btn-outline-secondary">
                <i className="bi bi-arrow-left me-1"></i> Back
              </Link>
              {canAct && stage?.can_assign && (
                <button type="button" className="btn btn-primary" onClick={() => setShowAssign(true)}>
                  <i className="bi bi-truck me-1"></i> Assign Vehicle &amp; Driver
                </button>
              )}
              {canAct && stage?.can_decline && (
                <button
                  type="button"
                  className="btn btn-outline-danger"
                  onClick={() => setShowDecline(true)}
                >
                  <i className="bi bi-x-lg me-1"></i> Decline
                </button>
              )}
              {showPlainApprove && (
                <button
                  type="button"
                  className="btn btn-success"
                  onClick={() => approveMutation.mutate({})}
                  disabled={approveMutation.isPending}
                >
                  <i className="bi bi-check-lg me-1"></i> Approve at {stage?.name}
                </button>
              )}
            </div>

            {showAmendForm && stage && (
              <div className="card mt-3 border-warning">
                <div className="card-header bg-warning bg-opacity-25">
                  <i className="bi bi-pencil-square me-1"></i>
                  <strong>{stage.name}</strong> — you may correct these before approving
                </div>
                <div className="card-body">
                  <div className="row g-3">
                    {amendable.map((field) => (
                      <div className="col-md-6" key={field.key}>
                        <label className="form-label" htmlFor={`amend-${field.key}`}>
                          {field.label}
                        </label>
                        {field.options.length > 0 ? (
                          <select
                            id={`amend-${field.key}`}
                            className="form-select form-select-sm"
                            value={
                              amendValues[field.key] ?? String(field.value ?? '')
                            }
                            onChange={(e) => onAmendChange(field.key, e.target.value)}
                          >
                            {field.options.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type={field.input_type}
                            id={`amend-${field.key}`}
                            className="form-control form-control-sm"
                            value={amendValues[field.key] ?? String(field.value ?? '')}
                            placeholder={field.placeholder}
                            onChange={(e) => onAmendChange(field.key, e.target.value)}
                          />
                        )}
                        <div className="form-text">Currently: {field.value ?? '—'}</div>
                      </div>
                    ))}
                    <div className="col-12">
                      <label className="form-label" htmlFor="grants-remarks">
                        Remarks (optional)
                      </label>
                      <textarea
                        name="remarks"
                        id="grants-remarks"
                        rows={2}
                        className="form-control form-control-sm"
                        placeholder="Why the codes were changed."
                        value={remarks}
                        onChange={(e) => setRemarks(e.target.value)}
                      />
                    </div>
                  </div>
                  {amendError && (
                    <div className="alert alert-danger py-2 mt-3 mb-0">
                      <i className="bi bi-exclamation-triangle me-1"></i>
                      {amendError}
                    </div>
                  )}
                  <button
                    type="button"
                    className="btn btn-success mt-3"
                    onClick={submitAmendApprove}
                    disabled={approveMutation.isPending}
                  >
                    <i className="bi bi-check-lg me-1"></i> Approve at {stage.name}
                  </button>
                  <div className="form-text mt-2">
                    Any value you change here is recorded in the audit log and shown to the
                    requester.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <ReasonModal
        open={showDecline}
        title={`Decline at ${stage?.name ?? 'this stage'}`}
        label="Reason"
        placeholder="What does the requester need to fix?"
        helpText="The requester is emailed this reason."
        confirmLabel="Decline"
        confirmClassName="btn-danger"
        required={!!stage?.require_reason_on_decline}
        onSubmit={async (reason) => {
          await declineMutation.mutateAsync(reason)
        }}
        onClose={() => setShowDecline(false)}
      />

      <AssignDriverModal
        open={showAssign}
        vehicles={act?.vehicles ?? []}
        drivers={act?.drivers ?? []}
        onSubmit={async (vehicleId, driverId) => {
          await assignMutation.mutateAsync({ vehicleId, driverId })
        }}
        onClose={() => setShowAssign(false)}
      />
    </div>
  )
}
