import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/hooks'
import { ReminderButton, useReminder } from '@/components/ReminderButton'
import { getAllResults } from '@/lib/paginate'
import { formatDateDMY } from '@/lib/utils'

interface ICTRequisition {
  id: number
  request_number: string
  full_name: string
  designation: string
  requisition_date: string
  status: string
  status_display?: string
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'pending_first')
    return (
      <span className="badge bg-warning">
        <i className="bi bi-hourglass-split me-1"></i>Pending 1st
      </span>
    )
  if (status === 'pending_second')
    return (
      <span className="badge bg-info">
        <i className="bi bi-hourglass-split me-1"></i>Pending 2nd
      </span>
    )
  if (status === 'approved')
    return (
      <span className="badge bg-success">
        <i className="bi bi-check-circle me-1"></i>Approved
      </span>
    )
  if (status === 'rejected')
    return (
      <span className="badge bg-danger">
        <i className="bi bi-x-circle me-1"></i>Rejected
      </span>
    )
  return <span className="badge bg-secondary">{status}</span>
}

// Exact replica of templates/ict_requisition/list.html
export function ICTList() {
  const { data, isLoading } = useQuery({
    queryKey: ['ict'],
    queryFn: async () => {
      return getAllResults<ICTRequisition>('/ict/')
    },
  })
  const { user } = useAuth()
  const { notice, busyId, send } = useReminder()

  // main gates the reminder button on `user.is_admin or user.is_ict_admin` and
  // on the requisition sitting at one of the two pending stages.
  const isReminderActor = !!user && (user.role === 'admin' || user.role === 'ict_admin')
  const canRemind = (status: string) =>
    isReminderActor && (status === 'pending_first' || status === 'pending_second')

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">ICT Requisitions</h2>
          <p className="text-muted mb-0 small">Manage ICT equipment and device requests</p>
        </div>
        <Link to="/ict/create" className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> New Request
        </Link>
      </div>

      {notice && (
        <div className={`alert alert-${notice.level} py-2 small`} role="alert">
          {notice.text}
        </div>
      )}

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Device/Equipment</th>
                  <th>Designation</th>
                  <th>Req Date</th>
                  <th>Status</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : data?.results.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-5">
                      <i className="bi bi-inbox" style={{ fontSize: '2.5rem', color: '#cbd5e1' }}></i>
                      <p className="text-muted mt-2 mb-0">No ICT requisitions found.</p>
                      <Link to="/ict/create" className="btn btn-primary mt-2">
                        Create One
                      </Link>
                    </td>
                  </tr>
                ) : (
                  data?.results.map((r) => (
                    <tr key={r.id}>
                      <td className="fw-semibold">{r.request_number}</td>
                      <td>{r.full_name}</td>
                      <td>—</td>
                      <td>{r.designation}</td>
                      <td className="text-muted small">{formatDateDMY(r.requisition_date)}</td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="text-end">
                        <div className="d-flex gap-1 justify-content-end">
                          <Link
                            to={`/ict/${r.id}`}
                            className="btn btn-sm btn-outline-secondary"
                            title="View"
                          >
                            <i className="bi bi-eye"></i>
                          </Link>
                          {canRemind(r.status) && (
                            <ReminderButton
                              reqType="ict"
                              id={r.id}
                              busy={busyId === r.id}
                              onClick={() => send('ict', r.id)}
                            />
                          )}
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
