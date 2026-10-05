import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'

// Payslip is a flat row keyed by PIN -- it has no relations at all.
// `month` and `year` are strings, not numbers.
interface Payslip {
  id: number
  pin: string
  name: string
  designation: string
  month: string
  year: string
  basic_salary: string
  gross_salary: string
  net_salary: string
}

function fmtMoney(v: string | number | null | undefined) {
  if (v === null || v === undefined || v === '') return '—'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })
}

// Replica of payslip/templates/payslip/list.html
export function PayslipList() {
  const { data: payslips, isLoading, isError } = useQuery({
    queryKey: ['payslips'],
    queryFn: async () => {
      const response = await api.get<{ results: Payslip[] }>('/payslips/')
      return response.data
    },
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h2 className="page-title mb-1">Payslip List</h2>
          <p className="text-muted mb-0 small">Manage and generate payslips</p>
        </div>
        <button className="btn btn-success btn-sm">
          <i className="bi bi-plus-lg me-1"></i> Create New Payslip
        </button>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>PIN</th>
                  <th>Name</th>
                  <th>Designation</th>
                  <th>Month</th>
                  <th>Year</th>
                  <th>Basic</th>
                  <th>Gross</th>
                  <th>Net</th>
                  <th className="text-end">PDF</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={9} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : isError ? (
                  <tr>
                    <td colSpan={9} className="text-center text-danger py-4">
                      Could not load payslips.
                    </td>
                  </tr>
                ) : payslips?.results.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center text-muted py-4">
                      No payslips found.
                    </td>
                  </tr>
                ) : (
                  payslips?.results.map((p) => (
                    <tr key={p.id}>
                      <td className="fw-semibold">{p.pin}</td>
                      <td>{p.name}</td>
                      <td>{p.designation || '—'}</td>
                      <td>{p.month}</td>
                      <td>{p.year}</td>
                      <td>{fmtMoney(p.basic_salary)}</td>
                      <td>
                        <strong>{fmtMoney(p.gross_salary)}</strong>
                      </td>
                      <td>
                        <strong>{fmtMoney(p.net_salary)}</strong>
                      </td>
                      <td className="text-end">
                        <button className="btn btn-sm btn-primary">Download</button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
