import { useEffect, useState } from 'react'

/** Pull the sentence the API returns for a failed workflow decision. */
export function apiErrorMessage(error: unknown): string {
  const data = (error as { response?: { data?: { error?: string; detail?: string } } })
    ?.response?.data
  return data?.error || data?.detail || 'Something went wrong. Please try again.'
}

/**
 * Bootstrap modal driven purely by React state.
 *
 * The app deliberately does not hand modal toggling to Bootstrap's JS (the same
 * reason the Requisitions dropdown is React state): React Router navigation and
 * outside-click handling both need to own that state.
 */
function ModalShell({
  open,
  title,
  titleIcon,
  onClose,
  children,
}: {
  open: boolean
  title: string
  titleIcon?: string
  onClose: () => void
  children: React.ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <>
      <div className="modal fade show d-block" tabIndex={-1} role="dialog" aria-modal="true">
        <div
          className="modal-dialog modal-dialog-centered"
          onClick={(e) => {
            if (e.target === e.currentTarget) onClose()
          }}
        >
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title">
                {titleIcon && <i className={`${titleIcon} me-2`}></i>}
                {title}
              </h5>
              <button
                type="button"
                className="btn-close"
                aria-label="Close"
                onClick={onClose}
              ></button>
            </div>
            {children}
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show"></div>
    </>
  )
}

interface ReasonModalProps {
  open: boolean
  title: string
  label?: string
  placeholder?: string
  helpText?: string
  confirmLabel: string
  confirmClassName?: string
  /** main's reject forms refuse an empty reason; cancellation behaves the same. */
  required?: boolean
  onSubmit: (reason: string) => Promise<void> | void
  onClose: () => void
}

/** The reject / decline / cancel reason form, as a modal over the detail page. */
export function ReasonModal({
  open,
  title,
  label = 'Reason',
  placeholder,
  helpText,
  confirmLabel,
  confirmClassName = 'btn-danger',
  required = true,
  onSubmit,
  onClose,
}: ReasonModalProps) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setReason('')
      setError('')
      setBusy(false)
    }
  }, [open])

  const submit = async () => {
    if (required && !reason.trim()) {
      setError('Please give a reason so the requester knows what to fix.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await onSubmit(reason.trim())
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell open={open} title={title} titleIcon="bi bi-x-lg" onClose={onClose}>
      <div className="modal-body">
        <label className="form-label" htmlFor="reason-modal-input">
          {label}
          {required && <span className="text-danger ms-1">*</span>}
        </label>
        <textarea
          id="reason-modal-input"
          className="form-control"
          rows={3}
          value={reason}
          placeholder={placeholder}
          onChange={(e) => setReason(e.target.value)}
          autoFocus
        />
        {helpText && <div className="form-text">{helpText}</div>}
        {error && (
          <div className="alert alert-danger py-2 mt-2 mb-0">
            <i className="bi bi-exclamation-triangle me-1"></i>
            {error}
          </div>
        )}
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className={`btn ${confirmClassName}`}
          onClick={submit}
          disabled={busy}
        >
          {busy ? (
            <>
              <span className="spinner-border spinner-border-sm me-1" role="status"></span>
              Saving...
            </>
          ) : (
            confirmLabel
          )}
        </button>
      </div>
    </ModalShell>
  )
}

interface AssignDriverModalProps {
  open: boolean
  vehicles: Array<{
    id: number
    registration_number: string
    vehicle_type_display?: string
    make_model?: string
  }>
  drivers: Array<{ id: number; name: string; cell_number?: string }>
  onSubmit: (vehicleId: number, driverId: number) => Promise<void> | void
  onClose: () => void
}

/**
 * The vehicle + driver pick lists from ``assign_driver.html`` — same two
 * required selects, same "choose both" validation message.
 */
export function AssignDriverModal({
  open,
  vehicles,
  drivers,
  onSubmit,
  onClose,
}: AssignDriverModalProps) {
  const [vehicleId, setVehicleId] = useState('')
  const [driverId, setDriverId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setVehicleId('')
      setDriverId('')
      setError('')
      setBusy(false)
    }
  }, [open])

  const submit = async () => {
    if (!vehicleId || !driverId) {
      setError('Choose both a vehicle and a driver.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await onSubmit(Number(vehicleId), Number(driverId))
      onClose()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell
      open={open}
      title="Assign Vehicle & Driver"
      titleIcon="bi bi-truck"
      onClose={onClose}
    >
      <div className="modal-body">
        <div className="mb-3">
          <label className="form-label" htmlFor="assign-vehicle">
            Vehicle
          </label>
          <select
            id="assign-vehicle"
            className="form-select"
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
          >
            <option value="">Choose a vehicle...</option>
            {vehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.registration_number}
                {v.vehicle_type_display ? ` — ${v.vehicle_type_display}` : ''}
                {v.make_model ? ` · ${v.make_model}` : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="mb-2">
          <label className="form-label" htmlFor="assign-driver">
            Driver
          </label>
          <select
            id="assign-driver"
            className="form-select"
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
          >
            <option value="">Choose a driver...</option>
            {drivers.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
                {d.cell_number ? ` — ${d.cell_number}` : ''}
              </option>
            ))}
          </select>
        </div>
        {error && (
          <div className="alert alert-danger py-2 mt-2 mb-0">
            <i className="bi bi-exclamation-triangle me-1"></i>
            {error}
          </div>
        )}
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={submit}
          disabled={busy}
        >
          {busy ? (
            <>
              <span className="spinner-border spinner-border-sm me-1" role="status"></span>
              Assigning...
            </>
          ) : (
            <>
              <i className="bi bi-truck me-1"></i> Assign
            </>
          )}
        </button>
      </div>
    </ModalShell>
  )
}
