import { useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { PageStyle } from '@/components/PageStyle'
import { useAuth } from '@/auth/hooks'
import { setFlash } from '@/lib/flash'
import { getAllResults } from '@/lib/paginate'

interface PayslipRequest {
  id: number
  name: string
  pin: string
  months: string
  year: string
  created_at: string
}

// payslip/templates/payslip/requests_list.html -- <style> block, verbatim.
const css = `
    .req-table { width:100%; border-collapse:collapse; font-size:13px; }
    .req-table th, .req-table td { padding:10px 14px; text-align:left; border-bottom:1px solid #e2e8f0; }
    .req-table th { background:#f8fafc; font-size:11px; font-weight:600; text-transform:uppercase; color:#64748b; }
    .req-table tbody tr:hover { background:#f8fafc; }
`

const MONTH_ABBR = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/** `{{ r.created_at|date:"M d, Y h:i A" }}` -- e.g. "Oct 07, 2026 03:15 PM". */
function fmtSubmitted(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const hour24 = date.getHours()
  const hour12 = ((hour24 - 1) % 12) + 1
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(hour12).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ampm = hour24 < 12 ? 'AM' : 'PM'
  return `${MONTH_ABBR[date.getMonth()]} ${dd}, ${date.getFullYear()} ${hh}:${mm} ${ampm}`
}

// Replica of payslip/templates/payslip/requests_list.html
export function PayslipRequestsList() {
  const { user } = useAuth()

  // payslip.views.payslip_requests: `if not request.user.is_hr_admin()` ->
  // messages.error('Access denied. HR admin only.') + redirect to the
  // contracts dashboard.
  const isHrAdmin = user?.role === 'admin' || user?.role === 'hr_admin'

  const { data: requests, isLoading, isError } = useQuery({
    queryKey: ['payslip-requests'],
    queryFn: async () => {
      return getAllResults<PayslipRequest>('/payslip-requests/')
    },
    enabled: isHrAdmin,
  })

  if (!isHrAdmin) {
    setFlash('error', 'Access denied. HR admin only.')
    return <Navigate to="/hr/contracts" replace />
  }

  const rows = requests?.results ?? []

  return (
    <>
      <PageStyle css={css} />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}
      >
        <div>
          <h4 style={{ margin: 0, fontWeight: 600 }}>Payslip Requests</h4>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#64748b' }}>
            {rows.length} request(s) submitted
          </p>
        </div>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      ) : isError ? (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
          Could not load payslip requests.
        </div>
      ) : rows.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="req-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>PIN</th>
                <th>Months</th>
                <th>Year</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, index) => (
                <tr key={r.id}>
                  {/* forloop.revcounter -- counted down from the total */}
                  <td className="text-muted">{rows.length - index}</td>
                  <td className="fw-semibold">{r.name}</td>
                  <td style={{ fontFamily: 'monospace' }}>{r.pin}</td>
                  <td>{r.months}</td>
                  <td>{r.year}</td>
                  <td className="text-muted small">{fmtSubmitted(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>📭</div>
          <h5 style={{ fontWeight: 600, marginBottom: '6px' }}>No requests yet</h5>
          <p style={{ fontSize: '13px' }}>
            Payslip requests submitted from the public home page will appear here.
          </p>
        </div>
      )}
    </>
  )
}
