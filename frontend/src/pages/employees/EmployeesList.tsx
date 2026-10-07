import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { PageStyle } from '@/components/PageStyle'
import { getAllResults } from '@/lib/paginate'

// Employee has no FK to User or Contract -- it is keyed by PIN, and the
// contract history counts are computed server-side against that PIN.
interface Employee {
  id: number
  pin: string
  name: string
  designation: string
  phone: string | null
  email: string | null
  salary: number | string | null
  project: string
  branch: string
  new_count: number
  extension_count: number
  revision_count: number
  renewal_count: number
}

/** `{{ emp.salary|floatformat:0 }}` -- rounded to an integer, no grouping. */
function fmtSalary(v: number | string | null | undefined) {
  if (v === null || v === undefined || v === '') return ''
  return String(Math.round(Number(v)))
}

// employees/templates/employees/list.html -- <style> block, verbatim.
const css = `
  @media (max-width: 768px) {
    .emp-table { font-size: 12px; }
    .emp-table th, .emp-table td { padding: 6px !important; }
    .contract-history { display: flex; flex-wrap: wrap; gap: 3px; }
    .btn { padding: 5px 10px; font-size: 12px; }
    .card-box { padding: 15px !important; }
    h4 { font-size: 18px; }
    div[style*="display: flex"] { flex-direction: column; gap: 10px; }
  }

  .emp-table { width: 100%; border-collapse: collapse; }
  .emp-table th, .emp-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
  .emp-table th { background: #f0f0f0; }
  .btn { padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 13px; margin-right: 5px; }
  .btn-edit { background: #2563EB; color: white; }
  .btn-delete { background: #DC2626; color: white; }
  .btn-add { background: #16A34A; color: white; padding: 8px 16px; border-radius: 6px; }
  .contract-history { font-size: 12px; color: #666; }
  .contract-badge { padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 3px; }
  .badge-new { background: #EFF6FF; color: #2563EB; }
  .badge-ext { background: #EFF6FF; color: #2563EB; }
  .badge-rev { background: #FFFBEB; color: #D97706; }
  .badge-ren { background: #F0FDF4; color: #16A34A; }
`

// Replica of employees/templates/employees/list.html
export function EmployeesList() {
  const { data: employees, isLoading, isError } = useQuery({
    queryKey: ['employees'],
    queryFn: async () => {
      return getAllResults<Employee>('/employees/')
    },
  })

  const rows = employees?.results ?? []

  return (
    <>
      <PageStyle css={css} />

      <div className="card-box">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
          }}
        >
          <h4>Employees</h4>
          <div style={{ display: 'flex', gap: '10px' }}>
            <Link to="/hr/employees/add" className="btn-add">
              Add Employee
            </Link>
            <Link
              to="/hr/employees/import"
              className="btn-add"
              style={{ background: '#6B7280' }}
            >
              Import CSV
            </Link>
          </div>
        </div>

        <table className="emp-table">
          <thead>
            <tr>
              <th>PIN</th>
              <th>Name</th>
              <th>Designation</th>
              <th>Phone</th>
              <th>Email</th>
              <th>Salary</th>
              <th>Contract History</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center' }}>
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center' }} className="text-danger">
                  Could not load employees.
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center' }}>
                  No employees found. Add or import employees.
                </td>
              </tr>
            ) : (
              rows.map((emp) => (
                <tr key={emp.id}>
                  <td>
                    <Link
                      to={`/hr/employees/detail/${emp.pin}`}
                      style={{
                        color: '#2563EB',
                        textDecoration: 'none',
                        fontWeight: 500,
                      }}
                    >
                      {emp.pin}
                    </Link>
                  </td>
                  <td>{emp.name}</td>
                  <td>{emp.designation}</td>
                  <td>{emp.phone || '-'}</td>
                  <td>{emp.email || '-'}</td>
                  <td>{fmtSalary(emp.salary)}</td>
                  <td className="contract-history">
                    <span className="contract-badge badge-new">
                      New: {emp.new_count}
                    </span>
                    <span className="contract-badge badge-ext">
                      Ext: {emp.extension_count}
                    </span>
                    <span className="contract-badge badge-rev">
                      Rev: {emp.revision_count}
                    </span>
                    <span className="contract-badge badge-ren">
                      Ren: {emp.renewal_count}
                    </span>
                  </td>
                  <td>
                    <Link
                      to={`/hr/employees/edit/${emp.pin}`}
                      className="btn btn-edit"
                    >
                      Edit
                    </Link>
                    <Link
                      to={`/hr/employees/delete/${emp.pin}`}
                      className="btn btn-delete"
                    >
                      Delete
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
