import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api, endpoints } from '@/api/axios'
import { useAuth } from '@/auth/hooks'
import { useStaffDefaults } from '@/lib/staffDefaults'

/**
 * BRAC University email request.
 *
 * `main` has no such form at all -- `public_home.html` links out to a Google
 * Form -- so this page is new rather than a port. It pre-fills the signed-in
 * employee's details the way the requisition forms do, and e-mails the request
 * to the internal team on submit.
 *
 * The fields are controlled state seeded from `useStaffDefaults` once that
 * query resolves, rather than `defaultValue` props: the employee lookup is
 * asynchronous, and a `defaultValue` is only read on mount, so seeding state
 * afterwards is what actually puts the PIN on screen.
 */

interface FormState {
  full_name: string
  email_address: string
  pin_number: string
  designation: string
  department: string
  phone: string
  requested_email: string
  reason: string
}

const EMPTY: FormState = {
  full_name: '',
  email_address: '',
  pin_number: '',
  designation: '',
  department: '',
  phone: '',
  requested_email: '',
  reason: '',
}

export function BuEmailRequest() {
  const { user } = useAuth()
  const staff = useStaffDefaults()
  const [form, setForm] = useState<FormState | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  // Seed once the pre-fill lookup resolves. Guarded on `form` being null so a
  // later update can never overwrite what the applicant has typed.
  useEffect(() => {
    if (staff.loading) return
    setForm((prev) => prev ?? {
      full_name: staff.full_name,
      email_address: staff.email_address,
      pin_number: staff.pin_number,
      designation: staff.designation,
      department: '',
      phone: staff.mobile_number,
      requested_email: '',
      reason: '',
    })
  }, [staff])

  // The admin runs the mail flow rather than requesting an address from it,
  // so this form is for everyone else — same rule as the Requisitions menu.
  if (user && user.role === 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  // `form` stays null until the lookup has resolved, so this doubles as the
  // loading state.
  if (!form) {
    return (
      <div className="d-flex justify-content-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  const set = (key: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => setForm((prev) => (prev ? { ...prev, [key]: e.target.value } : prev))

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post(endpoints.buEmailRequest(), form)
      setDone(true)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail
      setError(detail || 'Failed to submit the request.')
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="row justify-content-center">
        <div className="col-lg-8">
          <div className="card">
            <div className="card-body text-center py-5">
              <i
                className="bi bi-check-circle text-success"
                style={{ fontSize: '3rem' }}
              ></i>
              <h4 className="mt-3 mb-2">Request Submitted</h4>
              <p className="text-muted mb-4">
                Your request for a BRAC University email address has been sent to
                the internal team. You will be contacted at{' '}
                <strong>{form.email_address}</strong> once it is processed.
              </p>
              <Link to="/dashboard" className="btn btn-primary">
                <i className="bi bi-speedometer2 me-1"></i> Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card">
          <div className="card-header d-flex align-items-center gap-2">
            <i className="bi bi-envelope-paper" style={{ color: '#2563eb' }}></i>
            BRAC University Email Request
          </div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="alert alert-danger py-2 small">{error}</div>
              )}

              <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
                <i className="bi bi-person me-1"></i> Personal Information
              </h6>
              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label">
                    Full Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="full_name"
                    className="form-control"
                    placeholder="Your full name"
                    value={form.full_name}
                    onChange={set('full_name')}
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">
                    Current Email Address <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    name="email_address"
                    className="form-control"
                    placeholder="email@example.com"
                    value={form.email_address}
                    onChange={set('email_address')}
                    required
                  />
                </div>
              </div>
              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label">PIN Number</label>
                  <input
                    type="text"
                    name="pin_number"
                    className="form-control"
                    placeholder="Staff PIN number"
                    value={form.pin_number}
                    onChange={set('pin_number')}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Designation</label>
                  <input
                    type="text"
                    name="designation"
                    className="form-control"
                    placeholder="e.g. Software Engineer"
                    value={form.designation}
                    onChange={set('designation')}
                  />
                </div>
              </div>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label className="form-label">Department</label>
                  <input
                    type="text"
                    name="department"
                    className="form-control"
                    placeholder="e.g. IT"
                    value={form.department}
                    onChange={set('department')}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Phone</label>
                  <input
                    type="text"
                    name="phone"
                    className="form-control"
                    placeholder="e.g. +254 7XX XXX XXX"
                    value={form.phone}
                    onChange={set('phone')}
                  />
                </div>
              </div>

              <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
                <i className="bi bi-envelope-at me-1"></i> Email Address
              </h6>
              <div className="row mb-4">
                <div className="col-md-6">
                  <label className="form-label">
                    Requested @bracu.ac.bd Address{' '}
                    <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="requested_email"
                    className="form-control"
                    placeholder="firstname.lastname@bracu.ac.bd"
                    value={form.requested_email}
                    onChange={set('requested_email')}
                    required
                  />
                  <small className="text-muted">
                    BRAC University addresses are issued as
                    firstname.lastname@bracu.ac.bd.
                  </small>
                </div>
              </div>

              <div className="mb-4">
                <label className="form-label">Reason for Request</label>
                <textarea
                  name="reason"
                  className="form-control"
                  rows={3}
                  placeholder="Why do you need this address?"
                  value={form.reason}
                  onChange={set('reason')}
                />
              </div>

              <hr />
              <div className="d-flex gap-2">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={busy}
                >
                  <i className="bi bi-send me-1"></i>{' '}
                  {busy ? 'Submitting...' : 'Submit Request'}
                </button>
                <Link to="/dashboard" className="btn btn-outline-secondary">
                  <i className="bi bi-x me-1"></i> Cancel
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
