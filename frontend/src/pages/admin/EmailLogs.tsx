import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'

interface EmailLog {
  id: number
  department: string
  department_display: string
  email_type: string
  email_type_display: string
  req_type: string
  req_id: number | null
  recipient: string
  subject: string
  status: string
  error_message: string
  created_at: string
}

interface EmailLogResponse {
  count: number
  failed_count: number
  results: EmailLog[]
}

/** `M d H:i`, matching `{{ log.created_at|date:"M d H:i" }}`. */
function fmtTime(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${months[d.getMonth()]} ${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Replica of templates/notifications/email_logs.html
export function EmailLogs() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['emailLogs'],
    queryFn: async () => {
      const response = await api.get<EmailLogResponse>('/email-logs/')
      return response.data
    },
  })

  const retryMutation = useMutation({
    mutationFn: (id: number) => api.post(`/email-logs/${id}/retry/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['emailLogs'] }),
  })

  const retryAllMutation = useMutation({
    mutationFn: () => api.post('/email-logs/retry_all/'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['emailLogs'] }),
  })

  const failedCount = data?.failed_count ?? 0
  const results = data?.results || []

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Email Logs</h2>
          <p className="text-muted mb-0 small">
            {failedCount > 0 && (
              <>
                <span className="text-danger">{failedCount} failed</span> —{' '}
              </>
            )}
            Last 100 emails
          </p>
        </div>
        {failedCount > 0 && (
          <button
            className="btn btn-warning"
            disabled={retryAllMutation.isPending}
            onClick={() => {
              if (window.confirm(`Retry all ${failedCount} failed emails?`)) {
                retryAllMutation.mutate()
              }
            }}
          >
            <i className="bi bi-arrow-repeat me-1"></i> Retry All Failed
          </button>
        )}
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Dept</th>
                  <th>Type</th>
                  <th>Requisition</th>
                  <th>Recipient</th>
                  <th>Subject</th>
                  <th>Status</th>
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
                      Could not load email logs.
                    </td>
                  </tr>
                ) : results.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-4 text-muted">
                      No email logs yet.
                    </td>
                  </tr>
                ) : (
                  results.map((log) => (
                    <tr key={log.id}>
                      <td className="small text-muted">{fmtTime(log.created_at)}</td>
                      <td>
                        <span className="badge bg-light text-dark border">
                          {log.department_display}
                        </span>
                      </td>
                      <td>
                        <span className="small">{log.email_type_display}</span>
                      </td>
                      <td>{log.req_id ? `#${log.req_id}` : '—'}</td>
                      <td>{log.recipient}</td>
                      <td
                        className="small"
                        style={{
                          maxWidth: 250,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {log.subject}
                      </td>
                      <td>
                        {log.status === 'success' ? (
                          <span className="badge bg-success">Sent</span>
                        ) : (
                          <span className="badge bg-danger" title={log.error_message}>
                            Failed
                          </span>
                        )}
                      </td>
                      <td className="text-end">
                        {log.status === 'failed' && log.email_type === 'approval_request' && (
                          <button
                            className="btn btn-sm btn-outline-warning"
                            title="Retry"
                            disabled={retryMutation.isPending}
                            onClick={() => retryMutation.mutate(log.id)}
                          >
                            <i className="bi bi-arrow-repeat"></i>
                          </button>
                        )}
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
