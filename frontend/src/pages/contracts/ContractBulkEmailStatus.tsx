import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, type FlashLevel } from '@/lib/flash'

interface StatusResult {
  total: number
  sent: number
  failed: number
  pending: number
  finished: boolean
  results: Array<{
    contract_id: number | string
    name: string
    email: string
    status: 'sent' | 'failed' | 'pending'
    reason?: string
  }>
  elapsed: number
  group: string
}

interface JobState {
  group?: string
  total?: number
  started?: number
}

// contracts/templates/contracts/bulk_email_status.html -- <style> block, verbatim.
const css = `
  .s-container {
    max-width: 680px;
    margin: 0 auto;
  }
  .s-card {
    background: #fff;
    border-radius: 16px;
    padding: 28px;
    border: 1px solid #E2E8F0;
  }
  .s-card h3 {
    margin: 0 0 4px;
    font-size: 20px;
  }
  .s-card .sub {
    color: #64748B;
    font-size: 13px;
    margin-bottom: 20px;
  }
  .s-stats {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
  }
  .s-stat {
    flex: 1;
    text-align: center;
    padding: 16px 8px;
    border-radius: 12px;
    background: #F8FAFC;
  }
  .s-stat .num {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.2;
  }
  .s-stat .lbl {
    font-size: 12px;
    color: #64748B;
    margin-top: 2px;
  }
  .s-stat.sent .num { color: #16A34A; }
  .s-stat.fail .num { color: #EF4444; }
  .s-stat.pend .num { color: #F59E0B; }

  .s-bar {
    height: 6px;
    background: #E2E8F0;
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 12px;
  }
  .s-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563EB, #3B82F6);
    border-radius: 3px;
    transition: width .8s ease;
  }

  .s-info {
    font-size: 13px;
    color: #64748B;
    margin-bottom: 16px;
    text-align: center;
  }

  .s-list {
    margin-top: 16px;
    border-top: 1px solid #E2E8F0;
    padding-top: 12px;
    max-height: 320px;
    overflow-y: auto;
  }
  .s-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    font-size: 13px;
    border-bottom: 1px solid #F1F5F9;
  }
  .s-item .badge {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 20px;
  }
  .badge.sent { background: #F0FDF4; color: #16A34A; }
  .badge.failed { background: #FEF2F2; color: #EF4444; }
  .badge.pending { background: #FEF3C7; color: #F59E0B; }

  .s-empty {
    text-align: center;
    padding: 40px 0;
    color: #94A3B8;
  }
  .s-empty .big { font-size: 40px; margin-bottom: 8px; }
  .s-actions { margin-top: 20px; text-align: center; }
  .btn {
    display: inline-block;
    padding: 10px 22px;
    background: #2563EB;
    color: #fff;
    border-radius: 10px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
  }
  .btn:hover { background: #1D4ED8; }
  .btn-outline {
    background: transparent;
    color: #2563EB;
    border: 1px solid #E2E8F0;
    margin-left: 8px;
  }
  .btn-outline:hover { background: #F8FAFC; }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #E2E8F0;
    border-top-color: #2563EB;
    border-radius: 50%;
    animation: spin .8s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .fail-reason {
    font-size: 11px;
    color: #EF4444;
    margin-left: 8px;
  }
`

// Replica of contracts/templates/contracts/bulk_email_status.html
export function ContractBulkEmailStatus() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state ?? null) as JobState | null

  const group = state?.group ?? ''
  const total = state?.total ?? 0
  const started = state?.started

  const [finished, setFinished] = useState(false)
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)

  // main keeps the job in the session; the React caller carries it in router
  // state instead, so arriving without it means there is nothing to watch.
  useEffect(() => {
    if (!state || !group) navigate('/hr/contracts/list', { replace: true })
  }, [state, group, navigate])

  // The template reloads itself every 4s while jobs remain; here the same
  // cadence is a refetch that stops the moment the batch reports finished.
  const statusQuery = useQuery({
    queryKey: ['contracts', 'bulk-email-status', group, total, started],
    queryFn: async () =>
      (
        await api.get<StatusResult>('/contracts/bulk-email-status/', {
          params: { group, total, started },
        })
      ).data,
    enabled: Boolean(group),
    refetchInterval: finished ? false : 1500,
  })

  useEffect(() => {
    if (statusQuery.data?.finished) setFinished(true)
  }, [statusQuery.data])

  useEffect(() => {
    if (statusQuery.isError) {
      setNotice({ level: 'error', text: flashFromError(statusQuery.error).text })
    }
  }, [statusQuery.isError, statusQuery.error])

  const data = statusQuery.data
  const sent = data?.sent ?? 0
  const failed = data?.failed ?? 0
  const elapsed = data?.elapsed ?? 0
  const results = data?.results ?? []
  const done = sent + failed
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0

  const empty = total === 0

  return (
    <>
      <PageStyle css={css} />

      <div className="s-container">
        <div className="s-card">
          {empty ? (
            <div className="s-empty">
              <div className="big">📭</div>
              <p>No active bulk email job.</p>
              <p style={{ fontSize: '13px' }}>Submit contracts from the list page to start.</p>
              <div className="s-actions">
                <Link to="/hr/contracts/list" className="btn">
                  ← Go to Contract List
                </Link>
              </div>
            </div>
          ) : (
            <>
              <h3>📧 Bulk Email Progress</h3>
              <p className="sub">
                {total} contract(s) · {elapsed}s elapsed
              </p>

              <div className="s-stats">
                <div className="s-stat sent">
                  <div className="num">{sent}</div>
                  <div className="lbl">Sent</div>
                </div>
                <div className="s-stat pend">
                  <div className="num">{data?.pending ?? total}</div>
                  <div className="lbl">Pending</div>
                </div>
                <div className="s-stat fail">
                  <div className="num">{failed}</div>
                  <div className="lbl">Failed</div>
                </div>
              </div>

              <div className="s-bar">
                <div className="s-bar-fill" style={{ width: `${pct}%` }} />
              </div>

              <div className="s-info">
                {done} of {total} completed
                {!finished && (
                  <>
                    {' '}
                    · <span className="spinner" /> Processing...
                  </>
                )}
              </div>

              {notice && (
                <div className={`app-message ${notice.level}`}>
                  <span className="msg-close" onClick={() => setNotice(null)}>
                    &times;
                  </span>
                  {notice.text}
                </div>
              )}

              {results.length > 0 && (
                <div className="s-list">
                  {results.map((r, i) => (
                    <div className="s-item" key={`${r.contract_id}-${i}`}>
                      <span>
                        {r.name ? r.name : <>Contract #{r.contract_id}</>}
                        {r.email && (
                          <>
                            <br />
                            <small style={{ color: '#94A3B8' }}>{r.email}</small>
                          </>
                        )}
                      </span>
                      <span>
                        <span className={`badge ${r.status}`}>
                          {r.status === 'sent'
                            ? '✓ Sent'
                            : r.status === 'failed'
                              ? '✗ Failed'
                              : '⋯ Pending'}
                        </span>
                        {r.reason && <span className="fail-reason">({r.reason})</span>}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="s-actions">
                {!finished ? (
                  <button
                    type="button"
                    className="btn"
                    style={{ border: 'none', cursor: 'pointer' }}
                    onClick={() => statusQuery.refetch()}
                  >
                    🔄 Refresh
                  </button>
                ) : (
                  <>
                    <div
                      style={{
                        padding: '10px',
                        background: '#F0FDF4',
                        borderRadius: '10px',
                        color: '#16A34A',
                        fontSize: '14px',
                        fontWeight: 500,
                        marginBottom: '16px',
                      }}
                    >
                      ✅ All done — {sent} sent, {failed} failed in {elapsed}s
                    </div>
                    <Link to="/hr/contracts/list" className="btn">
                      ← Back to Contracts
                    </Link>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
