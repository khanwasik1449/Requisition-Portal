import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { ReasonModal, apiErrorMessage } from '@/components/workflow/WorkflowModals'
import { formatDateDMY, formatStamp, formatTimeHM } from '@/lib/utils'

interface Alt {
  room_id: number
  date: string
  start_time: string
  end_time: string
}

interface BookingDetail {
  id: number
  meeting_title: string
  status: string
  status_display?: string
  date: string
  start_time: string
  end_time: string
  number_of_participants: number
  requirements?: string
  cancellation_reason?: string
  cancelled_by_name?: string | null
  cancelled_at?: string | null
  alternatives?: Alt[]
  // Nested exactly as booking_detail.html reads them (b.user / b.room).
  user?: { id: number; username: string; first_name: string; last_name: string; email: string }
  room?: { id: number; room_number: string; floor: string; max_occupancy: number }
}

interface BookingActions {
  can_view: boolean
  is_owner: boolean
  is_hr_admin: boolean
  can_approve: boolean
  can_decline: boolean
  can_suggest_alternatives: boolean
  can_cancel: boolean
  can_review_alternatives: boolean
}

// Django's `date:"M d, Y H:i"` — shared so every detail page stamps identically.
const fmt = formatStamp

/** The dynamic "room + date + slot" rows from booking_suggest_alternatives.html. */
function SuggestModal({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (alternatives: Alt[]) => Promise<void>
}) {
  const [rows, setRows] = useState<Alt[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const { data: rooms } = useQuery({
    queryKey: ['rooms'],
    enabled: open,
    queryFn: async () => {
      const res = await api.get<{
        count?: number
        results?: Array<{ id: number; room_number: string; floor: string }>
      }>('/rooms/')
      const payload = res.data
      return payload.results ?? (payload as unknown as Array<{ id: number; room_number: string; floor: string }>)
    },
  })

  useEffect(() => {
    if (open) {
      setRows([
        { room_id: 0, date: '', start_time: '', end_time: '' },
      ])
      setError('')
      setBusy(false)
    }
  }, [open])

  if (!open) return null

  const update = (i: number, patch: Partial<Alt>) =>
    setRows((prev) => prev.map((row, idx) => (idx === i ? { ...row, ...patch } : row)))

  const submit = async () => {
    const filled = rows.filter((r) => r.room_id && r.date && r.start_time && r.end_time)
    if (!filled.length) {
      setError('Add at least one alternative slot.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await onSubmit(filled)
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="modal fade show d-block" tabIndex={-1}>
        <div className="modal-dialog modal-lg modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">
                <i className="bi bi-shuffle me-2"></i>Suggest Alternatives
              </h5>
              <button type="button" className="btn-close" onClick={onClose}></button>
            </div>
            <div className="modal-body">
              <p className="text-muted small">
                Offer the requester different rooms or slots instead of a flat rejection.
              </p>
              {rows.map((row, i) => (
                <div className="row g-2 align-items-end mb-2" key={i}>
                  <div className="col-md-4">
                    <label className="form-label small mb-1">Room</label>
                    <select
                      className="form-select form-select-sm"
                      value={row.room_id || ''}
                      onChange={(e) => update(i, { room_id: Number(e.target.value) })}
                    >
                      <option value="">Choose...</option>
                      {rooms?.map((rm) => (
                        <option key={rm.id} value={rm.id}>
                          Room {rm.room_number} (Floor {rm.floor})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-3">
                    <label className="form-label small mb-1">Date</label>
                    <input
                      type="date"
                      className="form-control form-control-sm"
                      value={row.date}
                      onChange={(e) => update(i, { date: e.target.value })}
                    />
                  </div>
                  <div className="col-md-2">
                    <label className="form-label small mb-1">Start</label>
                    <input
                      type="time"
                      className="form-control form-control-sm"
                      value={row.start_time}
                      onChange={(e) => update(i, { start_time: e.target.value })}
                    />
                  </div>
                  <div className="col-md-2">
                    <label className="form-label small mb-1">End</label>
                    <input
                      type="time"
                      className="form-control form-control-sm"
                      value={row.end_time}
                      onChange={(e) => update(i, { end_time: e.target.value })}
                    />
                  </div>
                  <div className="col-md-1">
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-sm w-100"
                      disabled={rows.length === 1}
                      onClick={() => setRows((prev) => prev.filter((_, idx) => idx !== i))}
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                </div>
              ))}
              <button
                type="button"
                className="btn btn-outline-primary btn-sm"
                onClick={() =>
                  setRows((prev) => [
                    ...prev,
                    { room_id: 0, date: '', start_time: '', end_time: '' },
                  ])
                }
              >
                <i className="bi bi-plus-lg me-1"></i> Add option
              </button>
              {error && (
                <div className="alert alert-danger py-2 mt-3 mb-0">
                  <i className="bi bi-exclamation-triangle me-1"></i>
                  {error}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="button" className="btn btn-info" onClick={submit} disabled={busy}>
                {busy ? (
                  <span className="spinner-border spinner-border-sm me-1"></span>
                ) : (
                  <i className="bi bi-shuffle me-1"></i>
                )}
                Send alternatives
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show"></div>
    </>
  )
}

/** The requester's "Review them" screen, as a modal instead of a separate page. */
function AlternativesModal({
  open,
  alternatives,
  rooms,
  onClose,
  onAccept,
  onDeclineAll,
}: {
  open: boolean
  alternatives: Alt[]
  rooms: Array<{ id: number; room_number: string; floor: string }>
  onClose: () => void
  onAccept: (index: number) => Promise<void>
  onDeclineAll: () => Promise<void>
}) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setError('')
      setBusy(false)
    }
  }, [open])

  if (!open) return null

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    setError('')
    try {
      await fn()
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const roomLabel = (id: number) => {
    const rm = rooms?.find((x) => x.id === id)
    return rm ? `Room ${rm.room_number} (Floor ${rm.floor})` : `Room #${id}`
  }

  return (
    <>
      <div className="modal fade show d-block" tabIndex={-1}>
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">
                <i className="bi bi-diagram-3 me-2"></i>Alternative Slots Offered
              </h5>
              <button type="button" className="btn-close" onClick={onClose}></button>
            </div>
            <div className="modal-body">
              <p className="text-muted small">
                The HR admin could not accommodate your original request. Pick one of these
                options, or decline them all.
              </p>
              {alternatives.map((alt, i) => (
                <div
                  className="border rounded p-3 mb-2 d-flex justify-content-between align-items-center"
                  key={i}
                >
                  <div>
                    <div className="fw-semibold">{roomLabel(alt.room_id)}</div>
                    <div className="small text-muted">
                      {alt.date} · {alt.start_time}-{alt.end_time}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-success btn-sm"
                    disabled={busy}
                    onClick={() => run(() => onAccept(i))}
                  >
                    <i className="bi bi-check-lg me-1"></i> Accept
                  </button>
                </div>
              ))}
              {error && (
                <div className="alert alert-danger py-2 mt-2 mb-0">
                  <i className="bi bi-exclamation-triangle me-1"></i>
                  {error}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
                Close
              </button>
              <button
                type="button"
                className="btn btn-outline-danger"
                disabled={busy}
                onClick={() => run(onDeclineAll)}
              >
                Decline all alternatives
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show"></div>
    </>
  )
}

// Exact replica of meetspace/templates/meetspace/booking_detail.html
export function MeetSpaceDetail() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [showReject, setShowReject] = useState(false)
  const [showCancel, setShowCancel] = useState(false)
  const [showSuggest, setShowSuggest] = useState(false)
  const [showAlternatives, setShowAlternatives] = useState(false)
  const [approveError, setApproveError] = useState('')

  const { data: b, isLoading } = useQuery({
    queryKey: ['meetspace', id],
    queryFn: async () => {
      const response = await api.get<BookingDetail>(`/meetspace/${id}/`)
      return response.data
    },
  })

  const { data: act } = useQuery({
    queryKey: ['meetspace-actions', id],
    queryFn: async () => {
      const response = await api.get<BookingActions>(`/meetspace/${id}/actions/`)
      return response.data
    },
  })

  const { data: rooms } = useQuery({
    queryKey: ['rooms'],
    queryFn: async () => {
      const res = await api.get<{
        count?: number
        results?: Array<{ id: number; room_number: string; floor: string }>
      }>('/rooms/')
      const payload = res.data
      return payload.results ??
        (payload as unknown as Array<{ id: number; room_number: string; floor: string }>)
    },
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['meetspace', id] })
    queryClient.invalidateQueries({ queryKey: ['meetspace'] })
    queryClient.invalidateQueries({ queryKey: ['meetspace-actions', id] })
  }

  const approveMutation = useMutation({
    mutationFn: () => api.post(`/meetspace/${id}/approve/`, {}),
    onSuccess: refresh,
  })
  const rejectMutation = useMutation({
    mutationFn: (reason: string) => api.post(`/meetspace/${id}/decline/`, { reason }),
    onSuccess: refresh,
  })
  const cancelMutation = useMutation({
    mutationFn: (reason: string) => api.post(`/meetspace/${id}/cancel/`, { reason }),
    onSuccess: refresh,
  })
  const suggestMutation = useMutation({
    mutationFn: (alternatives: Alt[]) =>
      api.post(`/meetspace/${id}/suggest_alternative/`, { alternatives }),
    onSuccess: refresh,
  })
  const acceptMutation = useMutation({
    mutationFn: (alternative_index: number) =>
      api.post(`/meetspace/${id}/accept_alternative/`, { alternative_index }),
    onSuccess: refresh,
  })
  const declineAltsMutation = useMutation({
    mutationFn: () => api.post(`/meetspace/${id}/reject_alternatives/`, {}),
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

  if (!b) return <p className="text-muted">Booking not found.</p>

  const statusBadgeClass =
    b.status === 'approved'
      ? 'bg-success'
      : b.status === 'pending'
        ? 'bg-warning text-dark'
        : b.status === 'rejected' || b.status === 'cancelled'
          ? 'bg-danger'
          : 'bg-info'

  const ownerName = b.user
    ? [b.user.first_name, b.user.last_name].filter(Boolean).join(' ') || b.user.username
    : ''
  const alternatives = b.alternatives ?? []

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card">
          <div className="card-header d-flex align-items-center justify-content-between">
            <span>
              <i className="bi bi-calendar3 me-1"></i>
              {b.meeting_title}
            </span>
            <span className={`badge ${statusBadgeClass}`}>
              {b.status_display || b.status}
            </span>
          </div>
          <div className="card-body">
            <div className="row g-3 mb-3">
              <div className="col-md-6">
                <label className="form-label text-muted small">Requester</label>
                <div className="fw-semibold">{ownerName || '—'}</div>
              </div>
              <div className="col-md-6">
                <label className="form-label text-muted small">Room</label>
                <div className="fw-semibold">
                  Room {b.room?.room_number ?? '—'}
                  {b.room?.floor ? ` (Floor ${b.room.floor})` : ''}
                </div>
              </div>
              <div className="col-md-4">
                <label className="form-label text-muted small">Date</label>
                <div>{formatDateDMY(b.date)}</div>
              </div>
              <div className="col-md-4">
                <label className="form-label text-muted small">Time</label>
                <div>
                  {formatTimeHM(b.start_time)} – {formatTimeHM(b.end_time)}
                </div>
              </div>
              <div className="col-md-4">
                <label className="form-label text-muted small">Participants</label>
                <div>{b.number_of_participants}</div>
              </div>
              {b.requirements && (
                <div className="col-12">
                  <label className="form-label text-muted small">Requirements</label>
                  <div className="bg-light rounded p-2">{b.requirements}</div>
                </div>
              )}
            </div>

            {b.status === 'alternatives' && act?.is_owner && (
              <div className="alert alert-info">
                <i className="bi bi-info-circle me-1"></i>
                The HR admin offered alternative slots.{' '}
                <a
                  href="#review"
                  onClick={(e) => {
                    e.preventDefault()
                    setShowAlternatives(true)
                  }}
                >
                  Review them
                </a>
                .
              </div>
            )}

            {b.cancellation_reason && (
              <div className="alert alert-danger">
                <strong>Reason:</strong> {b.cancellation_reason}
                {(b.cancelled_by_name || b.cancelled_at) && (
                  <div className="small mb-0">
                    by {b.cancelled_by_name || '—'}
                    {b.cancelled_at ? ` on ${fmt(b.cancelled_at)}` : ''}
                  </div>
                )}
              </div>
            )}

            <hr />
            <div className="d-flex flex-wrap gap-2">
              <Link to="/meetspace" className="btn btn-outline-secondary">
                <i className="bi bi-arrow-left me-1"></i> Back
              </Link>

              {act?.can_approve && (
                <button
                  type="button"
                  className="btn btn-success"
                  disabled={approveMutation.isPending}
                  onClick={async () => {
                    setApproveError('')
                    try {
                      await approveMutation.mutateAsync()
                    } catch (err) {
                      setApproveError(apiErrorMessage(err))
                    }
                  }}
                >
                  <i className="bi bi-check-lg me-1"></i> Approve
                </button>
              )}
              {act?.can_suggest_alternatives && (
                <button
                  type="button"
                  className="btn btn-info"
                  onClick={() => setShowSuggest(true)}
                >
                  <i className="bi bi-shuffle me-1"></i> Suggest alternatives
                </button>
              )}
              {act?.can_decline && (
                <button
                  type="button"
                  className="btn btn-outline-danger"
                  onClick={() => setShowReject(true)}
                >
                  <i className="bi bi-x-lg me-1"></i> Reject
                </button>
              )}
              {act?.can_cancel && (
                <button
                  type="button"
                  className="btn btn-outline-danger"
                  onClick={() => setShowCancel(true)}
                >
                  <i className="bi bi-x-circle me-1"></i> Cancel
                </button>
              )}

              {approveError && (
                <div className="w-100 alert alert-danger py-2 mb-0">
                  <i className="bi bi-exclamation-triangle me-1"></i>
                  {approveError}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <ReasonModal
        open={showReject}
        title="Reject Booking"
        label="Reason"
        placeholder="Why can't this slot be accommodated?"
        helpText="The requester is emailed this reason."
        confirmLabel="Reject"
        confirmClassName="btn-outline-danger"
        onSubmit={async (reason) => {
          await rejectMutation.mutateAsync(reason)
        }}
        onClose={() => setShowReject(false)}
      />

      <ReasonModal
        open={showCancel}
        title="Cancel Booking"
        label="Cancellation reason"
        placeholder="Why is this booking being cancelled?"
        confirmLabel="Cancel booking"
        confirmClassName="btn-danger"
        onSubmit={async (reason) => {
          await cancelMutation.mutateAsync(reason)
        }}
        onClose={() => setShowCancel(false)}
      />

      <SuggestModal
        open={showSuggest}
        onSubmit={async (alternatives) => {
          await suggestMutation.mutateAsync(alternatives)
        }}
        onClose={() => setShowSuggest(false)}
      />

      <AlternativesModal
        open={showAlternatives}
        alternatives={alternatives}
        rooms={rooms ?? []}
        onAccept={async (index) => {
          await acceptMutation.mutateAsync(index)
        }}
        onDeclineAll={async () => {
          await declineAltsMutation.mutateAsync()
        }}
        onClose={() => setShowAlternatives(false)}
      />
    </div>
  )
}
