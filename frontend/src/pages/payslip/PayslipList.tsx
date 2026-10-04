import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'

interface Payslip {
  id: number
  employee_name: string
  pin: string
  month: number
  year: number
  basic_salary: number
  status: string
}

const monthNames = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export function PayslipList() {
  const { data: payslips, isLoading } = useQuery({
    queryKey: ['payslips'],
    queryFn: async () => {
      const response = await api.get<{ results: Payslip[] }>('/payslips/')
      return response.data
    },
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Payslips</h2>
          <p className="text-muted mb-0 small">Manage and generate payslips</p>
        </div>
        <button className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> Generate Payslip
        </button>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>PIN</th>
                  <th>Employee</th>
                  <th>Period</th>
                  <th>Basic Salary</th>
                  <th>Status</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : payslips?.results.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center text-muted py-4">
                      No payslips found.
                    </td>
                  </tr>
                ) : (
                  payslips?.results.map((p) => (
                    <tr key={p.id}>
                      <td className="fw-semibold">{p.pin}</td>
                      <td>{p.employee_name}</td>
                      <td>
                        {monthNames[p.month - 1]} {p.year}
                      </td>
                      <td>৳ {p.basic_salary?.toLocaleString()}</td>
                      <td>
                        <span
                          className={`badge ${
                            p.status === 'paid' ? 'bg-success' : 'bg-warning text-dark'
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                      <td className="text-end">
                        <button className="btn btn-sm btn-outline-secondary" title="View">
                          <i className="bi bi-eye"></i>
                        </button>
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
