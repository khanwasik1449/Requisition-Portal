import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api, endpoints } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { formatStamp } from '@/lib/utils'

/**
 * `/notifications/track/<type>/<id>/` -- the public status card the
 * "Track Request Status" button in the requester's email opens.
 *
 * `notifications/track.html` is a standalone page (it extends nothing), so it
 * gets its own wrapper and its own `<style>` block, injected with `PageStyle`
 * for as long as the page is mounted.
 */

// templates/notifications/track.html, lines 8-15
const css = `
        body { background: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .status-icon { font-size: 3rem; }
        .timeline-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .timeline-dot.pending { background: #f59e0b; }
        .timeline-dot.approved { background: #16a34a; }
        .timeline-dot.rejected { background: #dc2626; }
    `

interface TrackRow {
  request_number: string
  full_name: string
  status: string
  created_at: string
  first_approved_at: string | null
  second_approved_at: string | null
  rejected_at: string | null
  rejection_reason: string
}

const PENDING_STATUSES = ['pending_first', 'pending_grants', 'pending_transport']

function StatusCard({ r }: { r: TrackRow }) {
  if (PENDING_STATUSES.includes(r.status)) {
    return (
      <>
        <div className="status-icon mb-2">⏳</div>
        <h2 className="h5 mb-1">Pending Approval</h2>
        <p className="text-muted small mb-0">
          {r.status === 'pending_first'
            ? 'Awaiting supervisor approval'
            : r.status === 'pending_grants'
              ? 'Approved by supervisor, awaiting Grants approval'
              : 'Approved by Grants, awaiting transport admin'}
        </p>
      </>
    )
  }

  if (r.status === 'approved') {
    return (
      <>
        <div className="status-icon mb-2">✅</div>
        <h2 className="h5 mb-1 text-success">Approved</h2>
        <p className="text-muted small mb-0">
          This requisition has been fully approved.
        </p>
      </>
    )
  }

  if (r.status === 'rejected') {
    return (
      <>
        <div className="status-icon mb-2">❌</div>
        <h2 className="h5 mb-1 text-danger">Rejected</h2>
        <p className="text-muted small mb-0">This requisition has been rejected.</p>
      </>
    )
  }

  // main renders an empty card for any status outside the three branches
  // above -- reproduced faithfully rather than papered over.
  return null
}

export function Track() {
  const { reqType = '', id = '' } = useParams()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['notification-track', reqType, id],
    queryFn: async () => {
      const { data: body } = await api.get(
        endpoints.notificationTrack(reqType, Number(id)),
      )
      return body as { label: string; r: TrackRow }
    },
  })

  if (isLoading) {
    return (
      <div className="container py-5">
        <div className="row justify-content-center">
          <div className="col-lg-6 text-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100 bg-light">
        <div className="card shadow-sm" style={{ maxWidth: '450px', width: '100%' }}>
          <div className="card-body text-center py-5">
            <div className="mb-3" style={{ fontSize: '3rem' }}>
              ⚠️
            </div>
            <h5 className="text-danger">Action Failed</h5>
            <p className="text-muted mb-0">
              The requisition could not be found.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const { label, r } = data

  return (
    <>
      <PageStyle css={css} />
      <div className="container py-5">
        <div className="row justify-content-center">
          <div className="col-lg-6">
            <div className="text-center mb-4">
              <h1 className="h3 mb-1">Requisition Status</h1>
              <p className="text-muted small">
                {label} &bull; {r.request_number}
              </p>
            </div>

            <div className="card shadow-sm mb-3">
              <div className="card-body text-center py-4">
                <StatusCard r={r} />
              </div>
            </div>

            <div className="card shadow-sm">
              <div className="card-body">
                <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
                  Details
                </h6>
                <table className="table table-sm table-borderless">
                  <tbody>
                    <tr>
                      <td className="text-muted small" style={{ width: '120px' }}>
                        Request #
                      </td>
                      <td className="fw-semibold">{r.request_number}</td>
                    </tr>
                    <tr>
                      <td className="text-muted small">Requester</td>
                      <td>{r.full_name}</td>
                    </tr>
                    <tr>
                      <td className="text-muted small">Submitted</td>
                      <td>{formatStamp(r.created_at)}</td>
                    </tr>
                    {r.first_approved_at && (
                      <tr>
                        <td className="text-muted small">1st Approval</td>
                        <td>{formatStamp(r.first_approved_at)}</td>
                      </tr>
                    )}
                    {r.second_approved_at && (
                      <tr>
                        <td className="text-muted small">2nd Approval</td>
                        <td>{formatStamp(r.second_approved_at)}</td>
                      </tr>
                    )}
                    {r.rejected_at && (
                      <tr>
                        <td className="text-muted small">Rejected</td>
                        <td>{formatStamp(r.rejected_at)}</td>
                      </tr>
                    )}
                    {r.rejection_reason && (
                      <tr>
                        <td className="text-muted small">Reason</td>
                        <td className="text-danger">{r.rejection_reason}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="text-center mt-4">
              <p className="text-muted small mb-0">BRAC IED Central Portal</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
