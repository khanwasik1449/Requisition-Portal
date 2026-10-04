import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'

interface Contract {
  id: number
  pin: string
  name: string
  designation: string
  new_designation?: string
  salary: number
  contract_type: string
  start_date: string
  end_date: string
}

function computeStatus(endDate: string): string {
  if (!endDate) return 'Active'
  const end = new Date(endDate)
  const now = new Date()
  const diff = (end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diff < 0) return 'Expired'
  if (diff <= 30) return 'Expiring'
  return 'Active'
}

function fmtDate(d: string) {
  if (!d) return '—'
  const [y, m, day] = d.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${day} ${months[parseInt(m, 10) - 1]} ${y}`
}

function fmtMoney(v: number) {
  if (!v && v !== 0) return '—'
  return '৳ ' + Number(v).toLocaleString('en-BD')
}

// Replica of contracts/templates/contracts/list.html
export function ContractsList() {
  const { data: contracts, isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: async () => {
      const response = await api.get<Contract[]>('/contracts/')
      return response.data
    },
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h2 className="page-title mb-1">Contracts dashboard</h2>
          <p className="text-muted mb-0 small">Manage and review all employee contracts</p>
        </div>
        <button className="btn btn-primary btn-sm">
          <i className="bi bi-plus-lg me-1"></i> New contract
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
                  <th>Designation</th>
                  <th>Salary</th>
                  <th>Type</th>
                  <th>Start date</th>
                  <th>End date</th>
                  <th>Status</th>
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
                ) : contracts?.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center text-muted py-4">
                      No contracts found.
                    </td>
                  </tr>
                ) : (
                  contracts?.map((c) => {
                    const status = computeStatus(c.end_date)
                    return (
                      <tr key={c.id}>
                        <td className="fw-semibold">{c.pin}</td>
                        <td>{c.name}</td>
                        <td>{c.designation || '—'}</td>
                        <td>{fmtMoney(c.salary)}</td>
                        <td>
                          <span className="badge bg-light text-dark border">
                            {c.contract_type}
                          </span>
                        </td>
                        <td>{fmtDate(c.start_date)}</td>
                        <td>{fmtDate(c.end_date)}</td>
                        <td>
                          <span
                            className={`badge ${
                              status === 'Active'
                                ? 'bg-success'
                                : status === 'Expiring'
                                  ? 'bg-warning text-dark'
                                  : 'bg-danger'
                            }`}
                          >
                            {status}
                          </span>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
