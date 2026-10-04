import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'

interface Employee {
  id: number
  full_name: string
  email: string
  designation: string
  department: string
  pin: string
}

export function EmployeesList() {
  const { data: employees, isLoading } = useQuery({
    queryKey: ['employees'],
    queryFn: async () => {
      const response = await api.get<{ results: Employee[] }>('/employees/')
      return response.data
    },
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Employees</h2>
          <p className="text-muted mb-0 small">Manage employee records</p>
        </div>
        <button className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> Add Employee
        </button>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>PIN</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Designation</th>
                  <th>Department</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : employees?.results.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-muted py-4">
                      No employees found.
                    </td>
                  </tr>
                ) : (
                  employees?.results.map((e) => (
                    <tr key={e.id}>
                      <td className="fw-semibold">{e.pin}</td>
                      <td>{e.full_name}</td>
                      <td>{e.email}</td>
                      <td>{e.designation}</td>
                      <td>
                        <span className="badge bg-light text-dark border">{e.department}</span>
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
