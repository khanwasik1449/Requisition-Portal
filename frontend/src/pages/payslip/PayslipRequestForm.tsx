import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError } from '@/lib/flash'

// payslip/views.request_payslip builds these two lists on every GET.
const MONTHS_LIST = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const currentYear = new Date().getFullYear()
// views: range(current_year - 2, current_year + 3)
const YEARS = [
  currentYear - 2,
  currentYear - 1,
  currentYear,
  currentYear + 1,
  currentYear + 2,
]

// payslip/templates/payslip/request_form.html -- <style> block, verbatim
// except for `body`: the SPA cannot restyle the document per route, so those
// declarations live on the full-height wrapper below instead.
const css = `
  .container { max-width: 500px; }
  .card {
      border: none;
      border-radius: 16px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.15);
      padding: 40px 32px;
      background: #fff;
  }
  .card h3 { font-weight: 700; color: #1e293b; }
  .card p { color: #64748b; font-size: .9rem; }
  .form-control {
      border-radius: 10px;
      border: 1.5px solid #e2e8f0;
      padding: 12px 14px;
      font-size: .9rem;
  }
  .form-control:focus {
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102,126,234,.12);
  }
  .form-label { font-weight: 600; font-size: .85rem; color: #1e293b; }
  .btn-primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      border-radius: 10px;
      padding: 12px;
      font-weight: 600;
  }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(102,126,234,.3); }
  .back-link { color: #000; text-decoration: none; font-size: .85rem; }
  .back-link:hover { color: #333; }
`

// payslip/templates/payslip/request_form.html -- a standalone public document
// (no base template, no @login_required), so it renders its own full-height
// gradient page rather than inside HrLayout.
export function PayslipRequestForm() {
  const [name, setName] = useState('')
  const [pin, setPin] = useState('')
  const [selectedMonths, setSelectedMonths] = useState<string[]>([])
  const [year, setYear] = useState(String(currentYear))
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const toggleMonth = (month: string) => {
    setSelectedMonths((prev) =>
      prev.includes(month) ? prev.filter((m) => m !== month) : [...prev, month],
    )
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    // main joins the checked checkboxes in the order they appear in the form
    // (`Array.from(...checked).map(c => c.value).join(', ')`).
    const months = MONTHS_LIST.filter((m) => selectedMonths.includes(m)).join(', ')

    try {
      await api.post('/payslip-requests/', { name, pin, months, year })
      // request_payslip redirects back to this same URL with a Django message
      // above an empty form -- so the alert lands inline, no navigation.
      setMessage('Your payslip request has been submitted successfully!')
      setName('')
      setPin('')
      setSelectedMonths([])
      setYear(String(currentYear))
    } catch (err) {
      setError(flashFromError(err).text)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <PageStyle css={css} />

      <div
        style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        <div className="container">
          <Link to="/" className="back-link mb-3 d-inline-block">
            ← Back to Home
          </Link>
          <div className="card">
            <div className="text-center mb-1" style={{ fontSize: '2.5rem' }}>
              💰
            </div>
            <h3 className="text-center">Payslip Request</h3>
            <p className="text-center mb-4">Submit your details to request a payslip</p>

            {message && <div className="alert alert-success py-2 small">{message}</div>}
            {/* request_form.html has no failure path -- a rejected POST would
                be a server error -- so the sentence uses Bootstrap's danger
                alert in the same slot the Django message renders in. */}
            {error && <div className="alert alert-danger py-2 small">{error}</div>}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  name="name"
                  className="form-control"
                  placeholder="Enter your full name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="mb-3">
                <label className="form-label">PIN</label>
                <input
                  type="text"
                  name="pin"
                  className="form-control"
                  placeholder="e.g. EMP-2024-001"
                  required
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                />
              </div>
              <div className="mb-4">
                <label className="form-label">
                  Months <small className="text-muted">(select one or more)</small>
                </label>
                <div className="row g-2" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  {MONTHS_LIST.map((m, index) => (
                    <div className="col-6" key={m}>
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          name="selected_months"
                          value={m}
                          id={`month_${index + 1}`}
                          checked={selectedMonths.includes(m)}
                          onChange={() => toggleMonth(m)}
                        />
                        <label className="form-check-label" htmlFor={`month_${index + 1}`}>
                          {m}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mb-4">
                <label className="form-label">Year</label>
                <select
                  name="year"
                  className="form-select"
                  required
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                >
                  {YEARS.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn-primary w-100" disabled={isSubmitting}>
                Submit Request
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  )
}
