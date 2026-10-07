import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'

interface EmailLogRow {
  id: number
  contract: number | null
  recipient_email: string
  recipient_name: string
  subject: string
  status: string
  error_message: string
  batch_id: string
  sent_at: string
}

interface EmailLogResponse {
  count: number
  results: EmailLogRow[]
}

/**
 * email_log.html prints `{{ log.sent_at|date:"d/m/Y H:i" }}`, and Django renders
 * a date filter in the active timezone -- Africa/Nairobi for this install.
 */
function fmtLogDate(iso: string): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Africa/Nairobi',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('day')}/${get('month')}/${get('year')} ${get('hour')}:${get('minute')}`
}

// contracts/templates/contracts/email_log.html -- <style> block, verbatim.
const css = `
  .log-wrap {
    max-width: 1000px;
    margin: 0 auto;
  }
  .log-wrap h2 {
    margin-bottom: 16px;
  }
  .log-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .log-table th {
    background: #F8FAFC;
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid #E2E8F0;
    font-weight: 600;
    color: #475569;
    white-space: nowrap;
  }
  .log-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #F1F5F9;
    vertical-align: top;
  }
  .log-table tr:hover td {
    background: #FAFBFC;
  }
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
  }
  .badge.sent { background: #F0FDF4; color: #16A34A; }
  .badge.failed { background: #FEF2F2; color: #EF4444; }
  .empty {
    text-align: center;
    padding: 48px;
    color: #94A3B8;
  }
  .error-msg {
    font-size: 11px;
    color: #EF4444;
    max-width: 250px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`

// Replica of contracts/templates/contracts/email_log.html
export function HrEmailLog() {
  const logQuery = useQuery({
    queryKey: ['contracts', 'email-log'],
    queryFn: async () => (await api.get<EmailLogResponse>('/contracts/email-log/')).data,
  })

  const logs = logQuery.data?.results ?? []

  return (
    <>
      <PageStyle css={css} />

      <div className="log-wrap">
        <h2>📧 Email Log</h2>

        {logQuery.isLoading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : logs.length > 0 ? (
          <>
            <div style={{ overflowX: 'auto' }}>
              <table className="log-table">
                <thead>
                  <tr>
                    <th>Date &amp; Time</th>
                    <th>Recipient</th>
                    <th>Name</th>
                    <th>Subject</th>
                    <th>Status</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>{fmtLogDate(log.sent_at)}</td>
                      <td>{log.recipient_email || '—'}</td>
                      <td>{log.recipient_name || '—'}</td>
                      <td
                        style={{
                          maxWidth: '300px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {log.subject}
                      </td>
                      <td>
                        <span className={`badge ${log.status}`}>
                          {log.status === 'sent' ? '✓ Sent' : '✗ Failed'}
                        </span>
                      </td>
                      <td>
                        {log.error_message ? (
                          <span className="error-msg" title={log.error_message}>
                            {log.error_message}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ marginTop: '12px', fontSize: '12px', color: '#94A3B8' }}>
              Showing last {logs.length} entries
            </p>
          </>
        ) : (
          <div className="empty">
            <p style={{ fontSize: '40px', marginBottom: '8px' }}>📭</p>
            <p>No emails have been sent yet.</p>
          </div>
        )}
      </div>
    </>
  )
}
