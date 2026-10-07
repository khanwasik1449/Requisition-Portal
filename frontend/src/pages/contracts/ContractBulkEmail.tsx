import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash, type FlashLevel } from '@/lib/flash'
import { getAllResults } from '@/lib/paginate'

interface Contract {
  id: number
  pin: string
  name: string
  designation: string
  new_designation?: string | null
  salary: number | string
  contract_type: string
  start_date: string
  end_date: string
}

interface BulkEmailResult {
  group: string
  total: number
  started: number
}

// The live bulk-email modal in list.html carries the body this page pre-fills.
const DEFAULT_SUBJECT = 'Contract Document'
const DEFAULT_BODY = `Dear Employee,

Please find your contract document attached with this email.

Best regards,
HR Department`

// contracts/templates/contracts/bulk_email.html -- <style> block, verbatim.
const css = `
  :root {
    --c-bg: #F7F6F3;
    --c-surface: #FFFFFF;
    --c-border: rgba(0,0,0,0.08);
    --c-border-strong: rgba(0,0,0,0.15);
    --c-text: #1A1917;
    --c-muted: #6B6A66;
    --c-hint: #A8A79F;
    --c-accent: #2563EB;
    --c-accent-bg: #EFF4FF;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);
  }

  .bulk-wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }

  .bulk-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.75rem;
    flex-wrap: wrap;
    gap: 12px;
  }

  .bulk-header h1 {
    font-size: 1.5rem;
    font-weight: 600;
  }

  .bulk-header p {
    font-size: 13px;
    color: var(--c-muted);
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 18px;
    background: var(--c-surface);
    color: var(--c-text);
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    font-size: 13px;
    text-decoration: none;
  }

  .content-grid {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 1.5rem;
  }

  @media (max-width: 900px) {
    .content-grid {
      grid-template-columns: 1fr;
    }
  }

  .card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
  }

  .card-header {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--c-border);
    font-size: 14px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
  }

  .card-body {
    padding: 1.25rem;
  }

  .table-scroll {
    overflow-x: auto;
    max-height: 500px;
    overflow-y: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  thead th {
    position: sticky;
    top: 0;
    background: var(--c-bg);
    padding: 10px 12px;
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    color: var(--c-hint);
    border-bottom: 1px solid var(--c-border-strong);
  }

  tbody td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--c-border);
  }

  tbody tr:hover {
    background: #FAFAF8;
  }

  tbody tr.selected {
    background: var(--c-accent-bg);
  }

  .checkbox-cell {
    width: 40px;
    text-align: center;
  }

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    cursor: pointer;
  }

  .badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
  }

  .badge-new {
    background: #EFF6FF;
    color: #1D4ED8;
  }

  .badge-renewal {
    background: #F0FDF4;
    color: #166534;
  }

  .badge-extension {
    background: #FEF3C7;
    color: #92400E;
  }

  .badge-revision {
    background: #FCE7F3;
    color: #9D174D;
  }

  .email-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .form-group label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--c-muted);
    margin-bottom: 6px;
  }

  .form-group input,
  .form-group textarea {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
  }

  .form-group textarea {
    min-height: 150px;
    resize: vertical;
  }

  .form-hint {
    font-size: 11px;
    color: var(--c-hint);
    margin-top: 4px;
    font-family: 'DM Mono', monospace;
  }

  .btn-send {
    width: 100%;
    padding: 12px;
    background: #2563EB;
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-send:disabled {
    background: var(--c-hint);
    cursor: not-allowed;
  }

  .selected-count {
    font-size: 13px;
    color: var(--c-accent);
    font-weight: 600;
    font-family: 'DM Mono', monospace;
  }
`

// Replica of contracts/templates/contracts/bulk_email.html
export function ContractBulkEmail() {
  const navigate = useNavigate()
  const location = useLocation()

  // The list page hands its ticked rows over on the way in; arriving without
  // state simply leaves the table empty to be ticked here.
  const [selected, setSelected] = useState<number[]>(() => {
    const state = (location.state ?? {}) as { contractIds?: number[]; ids?: number[] }
    return state.contractIds ?? state.ids ?? []
  })
  const [subject, setSubject] = useState(DEFAULT_SUBJECT)
  const [body, setBody] = useState(DEFAULT_BODY)
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)
  const ownsFlash = useRef(false)

  // A rejected POST leaves the page exactly as it was, so the sentence is
  // shown inline and the shared slot dropped again on unmount.
  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  const listQuery = useQuery({
    queryKey: ['contracts', 'bulk-email'],
    queryFn: async () => getAllResults<Contract>('/contracts/'),
  })

  useEffect(() => {
    if (listQuery.isError) {
      const text = flashFromError(listQuery.error).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    }
  }, [listQuery.isError, listQuery.error])

  const contracts = listQuery.data?.results ?? []
  const count = selected.length
  const allChecked = contracts.length > 0 && contracts.every((c) => selected.includes(c.id))

  function toggleRow(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  function toggleAll() {
    setSelected(allChecked ? [] : contracts.map((c) => c.id))
  }

  const send = useMutation({
    mutationFn: async () => {
      const response = await api.post<BulkEmailResult>('/contracts/bulk-email/', {
        contract_ids: selected,
        subject,
        body,
      })
      return response.data
    },
    onSuccess: (data) => {
      ownsFlash.current = false
      navigate('/hr/contracts/bulk-email-status', {
        state: { group: data.group, total: data.total, started: data.started },
      })
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    },
  })

  // bulk_email_contracts rejects an empty selection before queueing anything.
  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (count === 0) {
      setFlash('error', 'No contracts selected!')
      ownsFlash.current = true
      navigate('/hr/contracts/list')
      return
    }
    send.mutate()
  }

  return (
    <>
      <PageStyle css={css} />
      <link
        href={
          'https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap'
        }
        rel="stylesheet"
      />

      <div className="bulk-wrap">
        <div className="bulk-header">
          <div>
            <h1>Bulk Email Contracts</h1>
            <p>Select contracts and send them via email</p>
          </div>

          <Link to="/hr/contracts/list" className="back-btn">
            ← Back to List
          </Link>
        </div>

        {notice && (
          <div className={`app-message ${notice.level}`}>
            <span className="msg-close" onClick={() => setNotice(null)}>
              &times;
            </span>
            {notice.text}
          </div>
        )}

        <form className="content-grid" onSubmit={handleSubmit}>
          {/* LEFT */}
          <div className="card">
            <div className="card-header">
              <span>Select Contracts</span>
              <span className="selected-count">{count} selected</span>
            </div>

            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th className="checkbox-cell">
                      <input type="checkbox" checked={allChecked} onChange={toggleAll} />
                    </th>
                    <th>PIN</th>
                    <th>Name</th>
                    <th>Type</th>
                  </tr>
                </thead>

                <tbody>
                  {listQuery.isLoading ? (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>
                        <div className="spinner-border text-primary" role="status">
                          <span className="visually-hidden">Loading...</span>
                        </div>
                      </td>
                    </tr>
                  ) : contracts.length === 0 ? (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>
                        No contracts found
                      </td>
                    </tr>
                  ) : (
                    contracts.map((contract) => (
                      <tr
                        key={contract.id}
                        className={selected.includes(contract.id) ? 'selected' : ''}
                        onClick={(e) => {
                          // The template toggles the box from anywhere on the row.
                          if (!(e.target instanceof HTMLInputElement)) toggleRow(contract.id)
                        }}
                      >
                        <td className="checkbox-cell">
                          <input
                            type="checkbox"
                            name="contract_ids"
                            value={contract.id}
                            id={`check-${contract.id}`}
                            checked={selected.includes(contract.id)}
                            onChange={() => toggleRow(contract.id)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
                        <td style={{ fontFamily: "'DM Mono',monospace" }}>{contract.pin}</td>
                        <td>{contract.name}</td>
                        <td>
                          <span
                            className={`badge badge-${(contract.contract_type || '').toLowerCase()}`}
                          >
                            {contract.contract_type}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* RIGHT */}
          <div className="card">
            <div className="card-header">
              <span>Email Template</span>
            </div>

            <div className="card-body email-form">
              <div className="form-group">
                <label htmlFor="subject">Subject</label>

                <input
                  type="text"
                  name="subject"
                  id="subject"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />

                <div className="form-hint">Use {'{name}'}, {'{pin}'}</div>
              </div>

              <div className="form-group">
                <label htmlFor="body">Body</label>

                <textarea
                  name="body"
                  id="body"
                  required
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />

                <div className="form-hint">
                  Use {'{name}'}, {'{pin}'}, {'{start_date}'}, {'{end_date}'}
                </div>
              </div>

              <button type="submit" className="btn-send" disabled={count === 0 || send.isPending}>
                Send Emails (<span>{count}</span>)
              </button>
            </div>
          </div>
        </form>
      </div>
    </>
  )
}
