import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, endpoints } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { apiErrorMessages } from '@/lib/utils'

// templates/accounts/signup.html -- <style> block, verbatim, with two
// deviations: `body`'s declarations live on the wrapper below (the SPA cannot
// restyle the document per route), and the stray `margin: 0 auto 16px; } }`
// after `.brand-icon img` (lines 39-41 of the template) is omitted -- it is
// invalid CSS that browsers discard anyway.
const signupCss = `
    * { box-sizing: border-box; }
    .card {
        border: none;
        border-radius: 20px;
        box-shadow: 0 25px 60px rgba(0,0,0,.3);
        padding: 40px;
        width: 480px;
        max-width: 100%;
        background: #fff;
    }
    .brand-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 16px;
    }
    .brand-icon img {
        height: auto;
        max-height: 56px;
        width: auto;
    }
    h3 { font-weight: 700; color: #0f172a; }
    .form-control, .form-select {
        border-radius: 10px;
        border: 1.5px solid #e2e8f0;
        padding: 11px 14px;
        font-size: .875rem;
        transition: all .15s ease;
    }
    .form-control:focus, .form-select:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 3px rgba(37,99,235,.12);
    }
    .form-label { font-weight: 600; font-size: .8rem; color: #0f172a; }
    .btn-primary {
        background: #2563eb;
        border: none;
        padding: 12px;
        border-radius: 10px;
        font-weight: 600;
    }
    .btn-primary:hover { background: #1d4ed8; transform: translateY(-1px); }
    .divider { border-top: 1px solid #e2e8f0; margin: 24px 0; }
`

// templates/accounts/pending_approval.html -- <style> block, verbatim, except
// for `body`, which becomes the wrapper's declarations below.
const pendingCss = `
    .card {
        border: none;
        border-radius: 20px;
        box-shadow: 0 25px 60px rgba(0,0,0,.3);
        padding: 48px;
        width: 460px;
        max-width: 100%;
        background: #fff;
        text-align: center;
    }
    .icon { font-size: 4rem; margin-bottom: 16px; }
    h3 { font-weight: 700; color: #0f172a; }
`

// accounts.views.signup -- a standalone public page (no @login_required) that
// serves signup.html until the POST succeeds, then pending_approval.html.
export function Signup() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password1, setPassword1] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      // The template's role field is disabled, so main's form posts no `role`
      // and the view falls back to User.Role.REQUESTER -- reproduced here by
      // always sending 'requester'.
      await api.post(endpoints.signup(), {
        username,
        password1,
        password2,
        email,
        phone,
        role: 'requester',
      })
      setDone(true)
    } catch (err) {
      const data = (err as { response?: { data?: unknown } }).response?.data
      setError(apiErrorMessages(data, 'Unable to create account. Please try again.')[0])
    } finally {
      setIsSubmitting(false)
    }
  }

  if (done) {
    // templates/accounts/pending_approval.html
    return (
      <>
        <PageStyle css={pendingCss} />

        <div
          style={{
            background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
          }}
        >
          <div className="card">
            <div className="icon">⏳</div>
            <h3>Account Pending Approval</h3>
            <p className="text-muted mt-3">
              Your account has been created and is awaiting approval by an administrator. You
              will be notified once your account is activated.
            </p>
            <Link to="/login" className="btn btn-primary mt-3 px-4">
              Back to Login
            </Link>
          </div>
        </div>
      </>
    )
  }

  // templates/accounts/signup.html
  return (
    <>
      <PageStyle css={signupCss} />

      <div
        style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
          padding: '20px',
        }}
      >
        <div className="card">
          <div className="text-center mb-4">
            <div className="brand-icon">
              <img
                src="http://bracied.com/wp-content/uploads/2025/10/BRAC-IED-Color_PNG.png"
                alt="BRAC IED"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
            <h3>Create Account</h3>
            <p className="text-muted small">Register for a new account</p>
          </div>

          {error && (
            <div className="alert alert-danger py-2 small">
              <i className="bi bi-exclamation-circle me-1"></i> {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label">
                  Username <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  name="username"
                  className="form-control"
                  placeholder="Choose a username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
              <div className="col-md-6 mb-3">
                <label className="form-label">Email</label>
                <input
                  type="email"
                  name="email"
                  className="form-control"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label">Phone</label>
                <input
                  type="text"
                  name="phone"
                  className="form-control"
                  placeholder="+254 7XX XXX XXX"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
              <div className="col-md-6 mb-3">
                <label className="form-label">Role</label>
                <input type="text" className="form-control" defaultValue="requester" disabled />
              </div>
            </div>
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label">
                  Password <span className="text-danger">*</span>
                </label>
                <input
                  type="password"
                  name="password1"
                  className="form-control"
                  placeholder="Create a password"
                  required
                  value={password1}
                  onChange={(e) => setPassword1(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
              <div className="col-md-6 mb-3">
                <label className="form-label">
                  Confirm Password <span className="text-danger">*</span>
                </label>
                <input
                  type="password"
                  name="password2"
                  className="form-control"
                  placeholder="Confirm password"
                  required
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
            <div className="alert alert-info py-2 small">
              <i className="bi bi-info-circle me-1"></i>{' '}
              After registration, an administrator must approve your account before you can log
              in.
            </div>
            <button type="submit" className="btn btn-primary w-100" disabled={isSubmitting}>
              <i className="bi bi-person-plus me-1"></i> Create Account
            </button>
          </form>

          <div className="divider"></div>
          <p className="text-center mb-0 text-muted small">
            Already have an account?{' '}
            <Link to="/login" className="fw-semibold">
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </>
  )
}
