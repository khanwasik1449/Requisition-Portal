import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, endpoints } from '@/api/axios'

/**
 * `/notifications/action/<token>/` -- the page the Approve / Reject links in
 * an approval email open.
 *
 * main's `email_action_view` applies an approval on the GET that opens the link
 * and renders one of three standalone templates (action_error,
 * action_success, reject_reason). The React page resolves on GET and applies on
 * POST, exactly once, so reloading the link can never approve the same
 * requisition twice -- the visible result is the same card main would show.
 */

type ActionState =
  | { kind: 'loading' }
  | { kind: 'login_required'; next: string }
  | { kind: 'error'; error: string }
  | { kind: 'approve-ready'; message: string; token: string }
  | {
      kind: 'reject-form'
      requestNumber: string
      message: string
      token: string
      portalUrl: string
    }
  | { kind: 'success'; message: string }

export function EmailAction() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState<ActionState>({ kind: 'loading' })
  const [reason, setReason] = useState('')
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const applied = useRef(false)

  useEffect(() => {
    let cancelled = false

    api
      .get(endpoints.notificationAction(token))
      .then(({ data }) => {
        if (cancelled) return

        if (data.kind === 'login_required') {
          // main redirects to LOGIN_URL?next=...; the React page makes the
          // same jump, back to its own path for the same token.
          navigate(`/login?next=${encodeURIComponent(data.next)}`, { replace: true })
          return
        }

        if (data.kind === 'approve-ready') {
          if (applied.current) return
          applied.current = true
          api
            .post(endpoints.notificationAction(token))
            .then(({ data: done }) => {
              if (!cancelled) setState({ kind: 'success', message: done.message })
            })
            .catch(() => {
              if (!cancelled) {
                setState({
                  kind: 'error',
                  error: 'The approval could not be applied.',
                })
              }
            })
          return
        }

        if (data.kind === 'reject-form') {
          setState({
            kind: 'reject-form',
            requestNumber: data.requisition.request_number,
            message: data.message,
            token,
            portalUrl: data.portal_url,
          })
          return
        }

        setState(data)
      })
      .catch(() => {
        if (!cancelled) {
          setState({ kind: 'error', error: 'The link could not be read.' })
        }
      })

    return () => {
      cancelled = true
    }
  }, [token, navigate])

  const submitReject = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setBusy(true)
    try {
      const { data } = await api.post(endpoints.notificationAction(token), {
        reason,
      })
      setState({ kind: 'success', message: data.message })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail
      setFormError(detail || 'The rejection could not be applied.')
    } finally {
      setBusy(false)
    }
  }

  if (state.kind === 'loading') {
    return (
      <div
        className="d-flex align-items-center justify-content-center vh-100 bg-light"
        style={{ minHeight: '100vh' }}
      >
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  if (state.kind === 'error') {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100 bg-light">
        <div className="card shadow-sm" style={{ maxWidth: '450px', width: '100%' }}>
          <div className="card-body text-center py-5">
            <div className="mb-3" style={{ fontSize: '3rem' }}>
              ⚠️
            </div>
            <h5 className="text-danger">Action Failed</h5>
            <p className="text-muted mb-0">{state.error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (state.kind === 'success') {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100 bg-light">
        <div className="card shadow-sm" style={{ maxWidth: '450px', width: '100%' }}>
          <div className="card-body text-center py-5">
            <div className="mb-3" style={{ fontSize: '3rem' }}>
              ✅
            </div>
            <h5 className="text-success">Done</h5>
            <p className="text-muted mb-0">{state.message}</p>
          </div>
        </div>
      </div>
    )
  }

  if (state.kind === 'reject-form') {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100 bg-light">
        <div className="card shadow-sm" style={{ maxWidth: '500px', width: '100%' }}>
          <div className="card-body p-4">
            <h5 className="mb-3">Reject Requisition {state.requestNumber}</h5>
            <p className="text-muted small mb-3">
              Please provide a reason for rejecting this requisition.
            </p>
            {formError && (
              <div className="alert alert-danger py-2 small" role="alert">
                {formError}
              </div>
            )}
            <form onSubmit={submitReject}>
              <div className="mb-3">
                <textarea
                  name="reason"
                  className="form-control"
                  rows={4}
                  placeholder="Reason for rejection..."
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="d-flex gap-2">
                <button type="submit" className="btn btn-danger" disabled={busy}>
                  Reject
                </button>
                <Link to={state.portalUrl} className="btn btn-outline-secondary">
                  Go to Portal
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    )
  }

  // approve-ready: the POST is in flight, so hold the loading screen rather
  // than flashing the form.
  return (
    <div
      className="d-flex align-items-center justify-content-center vh-100 bg-light"
      style={{ minHeight: '100vh' }}
    >
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  )
}
