import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash, type FlashLevel } from '@/lib/flash'

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

interface EmailDefaults {
  subject: string
  body: string
  employee_email: string
}

interface EmailResult {
  detail: string
}

// contracts/templates/contracts/email_form.html -- <style> block, verbatim.
const css = `
  :root {
    --c-bg: #F7F6F3;
    --c-surface: #FFFFFF;
    --c-border: rgba(0,0,0,0.08);
    --c-border-strong: rgba(0,0,0,0.15);
    --c-text: #1A1917;
    --c-muted: #6B6A66;
    --c-accent: #2563EB;
    --c-success: #16A34A;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--c-bg);
    color: var(--c-text);
  }

  @media (max-width: 768px) {
    .email-wrapper { padding: 1rem !important; }
    .card-header { padding: 15px !important; }
    .card-body { padding: 15px !important; }
    .field input, .field textarea { font-size: 16px; }
    .btn { width: 100%; justify-content: center; }
    .back-btn { width: auto; }
  }

  .email-wrapper {
    max-width: 600px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem;
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: #fff;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    color: var(--c-text);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 1.5rem;
    transition: all 0.2s;
  }

  .back-btn:hover {
    background: var(--c-bg);
    border-color: var(--c-accent);
    color: var(--c-accent);
  }

  .card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
  }

  .card-header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--c-border);
  }

  .card-header h2 {
    font-size: 18px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .card-body {
    padding: 24px;
  }

  .field {
    margin-bottom: 20px;
  }

  .field label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--c-muted);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .field input,
  .field textarea {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    transition: border-color 0.2s;
  }

  .field input:focus,
  .field textarea:focus {
    outline: none;
    border-color: var(--c-accent);
  }

  .field textarea {
    resize: vertical;
    min-height: 120px;
  }

  .contract-info {
    background: var(--c-bg);
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    margin-bottom: 20px;
    font-size: 14px;
    color: var(--c-muted);
  }

  .contract-info strong {
    color: var(--c-text);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 20px;
    border-radius: var(--radius-sm);
    border: none;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    transition: all 0.2s;
  }

  .btn-primary {
    background: var(--c-accent);
    color: #fff;
  }

  .btn-primary:hover {
    background: #1D4ED8;
  }

  .btn-primary:disabled {
    background: #93C5FD;
    cursor: not-allowed;
  }

  .alert {
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    margin-bottom: 20px;
    font-size: 14px;
  }

  .alert-success {
    background: #F0FDF4;
    color: #16A34A;
    border: 1px solid #BBF7D0;
  }

  .alert-error {
    background: #FEF2F2;
    color: #DC2626;
    border: 1px solid #FECACA;
  }
`

// Replica of contracts/templates/contracts/email_form.html
export function ContractEmail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [recipient, setRecipient] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)
  const ownsFlash = useRef(false)

  // main re-renders email_form with the messages block after a failed POST
  // without leaving the page -- so the sentence is shown inline and the shared
  // slot is dropped again rather than leaking onto the next page.
  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  const contractQuery = useQuery({
    queryKey: ['contracts', 'detail', id],
    queryFn: async () => (await api.get<Contract>(`/contracts/${id}/`)).data,
    enabled: Boolean(id),
  })

  const defaultsQuery = useQuery({
    queryKey: ['contracts', 'email-defaults', id],
    queryFn: async () => (await api.get<EmailDefaults>(`/contracts/${id}/defaults/`)).data,
    enabled: Boolean(id),
  })

  // The template renders the pre-filled subject/body straight from the view;
  // the form fields take the same values as they arrive, and only while they
  // are still empty so a half-typed message is never overwritten.
  useEffect(() => {
    const defaults = defaultsQuery.data
    if (!defaults) return
    setSubject((prev) => (prev === '' ? defaults.subject : prev))
    setBody((prev) => (prev === '' ? defaults.body : prev))
    setRecipient((prev) => (prev === '' ? defaults.employee_email : prev))
  }, [defaultsQuery.data])

  useEffect(() => {
    if (contractQuery.isError) {
      const text = flashFromError(contractQuery.error).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    }
  }, [contractQuery.isError, contractQuery.error])

  const send = useMutation({
    mutationFn: async () => {
      const response = await api.post<EmailResult>(`/contracts/${id}/email/`, {
        recipient,
        subject,
        body,
      })
      return response.data
    },
    onSuccess: (data) => {
      ownsFlash.current = false
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      setFlash('success', data.detail)
      navigate('/hr/contracts/list')
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    },
  })

  const contract = contractQuery.data
  const employeeEmail = defaultsQuery.data?.employee_email ?? ''
  const alertClass = notice?.level === 'success' ? 'alert alert-success' : 'alert alert-error'

  return (
    <>
      <PageStyle css={css} />
      <link
        href={'https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap'}
        rel="stylesheet"
      />

      <div className="email-wrapper">
        <Link to="/hr/contracts/list" className="back-btn">
          ← Back to Contracts
        </Link>

        <div className="card">
          <div className="card-header">
            <h2>📧 Send Contract via Email</h2>
          </div>
          <div className="card-body">
            {notice && (
              <div className={alertClass}>
                <span
                  onClick={() => setNotice(null)}
                  style={{ float: 'right', cursor: 'pointer', opacity: 0.6, marginLeft: '8px' }}
                >
                  &times;
                </span>
                {notice.text}
              </div>
            )}

            {contract ? (
              <>
                <div className="contract-info">
                  Sending contract for: <strong>{contract.name}</strong> (PIN: {contract.pin})
                  <br />
                  Contract Type: <strong>{contract.contract_type}</strong> | Period:{' '}
                  {contract.start_date} to {contract.end_date}
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    setNotice(null)
                    send.mutate()
                  }}
                >
                  <div className="field">
                    <label>Recipient Email *</label>
                    <input
                      type="email"
                      name="recipient"
                      required
                      value={recipient}
                      onChange={(e) => setRecipient(e.target.value)}
                      placeholder="recipient@example.com"
                    />
                    {!employeeEmail && (
                      <div style={{ fontSize: '12px', color: 'var(--c-muted)', marginTop: '4px' }}>
                        No email found for this employee. Please enter manually.
                      </div>
                    )}
                  </div>

                  <div className="field">
                    <label>Subject</label>
                    <input
                      type="text"
                      name="subject"
                      required
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                    />
                  </div>

                  <div className="field">
                    <label>Message Body</label>
                    <textarea
                      name="body"
                      required
                      rows={6}
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="btn btn-primary" disabled={send.isPending}>
                    📤 Send Email
                  </button>
                </form>
              </>
            ) : contractQuery.isError ? null : (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
