import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError } from '@/lib/flash'
import { getAllResults } from '@/lib/paginate'

interface Employee {
  id: number
  pin: string
  name: string
  designation: string
  gender: string | null
  tin: string | null
  phone: string | null
  email: string | null
  salary: number | string | null
}

interface Contract {
  id: number
  pin: string
  contract_type: string | null
  start_date: string
  end_date: string
  salary: number | string
  new_designation: string | null
  created_at: string
}

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/** `{{ emp.salary|floatformat:0 }}` -- rounded to an integer, no grouping. */
function fmtSalary(v: number | string | null | undefined) {
  if (v === null || v === undefined || v === '') return ''
  return String(Math.round(Number(v)))
}

/** `{{ contract.start_date|date:"M d, Y" }}` on a plain `YYYY-MM-DD`. */
function fmtDate(value: string | null | undefined) {
  if (!value) return ''
  const [y, m, d] = value.slice(0, 10).split('-')
  const month = MONTHS[Number(m) - 1]
  if (!month || !y || !d) return value
  return `${month} ${d}, ${y}`
}

/**
 * `{{ contract.created_at|date:"M d, Y" }}` -- settings.TIME_ZONE is
 * 'Africa/Nairobi' (UTC+3), so Django renders datetimes shifted before the
 * date part is taken.
 */
function fmtDateTime(value: string | null | undefined) {
  if (!value) return ''
  const shifted = new Date(new Date(value).getTime() + 3 * 60 * 60 * 1000)
  if (isNaN(shifted.getTime())) return value
  const month = MONTHS[shifted.getUTCMonth()]
  const day = String(shifted.getUTCDate()).padStart(2, '0')
  return `${month} ${day}, ${shifted.getUTCFullYear()}`
}

// employees/templates/employees/detail.html -- <style> block, verbatim.
const css = `
  :root {
    --c-bg: #F7F6F3;
    --c-surface: #FFFFFF;
    --c-border: rgba(0,0,0,0.08);
    --c-border-strong: rgba(0,0,0,0.15);
    --c-text: #1A1917;
    --c-muted: #6B6A66;
    --c-accent: #2563EB;
    --c-success: #16A34A;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  }

  @media (max-width: 768px) {
    .detail-wrapper { padding: 1rem !important; }
    .card-header { padding: 15px !important; }
    .card-body { padding: 15px !important; }
    .info-grid { grid-template-columns: repeat(2, 1fr) !important; gap: 15px !important; }
    .btn { width: 100%; justify-content: center; margin-bottom: 8px; }
    .contract-table { font-size: 12px; }
    .contract-table th, .contract-table td { padding: 8px !important; }
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--c-bg);
    color: var(--c-text);
  }

  .detail-wrapper {
    max-width: 900px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem;
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: #fff;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    color: var(--c-text);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 1.5rem;
    transition: all 0.2s;
  }

  .back-btn:hover {
    background: var(--c-bg);
    border-color: var(--c-accent);
    color: var(--c-accent);
  }

  .card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 1.5rem;
  }

  .card-header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--c-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .card-header h2 {
    font-size: 18px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .card-body {
    padding: 24px;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .info-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--c-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .info-value {
    font-size: 15px;
    font-weight: 500;
    color: var(--c-text);
  }

  .info-value.muted {
    color: var(--c-muted);
  }

  .section-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--c-accent);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .contract-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  .contract-table thead th {
    background: var(--c-bg);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    color: var(--c-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid var(--c-border-strong);
  }

  .contract-table tbody td {
    padding: 12px;
    border-bottom: 1px solid var(--c-border);
    color: var(--c-text);
  }

  .contract-table tbody tr:hover {
    background: var(--c-bg);
  }

  .badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .badge-new {
    background: #EFF6FF;
    color: #2563EB;
  }

  .badge-ext {
    background: #F0FDF4;
    color: #16A34A;
  }

  .badge-rev {
    background: #FFFBEB;
    color: #D97706;
  }

  .badge-ren {
    background: #FDF4FF;
    color: #7C3AED;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    border: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    transition: all 0.2s;
  }

  .btn-primary {
    background: var(--c-accent);
    color: #fff;
  }

  .btn-primary:hover {
    background: #1D4ED8;
  }

  .btn-danger {
    background: #DC2626;
    color: #fff;
  }

  .btn-danger:hover {
    background: #B91C1C;
  }

  .btn-pdf {
    background: #FEF2F2;
    color: #DC2626;
    padding: 6px 12px;
    font-size: 12px;
  }

  .btn-pdf:hover {
    background: #FEE2E2;
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--c-muted);
  }

  .empty-state-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }

  .actions {
    display: flex;
    gap: 10px;
    margin-top: 1.5rem;
  }

  .contract-count {
    background: var(--c-bg);
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    color: var(--c-accent);
  }
`

// Replica of employees/templates/employees/detail.html
export function EmployeeDetail() {
  const { pin } = useParams<{ pin: string }>()
  const [error, setError] = useState<string | null>(null)

  const { data: employee, error: employeeError } = useQuery({
    queryKey: ['employees', pin],
    queryFn: async () =>
      (await api.get<Employee>(`/employees/${encodeURIComponent(pin!)}/`)).data,
    enabled: Boolean(pin),
  })

  const { data: contracts, isLoading: contractsLoading } = useQuery({
    queryKey: ['contracts', 'employee', pin],
    queryFn: async () => {
      // Contract.objects.filter(pin=pin).order_by('-start_date') -- the search
      // param narrows the pages, the exact pin match keeps the queryset honest.
      const response = await getAllResults<Contract>('/contracts/', { q: pin })
      return response.results
        .filter((contract) => contract.pin === pin)
        .sort((a, b) =>
          a.start_date === b.start_date
            ? 0
            : a.start_date < b.start_date
              ? 1
              : -1,
        )
    },
    enabled: Boolean(pin),
  })

  useEffect(() => {
    if (employeeError) setError(flashFromError(employeeError).text)
  }, [employeeError])

  const contractList = contracts ?? []
  const count = contractList.length

  // contracts.views.generate_pdf returns an attachment, so the blob is handed
  // to a download link -- a plain <a href> could not carry the JWT.
  const downloadPdf = async (contract: Contract) => {
    try {
      const response = await api.get(`/contracts/${contract.id}/pdf/`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(
        new Blob([response.data], { type: 'application/pdf' }),
      )
      const link = document.createElement('a')
      link.href = url
      link.download = `contract_${contract.pin}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      // Delayed so the browser has grabbed the blob before it is revoked.
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (err) {
      setError(flashFromError(err).text)
    }
  }

  return (
    <>
      <PageStyle css={css} />

      {error && (
        <div className="app-message error">
          <span className="msg-close" onClick={() => setError(null)}>
            &times;
          </span>
          {error}
        </div>
      )}

      <div className="detail-wrapper">
        <Link to="/hr/employees" className="back-btn">
          ← Back to Employees
        </Link>

        {/* Employee Details Card */}
        <div className="card">
          <div className="card-header">
            <h2>👤 Employee Details</h2>
            <span className="contract-count">{count} Contracts</span>
          </div>
          <div className="card-body">
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">PIN</span>
                <span
                  className="info-value"
                  style={{
                    fontSize: '18px',
                    fontWeight: 600,
                    color: 'var(--c-accent)',
                  }}
                >
                  {employee?.pin}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">Full Name</span>
                <span className="info-value">{employee?.name}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Designation</span>
                <span className="info-value">{employee?.designation}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Gender</span>
                <span
                  className={`info-value${employee?.gender ? '' : ' muted'}`}
                >
                  {employee?.gender || 'Not specified'}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">TIN</span>
                <span className={`info-value${employee?.tin ? '' : ' muted'}`}>
                  {employee?.tin || 'Not provided'}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">Phone</span>
                <span
                  className={`info-value${employee?.phone ? '' : ' muted'}`}
                >
                  {employee?.phone || 'Not provided'}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">Email</span>
                <span
                  className={`info-value${employee?.email ? '' : ' muted'}`}
                >
                  {employee?.email || 'Not provided'}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">Salary</span>
                <span
                  className="info-value"
                  style={{ fontSize: '16px', fontWeight: 600 }}
                >
                  ৳ {fmtSalary(employee?.salary)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Contract History Card */}
        <div className="card">
          <div className="card-header">
            <h2>📄 Contract History</h2>
            <span className="contract-count">{count} Total</span>
          </div>
          <div className="card-body">
            {contractsLoading ? null : count > 0 ? (
              <table className="contract-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Salary</th>
                    <th>New Designation</th>
                    <th>Created</th>
                    <th>PDF</th>
                  </tr>
                </thead>
                <tbody>
                  {contractList.map((contract) => (
                    <tr key={contract.id}>
                      <td>
                        {contract.contract_type === 'New' && (
                          <span className="badge badge-new">New</span>
                        )}
                        {contract.contract_type === 'Extension' && (
                          <span className="badge badge-ext">Extension</span>
                        )}
                        {contract.contract_type === 'Revision' && (
                          <span className="badge badge-rev">Revision</span>
                        )}
                        {contract.contract_type === 'Renewal' && (
                          <span className="badge badge-ren">Renewal</span>
                        )}
                      </td>
                      <td>{fmtDate(contract.start_date)}</td>
                      <td>{fmtDate(contract.end_date)}</td>
                      <td>৳ {fmtSalary(contract.salary)}</td>
                      <td>
                        {contract.new_designation ? (
                          <span
                            style={{
                              color: 'var(--c-accent)',
                              fontWeight: 500,
                            }}
                          >
                            {contract.new_designation}
                          </span>
                        ) : (
                          <span
                            className="muted"
                            style={{ color: 'var(--c-muted)' }}
                          >
                            —
                          </span>
                        )}
                      </td>
                      <td style={{ color: 'var(--c-muted)', fontSize: '13px' }}>
                        {fmtDateTime(contract.created_at)}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-pdf"
                          onClick={() => downloadPdf(contract)}
                        >
                          📥 PDF
                        </button>
                        <Link
                          to={`/hr/contracts/email/${contract.id}`}
                          className="btn btn-email"
                          style={{
                            marginLeft: '4px',
                            background: '#EFF6FF',
                            color: '#2563EB',
                            padding: '6px 12px',
                            fontSize: '12px',
                            borderRadius: '4px',
                            textDecoration: 'none',
                          }}
                        >
                          📧 Email
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <p
                  style={{
                    fontSize: '15px',
                    fontWeight: 500,
                    marginBottom: '4px',
                  }}
                >
                  No contracts found
                </p>
                <p style={{ fontSize: '13px' }}>
                  {"This employee doesn't have any contracts yet."}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="actions">
          <Link
            to={`/hr/employees/edit/${employee?.pin ?? pin}`}
            className="btn btn-primary"
          >
            ✏️ Edit Employee
          </Link>
          <Link
            to={`/hr/employees/delete/${employee?.pin ?? pin}`}
            className="btn btn-danger"
          >
            🗑️ Delete Employee
          </Link>
        </div>
      </div>
    </>
  )
}
