import { useQuery } from '@tanstack/react-query'
import { getAllResults } from '@/lib/paginate'

interface AuditLogRow {
  id: number
  req_type: string
  req_type_display: string
  req_id: number
  request_number: string
  action: string
  action_display: string
  /** Null for public submissions and system actions -- page falls back to "System". */
  performed_by_display: string | null
  details: string
  created_at: string
}

// The colours from templates/notifications/audit_log.html, keyed on `action`.
const actionColors: Record<string, { background: string; color: string }> = {
  created: { background: '#e0f2fe', color: '#075985' },
  pending_first: { background: '#fef3c7', color: '#92400e' },
  pending_second: { background: '#fef3c7', color: '#92400e' },
  pending_grants: { background: '#fef3c7', color: '#92400e' },
  pending_transport: { background: '#fef3c7', color: '#92400e' },
  approved: { background: '#dcfce7', color: '#166534' },
  assigned: { background: '#dcfce7', color: '#166534' },
  rejected: { background: '#fee2e2', color: '#991b1b' },
}

/** `d M Y H:i`, matching `{{ log.created_at|date:"d M Y H:i" }}`. */
function fmtDateTime(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getDate())} ${months[d.getMonth()]} ${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Replica of templates/notifications/audit_log.html
export function AuditLog() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['auditLogs'],
    queryFn: async () => {
      return getAllResults<AuditLogRow>('/audit-logs/')
    },
  })

  const results = data?.results || []

  return (
    <>
      <style>{`
        .audit-table { width:100%; border-collapse:collapse; font-size:.85rem; }
        .audit-table th { text-align:left; padding:12px 14px; font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); border-bottom:2px solid var(--border); background:#f8fafc; }
        .audit-table td { padding:14px; border-bottom:1px solid #f1f5f9; vertical-align:middle; }
        .audit-table tr:hover { background:#f8fafc; }
        .action-badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:.7rem; font-weight:600; }
        .empty-state { text-align:center; padding:60px 20px; color:var(--muted); }
        .empty-state .icon { font-size:3rem; margin-bottom:16px; }
        @media(max-width:768px){
            .audit-table, .audit-table thead, .audit-table tbody, .audit-table tr, .audit-table th, .audit-table td { display:block; }
            .audit-table thead { display:none; }
            .audit-table tr { padding:14px; margin-bottom:12px; border:1px solid var(--border); border-radius:12px; background:#fff; }
            .audit-table td { padding:6px 0; border:none; display:flex; justify-content:space-between; gap:8px; }
            .audit-table td::before { content:attr(data-label); font-weight:600; color:var(--muted); font-size:.75rem; text-transform:uppercase; }
        }
      `}</style>

      {isLoading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      ) : isError ? (
        <div className="alert alert-danger">Could not load the audit log.</div>
      ) : results.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="audit-table">
            <thead>
              <tr>
                <th>Date/Time</th>
                <th>Type</th>
                <th>Request #</th>
                <th>Action</th>
                <th>Performed By</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {results.map((log) => (
                <tr key={log.id}>
                  <td data-label="Date/Time">{fmtDateTime(log.created_at)}</td>
                  <td data-label="Type">{log.req_type_display}</td>
                  <td data-label="Request #">
                    <strong>{log.request_number}</strong>
                  </td>
                  <td data-label="Action">
                    <span className="action-badge" style={actionColors[log.action]}>
                      {log.action_display}
                    </span>
                  </td>
                  <td data-label="By">{log.performed_by_display || 'System'}</td>
                  <td data-label="Details">{log.details || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <div className="icon">📜</div>
          <h5 style={{ fontWeight: 600 }}>No activity yet</h5>
          <p style={{ color: 'var(--muted)' }}>No audit log entries found.</p>
        </div>
      )}
    </>
  )
}
