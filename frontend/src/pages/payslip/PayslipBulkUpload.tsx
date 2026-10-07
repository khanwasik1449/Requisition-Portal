import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash } from '@/lib/flash'

interface BulkUploadResponse {
  detail: string
  warning: string
  created: number
  failed: number
  errors: string[]
}

// payslip/templates/payslip/bulk_upload.html -- <style> block, verbatim. The
// template's Google-Fonts <link> rides along as an @import (same sheet, and
// @import has to be the first rule).
const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');

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
  body { font-family: 'DM Sans', sans-serif; background: var(--c-bg); color: var(--c-text); }
  .bu-wrapper { max-width: 700px; margin: 0 auto; padding: 2.5rem 1.5rem; }
  .bu-header { margin-bottom: 2rem; }
  .bu-header h1 { font-size: 1.6rem; font-weight: 600; }
  .bu-header p { font-size: 0.875rem; color: var(--c-muted); margin-top: 4px; }
  .bu-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius); box-shadow: var(--shadow); }
  .bu-card-body { padding: 1.75rem; }
  .field { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
  .field label { font-size: 13px; font-weight: 500; color: var(--c-muted); }
  .field input, .field select { border: 1px solid var(--c-border-strong); border-radius: var(--radius-sm); padding: 10px 12px; font-size: 14px; background: var(--c-bg); outline: none; width: 100%; }
  .field input:focus { border-color: var(--c-accent); background: #fff; }
  .alert { padding: 12px 16px; border-radius: var(--radius-sm); font-size: 14px; margin-bottom: 1rem; }
  .alert-success { background: #F0FDF4; color: #16A34A; border: 1px solid rgba(22,163,74,0.15); }
  .alert-error { background: #FEF2F2; color: #DC2626; border: 1px solid rgba(220,38,38,0.15); }
  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 10px 20px; border-radius: var(--radius-sm); font-size: 14px; font-weight: 500; cursor: pointer; border: none; }
  .btn-success { background: var(--c-success); color: #fff; }
  .helper { font-size: 12px; color: #A8A79F; margin-top: 4px; }
  .section-label { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #A8A79F; margin-top: 1rem; margin-bottom: 0.5rem; }
`

// Replica of payslip/templates/payslip/bulk_upload.html
export function PayslipBulkUpload() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  // main re-renders this page with a messages queue only on the failure path
  // (success redirects to payslip:list), so the alert lives right here.
  const [message, setMessage] = useState<{ level: string; text: string } | null>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setMessage(null)

    const form = e.currentTarget
    const file = (form.file as HTMLInputElement).files?.[0]
    const employeeFile = (form.employee_file as HTMLInputElement).files?.[0]
    const year = (form.year as HTMLSelectElement).value

    const formData = new FormData()
    formData.append('year', year)
    if (employeeFile) formData.append('employee_file', employeeFile)
    if (file) formData.append('file', file)

    setIsSubmitting(true)
    try {
      const { data } = await api.post<BulkUploadResponse>('/payslips/bulk/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      // main queues messages.success(detail) and messages.warning(warning)
      // before redirecting to payslip:list -- the flash slot carries one of
      // them over to that page.
      if (data.detail) setFlash('success', data.detail)
      else if (data.warning) setFlash('warning', data.warning)
      navigate('/hr/payslip/list')
    } catch (err) {
      // `❌ Upload failed: ...` / `No file uploaded! ...` come back as a 400
      // and stay on this page, exactly as the view falls through to render.
      setMessage({ level: 'error', text: flashFromError(err).text })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <PageStyle css={css} />

      <div className="bu-wrapper">
        <div className="bu-header">
          <h1>Bulk Upload Payslip (CSV)</h1>
          <p>Upload salary data for multiple employees at once. Requires two CSV files.</p>
        </div>

        {message && (
          <div className={`alert ${message.level === 'error' ? 'alert-error' : 'alert-success'}`}>
            {message.text}
          </div>
        )}

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
                Prepare <strong>Employee CSV</strong> with columns:{' '}
                <code>Dummy PIN, Real PIN, Name, Designation</code>
              </li>
              <li>
                Prepare <strong>Salary CSV</strong> with columns:{' '}
                <code>
                  Dummy PIN, Gender, TIN No., Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Apr, May,
                  Jun
                </code>
              </li>
              <li>
                Select the <strong>Year</strong> for which you're uploading data
              </li>
              <li>Upload both files and click "Upload CSV"</li>
            </ol>

            <div className="section-label" style={{ marginTop: '1.5rem' }}>
              📄 CSV Format Examples
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
                marginTop: '12px',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: 'var(--c-accent)',
                    marginBottom: '8px',
                  }}
                >
                  Employee CSV (employee.csv)
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
                  {'Dummy PIN,Real PIN,Name,Designation\n' +
                    'D001,E001,John Doe,Software Engineer\n' +
                    'D002,E002,Jane Smith,Data Analyst'}
                </pre>
              </div>

              <div>
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: 'var(--c-accent)',
                    marginBottom: '8px',
                  }}
                >
                  Salary CSV (salary.csv)
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
                  {'Dummy PIN,Gender,TIN No.,Jul,Aug,Sep,Oct,Nov,Dec,Jan,Feb,Mar,Apr,May,Jun\n' +
                    'D001,Male,1234567890,50000,50000,50000,50000,50000,50000,50000,50000,50000,50000,50000\n' +
                    'D002,Female,9876543210,60000,60000,60000,60000,60000,60000,60000,60000,60000,60000,60000'}
                </pre>
              </div>
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
              <strong>⚠️ Note:</strong> Dummy PIN in Salary CSV must match Dummy PIN in Employee CSV
              for proper mapping.
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="bu-card">
            <div className="bu-card-body">
              <div className="field">
                <label>Year</label>
                <select name="year" required>
                  <option value="2025">2025-26</option>
                  <option value="2024">2024-25</option>
                  <option value="2026">2026-27</option>
                </select>
              </div>

              <div className="section-label">PIN Mapping (Required)</div>
              <div className="field">
                <label>Employee CSV (Dummy PIN, Real PIN, Name, Designation)</label>
                <input type="file" name="employee_file" accept=".csv" required />
                <div className="helper">Maps Dummy PIN to Real PIN and employee details</div>
              </div>

              <div className="section-label">Salary Data</div>
              <div className="field">
                <label>Salary CSV (Dummy PIN, Gender, TIN No., then 12 monthly values)</label>
                <input type="file" name="file" accept=".csv" required />
                <div className="helper">
                  Columns: Dummy PIN, Gender, TIN No., Jul, Aug, Sep... (12 months)
                </div>
              </div>

              <button type="submit" className="btn btn-success" disabled={isSubmitting}>
                Upload CSV
              </button>
            </div>
          </div>
        </form>
      </div>
    </>
  )
}
