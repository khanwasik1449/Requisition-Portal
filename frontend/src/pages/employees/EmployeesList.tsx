import { useQuery } from '@tanstack/react-query'
import { getAllResults } from '@/lib/paginate'

// Employee has no FK to User or Contract -- it is keyed by PIN, and the
// contract history counts are computed server-side against that PIN.
interface Employee {
  id: number
  pin: string
  name: string
  designation: string
  phone: string
  email: string
  salary: number | null
  project: string
  branch: string
  new_count: number
  extension_count: number
  revision_count: number
  renewal_count: number
}

function fmtMoney(v: number | null) {
  if (v === null || v === undefined) return '—'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

// Replica of employees/templates/employees/list.html
export function EmployeesList() {
  const { data: employees, isLoading, isError } = useQuery({
    queryKey: ['employees'],
    queryFn: async () => {
      return getAllResults<Employee>('/employees/')
    },
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h2 className="page-title mb-1">Employees</h2>
          <p className="text-muted mb-0 small">Manage employee records</p>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-success btn-sm">
            <i className="bi bi-plus-lg me-1"></i> Add Employee
          </button>
          <button className="btn btn-secondary btn-sm">
            <i className="bi bi-upload me-1"></i> Import CSV
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>PIN</th>
                  <th>Name</th>
                  <th>Designation</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Salary</th>
                  <th>Contract History</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : isError ? (
                  <tr>
                    <td colSpan={8} className="text-center text-danger py-4">
                      Could not load employees.
                    </td>
                  </tr>
                ) : employees?.results.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center text-muted py-5">
                      No employees found. Add or import employees.
                    </td>
                  </tr>
                ) : (
                  employees?.results.map((e) => (
                    <tr key={e.id}>
                      <td className="fw-semibold">
                        <a href={`/employees`} className="text-decoration-none">
                          {e.pin}
                        </a>
                      </td>
                      <td>{e.name}</td>
                      <td>{e.designation || '—'}</td>
                      <td>{e.phone || '—'}</td>
                      <td>{e.email || '—'}</td>
                      <td>{fmtMoney(e.salary)}</td>
                      <td>
                        <span className="badge bg-light text-dark border me-1">
                          New: {e.new_count}
                        </span>
                        <span className="badge bg-light text-dark border me-1">
                          Ext: {e.extension_count}
                        </span>
                        <span className="badge bg-light text-dark border me-1">
                          Rev: {e.revision_count}
                        </span>
                        <span className="badge bg-light text-dark border">Ren: {e.renewal_count}</span>
                      </td>
                      <td className="text-end">
                        <div className="d-flex gap-1 justify-content-end">
                          <button className="btn btn-sm btn-outline-primary" title="Edit">
                            <i className="bi bi-pencil"></i>
                          </button>
                          <button className="btn btn-sm btn-outline-danger" title="Delete">
                            <i className="bi bi-trash"></i>
                          </button>
                        </div>
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
