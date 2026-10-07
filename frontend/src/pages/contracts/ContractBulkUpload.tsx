import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash, type FlashLevel } from '@/lib/flash'

interface BulkResult {
  detail: string
  warning: string
  created: number
  updated: number
  failed: number
}

// bulk_upload.html's <pre> sample rows, byte for byte.
const csvExample = `PIN,Name,Designation,Salary,Start Date,End Date,Contract Type,Email,Phone,TIN,New Designation
123,John Doe,Senior Analyst,50000,2025-07-01,2026-06-30,Renewal,john@company.com,01712345678,123456789,Lead Analyst
124,Jane Smith,Manager,60000,2025-07-01,2026-06-30,Extension,jane@company.com,01723456789,987654321,
125,Alex Lee,Analyst,45000,2025-07-01,2026-06-30,Revision,alex@company.com,01734567890,456789123,`

// contracts/templates/contracts/bulk_upload.html -- <style> block, verbatim.
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

  .bu-wrapper {
    max-width: 700px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem;
  }

  .bu-card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
  }

  .bu-card-body {
    padding: 20px;
  }

  .bu-header {
    margin-bottom: 1.5rem;
  }

  .bu-header h1 {
    font-size: 22px;
    margin-bottom: 6px;
  }

  .bu-header p {
    color: var(--c-muted);
    font-size: 14px;
  }

  .field {
    margin-bottom: 16px;
  }

  .field label {
    display: block;
    font-size: 14px;
    margin-bottom: 6px;
    font-weight: 500;
  }

  .field input,
  .field select {
    width: 100%;
    padding: 10px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--c-border);
    font-size: 14px;
  }

  .helper {
    font-size: 12px;
    color: var(--c-muted);
    margin-top: 4px;
  }

  .section-label {
    font-size: 13px;
    font-weight: 600;
    margin: 16px 0 8px;
    color: var(--c-accent);
  }

  .btn {
    display: inline-block;
    padding: 10px 16px;
    border-radius: var(--radius-sm);
    border: none;
    cursor: pointer;
    font-size: 14px;
  }

  .btn-success {
    background: var(--c-success);
    color: #fff;
  }
`

// Replica of contracts/templates/contracts/bulk_upload.html
export function ContractBulkUpload() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [file, setFile] = useState<File | null>(null)
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)
  const ownsFlash = useRef(false)

  // A rejected upload re-renders this page with the messages block, so the
  // sentence is shown inline and the shared slot -- which only HrLayout
  // drains on a navigation -- is dropped again rather than leaking onward.
  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  const upload = useMutation({
    mutationFn: async (csv: File) => {
      const body = new FormData()
      body.append('file', csv)
      const response = await api.post<BulkResult>('/contracts/bulk/', body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: (data) => {
      ownsFlash.current = false
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      // main queues the count as a success and the failed rows as a warning;
      // the slot holds one message, so both sentences ride together.
      if (data.warning) setFlash('warning', `${data.detail} ${data.warning}`)
      else setFlash('success', data.detail)
      navigate('/hr/contracts/list')
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    },
  })

  return (
    <>
      <PageStyle css={css} />
      <link
        href={'https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap'}
        rel="stylesheet"
      />

      <div className="bu-wrapper">
        {/* Instructions */}
        <div className="bu-card" style={{ marginBottom: '1.5rem' }}>
          <div className="bu-card-body">
            <div className="section-label">📋 Instructions</div>
            <ol
              style={{
                fontSize: '14px',
                lineHeight: 1.8,
                color: 'var(--c-muted)',
                paddingLeft: '20px',
              }}
            >
              <li>
                Prepare <strong>Contract CSV</strong> with columns: <code>PIN, Name, Designation,
                Salary, Start Date, End Date, Contract Type</code>
              </li>
              <li>
                <strong>Optional columns</strong>: Email, Phone, TIN, New Designation (will update
                employee if PIN exists)
              </li>
              <li>Upload the CSV file using the form below</li>
              <li>Click "Upload CSV" to import contracts</li>
            </ol>

            <div className="section-label" style={{ marginTop: '1.5rem' }}>
              📄 CSV Format Example
              <a
                href="/api/contracts/csv-template/"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  marginLeft: '12px',
                  padding: '4px 10px',
                  background: '#2563EB',
                  color: '#fff',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: '500',
                  textDecoration: 'none',
                  verticalAlign: 'middle',
                }}
              >
                ⬇ Download CSV
              </a>
            </div>

            <div style={{ marginTop: '12px' }}>
              <div
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--c-accent)',
                  marginBottom: '8px',
                }}
              >
                Contract CSV (contracts.csv)
              </div>
              <pre
                style={{
                  background: 'var(--c-bg)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12px',
                  overflowX: 'auto',
                  border: '1px solid var(--c-border)',
                }}
              >
                {csvExample}
              </pre>
            </div>

            <div
              style={{
                marginTop: '1rem',
                padding: '10px 14px',
                background: '#FFF7ED',
                border: '1px solid rgba(234,88,12,0.2)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
                color: '#9A3412',
              }}
            >
              <strong>⚠️ Note:</strong> PIN is required. If PIN exists, employee info (Name,
              Designation, Salary, Email, Phone, TIN) will be updated. New Designation is used only
              for Renewal contracts.
            </div>
          </div>
        </div>

        {/* Header */}
        <div className="bu-header">
          <h1>Bulk Upload Contracts (CSV)</h1>
          <p>Upload contract data for multiple employees at once.</p>
        </div>

        {notice && (
          <div className={`app-message ${notice.level}`}>
            <span className="msg-close" onClick={() => setNotice(null)}>
              &times;
            </span>
            {notice.text}
          </div>
        )}

        {/* Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            setNotice(null)
            if (file) upload.mutate(file)
          }}
        >
          <div className="bu-card">
            <div className="bu-card-body">
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '16px',
                }}
              >
                <div className="section-label" style={{ margin: 0 }}>
                  Contract Data
                </div>
              </div>
              <div className="field">
                <label>
                  Contract CSV (PIN, Name, Designation, Salary, Start Date, End Date, Contract Type)
                </label>
                <input
                  type="file"
                  name="file"
                  accept=".csv"
                  required
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <div className="helper">
                  Columns: PIN (required), Name, Designation, Salary, Start Date (YYYY-MM-DD), End
                  Date (YYYY-MM-DD), Type (New/Extension/Revision/Renewal). Optional: Email, Phone,
                  TIN, New Designation
                </div>
              </div>

              <button type="submit" className="btn btn-success" disabled={upload.isPending}>
                Upload CSV
              </button>
            </div>
          </div>
        </form>
      </div>
    </>
  )
}
