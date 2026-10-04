import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'

interface MyReqItem {
  id: number
  request_number: string
  type: string
  type_icon: string
  summary: string
  status: string
  status_label: string
  created_at: string
  url: string
}

const badgeStyles: Record<string, React.CSSProperties> = {
  pending_first: { background: '#fef3c7', color: '#92400e' },
  pending_second: { background: '#fef3c7', color: '#92400e' },
  pending_grants: { background: '#fef3c7', color: '#92400e' },
  pending_transport: { background: '#fef3c7', color: '#92400e' },
  pending: { background: '#fef3c7', color: '#92400e' },
  approved: { background: '#dcfce7', color: '#166534' },
  assigned: { background: '#dcfce7', color: '#166534' },
  rejected: { background: '#fee2e2', color: '#991b1b' },
}

// Exact replica of templates/my_requisitions.html
export function MyRequisitions() {
  const { data: items, isLoading } = useQuery({
    queryKey: ['myRequisitions'],
    queryFn: async () => {
      const response = await api.get<MyReqItem[]>('/my-requisitions/')
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <>
      <style>{`
        .req-table { width:100%; border-collapse:collapse; font-size:.85rem; }
        .req-table th { text-align:left; padding:12px 14px; font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); border-bottom:2px solid var(--border); background:#f8fafc; }
        .req-table td { padding:14px; border-bottom:1px solid #f1f5f9; vertical-align:middle; }
        .req-table tr:hover { background:#f8fafc; }
        .badge-status { display:inline-block; padding:3px 12px; border-radius:20px; font-size:.7rem; font-weight:600; }
        .empty-state { text-align:center; padding:60px 20px; color:var(--muted); }
        .empty-state .icon { font-size:3rem; margin-bottom:16px; }
        @media(max-width:768px){
            .req-table, .req-table thead, .req-table tbody, .req-table tr, .req-table th, .req-table td { display:block; }
            .req-table thead { display:none; }
            .req-table tr { padding:14px; margin-bottom:12px; border:1px solid var(--border); border-radius:12px; background:#fff; }
            .req-table td { padding:6px 0; border:none; display:flex; justify-content:space-between; gap:8px; }
            .req-table td::before { content:attr(data-label); font-weight:600; color:var(--muted); font-size:.75rem; text-transform:uppercase; }
        }
      `}</style>

      {items && items.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="req-table">
            <thead>
              <tr>
                <th>Request #</th>
                <th>Type</th>
                <th>Summary</th>
                <th>Status</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={`${item.type}-${item.id}`}>
                  <td data-label="Request #">
                    <strong>{item.request_number}</strong>
                  </td>
                  <td data-label="Type">
                    {item.type_icon} {item.type}
                  </td>
                  <td data-label="Summary">{item.summary}</td>
                  <td data-label="Status">
                    <span
                      className="badge-status"
                      style={badgeStyles[item.status] || { background: '#f1f5f9', color: '#475569' }}
                    >
                      {item.status_label}
                    </span>
                  </td>
                  <td data-label="Date">{item.created_at}</td>
                  <td>
                    <Link
                      to={`/${item.type.toLowerCase()}/${item.id}`}
                      className="btn btn-sm btn-outline-secondary"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <div className="icon">📋</div>
          <h5 style={{ fontWeight: 600 }}>No requisitions yet</h5>
          <p style={{ color: 'var(--muted)' }}>You haven't submitted any requisitions.</p>
        </div>
      )}
    </>
  )
}
