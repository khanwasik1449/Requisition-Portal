import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError } from '@/lib/flash'

// Payslip is a flat row keyed by PIN -- it has no relations at all. `month`
// and `year` are strings; the Decimal columns come back as strings too, and
// `gross_salary` / `net_salary` are SerializerMethodFields (str of a Decimal).
interface Payslip {
  id: number
  pin: string
  name: string
  designation: string
  gender: string | null
  tin: string | null
  month: string
  year: string
  project: string
  branch: string
  basic_salary: string
  house_rent: string
  medical_allowance: string
  conveyance: string
  festival_bonus: string
  arrears: string
  others: string
  transport: string
  income_tax: string
  other_deduction: string
  created_at: string
  gross_salary: string
  net_salary: string
}

interface PayslipDraft {
  pin: string
  name: string
  designation: string
  month: string
  year: string
  project: string
  branch: string
  basic_salary: string
  transport: string
  income_tax: string
  other_deduction: string
}

const emptyDraft: PayslipDraft = {
  pin: '',
  name: '',
  designation: '',
  month: '',
  year: '2026',
  project: 'BUIED',
  branch: 'Niketon Housing, Gulshan',
  basic_salary: '',
  transport: '0',
  income_tax: '0',
  other_deduction: '0',
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

// Download through axios so the JWT is attached -- a plain <a href> cannot
// carry the Authorization header.
async function downloadPayslipPdf(p: Payslip): Promise<void> {
  const response = await api.get(`/payslips/${p.id}/pdf/`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `payslip_${p.pin}_${p.month}_${p.year}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

// payslip/templates/payslip/form.html -- <style> block, verbatim. The
// template's Google-Fonts <link> rides along as an @import (same sheet, and
// @import has to be the first rule).
const css = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

  :root {
    --c-bg: #F7F6F3;
    --c-surface: #FFFFFF;
    --c-border: rgba(0,0,0,0.08);
    --c-border-strong: rgba(0,0,0,0.15);
    --c-text: #1A1917;
    --c-muted: #6B6A66;
    --c-hint: #A8A79F;
    --c-accent: #2563EB;
    --c-accent-light: #EFF4FF;
    --c-success: #16A34A;
    --c-success-light: #F0FDF4;
    --c-danger: #DC2626;
    --c-danger-light: #FEF2F2;
    --c-amber: #D97706;
    --c-amber-light: #FFFBEB;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body { font-family: 'DM Sans', sans-serif; background: var(--c-bg); color: var(--c-text); }

  .ps-wrapper { max-width: 800px; margin: 0 auto; padding: 2.5rem 1.5rem; }

  .ps-header { margin-bottom: 2rem; }
  .ps-header h1 { font-size: 1.6rem; font-weight: 600; }
  .ps-header p { font-size: 0.875rem; color: var(--c-muted); margin-top: 4px; }

  .ps-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius); box-shadow: var(--shadow); }
  .ps-card-body { padding: 1.75rem; }

  .section-label { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--c-hint); margin-bottom: 1.25rem; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  .grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 14px; }

  @media (max-width: 600px) { .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } }

  .field { display: flex; flex-direction: column; gap: 5px; }
  .field label { font-size: 13px; font-weight: 500; color: var(--c-muted); }
  .field input, .field select {
    height: 40px; border: 1px solid var(--c-border-strong); border-radius: var(--radius-sm);
    padding: 0 12px; font-size: 14px; font-family: 'DM Sans', sans-serif;
    background: var(--c-bg); outline: none; width: 100%;
  }
  .field input:focus, .field select:focus { border-color: var(--c-accent); box-shadow: 0 0 0 3px rgba(37,99,235,0.1); background: #fff; }

  .divider { height: 1px; background: var(--c-border); margin: 1.5rem 0; }

  .salary-box { background: var(--c-bg); border: 1px solid var(--c-border); border-radius: var(--radius-sm); padding: 14px 16px; text-align: center; }
  .salary-box .label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-hint); margin-bottom: 4px; }
  .salary-box .value { font-size: 18px; font-weight: 600; font-family: 'DM Mono', monospace; }
  .salary-box.highlight { background: var(--c-accent-light); border-color: var(--c-accent); }
  .salary-box.highlight .value { color: var(--c-accent); }
  .salary-box.success { background: var(--c-success-light); border-color: var(--c-success); }
  .salary-box.success .value { color: var(--c-success); }
  .salary-box.danger { background: var(--c-danger-light); border-color: var(--c-danger); }
  .salary-box.danger .value { color: var(--c-danger); }
  .salary-box.info { background: #EFF6FF; border-color: #3B82F6; }
  .salary-box.info .value { color: #3B82F6; }

  .btn { display: inline-flex; align-items: center; gap: 6px; padding: 9px 20px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; transition: all 0.18s; text-decoration: none; }
  .btn-success { background: var(--c-success); color: #fff; border-color: var(--c-success); }
  .btn-success:hover { background: #15803D; transform: translateY(-1px); }

  .alert-box { padding: 12px 16px; border-radius: var(--radius-sm); font-size: 14px; margin-bottom: 1rem; display: flex; align-items: center; gap: 10px; }
  .alert-success { background: var(--c-success-light); color: var(--c-success); border: 1px solid rgba(22,163,74,0.15); }

  @keyframes popIn { from { transform: scale(0.5); opacity: 0; } to { transform: scale(1); opacity: 1; } }
  .success-state h2 { font-size: 1.25rem; font-weight: 600; }
  .success-state p { font-size: 14px; color: var(--c-muted); margin-bottom: 1.75rem; }
  .btn-group { display: flex; gap: 10px; justify-content: center; }
`

// Replica of payslip/templates/payslip/form.html
export function PayslipForm() {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<PayslipDraft>(emptyDraft)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  // create_payslip redirects back to this same URL and re-renders it with
  // `created_payslip` from the session, so success swaps in the template's
  // alert + modal rather than routing away.
  const [created, setCreated] = useState<Payslip | null>(null)

  const field = (key: keyof PayslipDraft, value: string) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
  }

  // The template's inline calculate() -- one figure in, the 50/30/10/10
  // breakdown and the three totals out.
  const totalSalary = parseFloat(draft.basic_salary) || 0
  const transport = parseFloat(draft.transport) || 0
  const incomeTax = parseFloat(draft.income_tax) || 0
  const otherDeduction = parseFloat(draft.other_deduction) || 0
  const fmt = (n: number) => n.toLocaleString('en-BD', { minimumFractionDigits: 2 })
  const basic = totalSalary * 0.5
  const houseRent = totalSalary * 0.3
  const medical = totalSalary * 0.1
  const conveyance = totalSalary * 0.1
  const totalDeduction = transport + incomeTax + otherDeduction
  const netPay = totalSalary - totalDeduction

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      // The view treats the posted `basic_salary` as the *total* salary and
      // splits it 50/30/10/10 server-side; the response is the saved row with
      // the four columns already split -- exactly what form.html renders as
      // `created_payslip`.
      const { data } = await api.post<Payslip>('/payslips/', {
        pin: draft.pin,
        name: draft.name,
        designation: draft.designation,
        month: draft.month,
        year: draft.year,
        project: draft.project,
        branch: draft.branch,
        basic_salary: draft.basic_salary,
        transport: draft.transport,
        income_tax: draft.income_tax,
        other_deduction: draft.other_deduction,
      })
      queryClient.invalidateQueries({ queryKey: ['payslips'] })
      setCreated(data)
    } catch (err) {
      setError(flashFromError(err).text)
    } finally {
      setIsSubmitting(false)
    }
  }

  // "Create another" reloads the same pathname in main -- a fresh form with
  // the session's created_payslip popped.
  const resetForm = () => {
    setCreated(null)
    setError('')
    setDraft(emptyDraft)
  }

  const handlePdf = async () => {
    if (!created) return
    try {
      await downloadPayslipPdf(created)
    } catch (err) {
      setError(flashFromError(err).text)
    }
  }

  return (
    <>
      <PageStyle css={css} />

      <div className="ps-wrapper">
        <div className="ps-header">
          <h1>Create Payslip</h1>
          <p>Enter employee details and salary information.</p>
        </div>

        {created && (
          <div className="alert-box alert-success">✓ Payslip created successfully!</div>
        )}

        {/* The form has no error slot in main -- a rejected POST just
            re-renders the form, so the sentence sits in the same alert box. */}
        {error && (
          <div
            className="alert-box"
            style={{
              background: 'var(--c-danger-light)',
              color: 'var(--c-danger)',
              border: '1px solid rgba(220,38,38,0.15)',
            }}
          >
            {error}
          </div>
        )}

        <form id="payslipForm" onSubmit={handleSubmit}>
          <div className="ps-card">
            <div className="ps-card-body">
              <div className="section-label">Employee Information</div>
              <div className="grid-3">
                <div className="field">
                  <label>
                    PIN <span style={{ color: 'var(--c-danger)' }}>*</span>
                  </label>
                  <input
                    type="text"
                    name="pin"
                    placeholder="e.g. EMP-001"
                    required
                    value={draft.pin}
                    onChange={(e) => field('pin', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>
                    Name <span style={{ color: 'var(--c-danger)' }}>*</span>
                  </label>
                  <input
                    type="text"
                    name="name"
                    placeholder="Full name"
                    required
                    value={draft.name}
                    onChange={(e) => field('name', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>
                    Designation <span style={{ color: 'var(--c-danger)' }}>*</span>
                  </label>
                  <input
                    type="text"
                    name="designation"
                    placeholder="Job title"
                    required
                    value={draft.designation}
                    onChange={(e) => field('designation', e.target.value)}
                  />
                </div>
              </div>

              <div className="divider" />

              <div className="section-label">Period</div>
              <div className="grid-4">
                <div className="field">
                  <label>
                    Month <span style={{ color: 'var(--c-danger)' }}>*</span>
                  </label>
                  <select
                    name="month"
                    required
                    value={draft.month}
                    onChange={(e) => field('month', e.target.value)}
                  >
                    <option value="">Select</option>
                    {MONTHS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>
                    Year <span style={{ color: 'var(--c-danger)' }}>*</span>
                  </label>
                  <input
                    type="number"
                    name="year"
                    required
                    value={draft.year}
                    onChange={(e) => field('year', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Project</label>
                  <input
                    type="text"
                    name="project"
                    value={draft.project}
                    onChange={(e) => field('project', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Branch</label>
                  <input
                    type="text"
                    name="branch"
                    value={draft.branch}
                    onChange={(e) => field('branch', e.target.value)}
                  />
                </div>
              </div>

              <div className="divider" />

              <div className="section-label">
                Salary (Enter total salary - breakdown auto-calculated)
              </div>
              <div className="grid-2">
                <div className="field">
                  <label>
                    Total Salary (BDT) <span style={{ color: 'var(--c-danger)' }}>*</span>
                  </label>
                  <input
                    type="number"
                    name="basic_salary"
                    placeholder="0"
                    step="0.01"
                    required
                    value={draft.basic_salary}
                    onChange={(e) => field('basic_salary', e.target.value)}
                  />
                  <small style={{ color: 'var(--c-hint)' }}>
                    Auto: Basic 50%, House Rent 30%, Medical 10%, Conveyance 10%
                  </small>
                </div>
              </div>

              <div className="grid-4 mt-3">
                <div className="salary-box info">
                  <div className="label">Basic (50%)</div>
                  <div className="value">{fmt(basic)}</div>
                </div>
                <div className="salary-box info">
                  <div className="label">House Rent (30%)</div>
                  <div className="value">{fmt(houseRent)}</div>
                </div>
                <div className="salary-box info">
                  <div className="label">Medical (10%)</div>
                  <div className="value">{fmt(medical)}</div>
                </div>
                <div className="salary-box info">
                  <div className="label">Conveyance (10%)</div>
                  <div className="value">{fmt(conveyance)}</div>
                </div>
              </div>

              <div className="divider" />

              <div className="section-label">Deductions (Manual Input)</div>
              <div className="grid-3">
                <div className="field">
                  <label>Transport</label>
                  <input
                    type="number"
                    name="transport"
                    value={draft.transport}
                    step="0.01"
                    onChange={(e) => field('transport', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Income Tax</label>
                  <input
                    type="number"
                    name="income_tax"
                    value={draft.income_tax}
                    step="0.01"
                    onChange={(e) => field('income_tax', e.target.value)}
                  />
                </div>
                <div className="field">
                  <label>Other Deduction</label>
                  <input
                    type="number"
                    name="other_deduction"
                    value={draft.other_deduction}
                    step="0.01"
                    onChange={(e) => field('other_deduction', e.target.value)}
                  />
                </div>
              </div>

              <div className="divider" />

              <div className="grid-3">
                <div className="salary-box highlight">
                  <div className="label">Total Salary</div>
                  <div className="value">{fmt(totalSalary)}</div>
                </div>
                <div className="salary-box danger">
                  <div className="label">Total Deduction</div>
                  <div className="value">{fmt(totalDeduction)}</div>
                </div>
                <div className="salary-box success">
                  <div className="label">Net Pay</div>
                  <div className="value">{fmt(netPay)}</div>
                </div>
              </div>
            </div>

            <div
              style={{
                padding: '1.25rem 1.75rem',
                borderTop: '1px solid var(--c-border)',
                background: 'var(--c-bg)',
              }}
            >
              <button
                type="submit"
                className="btn btn-success"
                style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
                disabled={isSubmitting}
              >
                Create Payslip
              </button>
            </div>
          </div>
        </form>
      </div>

      {created && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            style={{
              background: '#fff',
              padding: '2.5rem 2rem',
              borderRadius: '16px',
              minWidth: '360px',
              maxWidth: '440px',
              textAlign: 'center',
              animation: 'popIn .35s cubic-bezier(.175,.885,.32,1.275)',
            }}
          >
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: '#F0FDF4',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.25rem',
                fontSize: '24px',
              }}
            >
              ✓
            </div>
            <h3 style={{ fontWeight: 600, fontSize: '1.2rem', marginBottom: '6px' }}>
              Payslip created
            </h3>
            <p style={{ fontSize: '14px', color: '#6B6A66', marginBottom: '1.75rem' }}>
              Successfully created for <strong>{created.name}</strong>
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  void handlePdf()
                }}
                style={{
                  display: 'block',
                  padding: '10px 20px',
                  background: '#2563EB',
                  color: '#fff',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontWeight: 500,
                }}
              >
                Download PDF
              </a>
              <button
                type="button"
                onClick={resetForm}
                style={{
                  padding: '10px 20px',
                  background: 'transparent',
                  border: '1px solid rgba(0,0,0,0.12)',
                  borderRadius: '8px',
                  color: '#6B6A66',
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                Create another
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
