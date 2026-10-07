import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { getAllResults } from '@/lib/paginate'

// Payslip is a flat row keyed by PIN -- it has no relations at all.
// `month` and `year` are strings, not numbers; the Decimal columns come back
// as strings, exactly what `{{ payslip.basic_salary }}` prints in main.
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

// Download through axios so the JWT is attached -- a plain <a href> cannot
// carry the Authorization header.
async function downloadPayslipPdf(p: Payslip): Promise<void> {
  const response = await api.get(`/payslips/${p.id}/pdf/`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `payslip_${p.pin}_${p.month}_${p.year}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

// Replica of payslip/templates/payslip/list.html
export function PayslipList() {
  const { data: payslips, isLoading, isError } = useQuery({
    queryKey: ['payslips'],
    queryFn: async () => {
      return getAllResults<Payslip>('/payslips/')
    },
  })

  const rows = payslips?.results ?? []

  return (
    <div className="card-box">
      <h4 className="mb-4">Payslip List</h4>

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
            <th>PDF</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td colSpan={9} className="text-center">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              </td>
            </tr>
          ) : isError ? (
            <tr>
              <td colSpan={9} className="text-center text-danger">
                Could not load payslips.
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={9} className="text-center">
                No payslips found.
              </td>
            </tr>
          ) : (
            rows.map((p) => (
              <tr key={p.id}>
                <td>{p.pin}</td>
                <td>{p.name}</td>
                <td>{p.designation}</td>
                <td>{p.month}</td>
                <td>{p.year}</td>
                <td>{p.basic_salary}</td>
                <td>
                  <strong>{p.gross_salary}</strong>
                </td>
                <td>
                  <strong>{p.net_salary}</strong>
                </td>
                <td>
                  <a
                    href={`/api/payslips/${p.id}/pdf/`}
                    className="btn btn-sm btn-primary"
                    onClick={(e) => {
                      e.preventDefault()
                      void downloadPayslipPdf(p)
                    }}
                  >
                    Download
                  </a>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <Link to="/hr/payslip" className="btn btn-success">
        Create New Payslip
      </Link>
    </div>
  )
}
