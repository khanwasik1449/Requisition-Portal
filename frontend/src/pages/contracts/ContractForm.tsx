import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
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

interface EmployeeLookup {
  exists: boolean
  name?: string
  designation?: string
  salary?: number | string | null
  phone?: string | null
  email?: string | null
  tin?: string | null
}

interface Draft {
  pin: string
  name: string
  designation: string
  phone: string
  email: string
  tin: string
  start_date: string
  end_date: string
  salary: string
  new_designation: string
}

const emptyDraft: Draft = {
  pin: '',
  name: '',
  designation: '',
  phone: '',
  email: '',
  tin: '',
  start_date: '',
  end_date: '',
  salary: '',
  new_designation: '',
}

const CONTRACT_TYPES = ['New', 'Extension', 'Revision', 'Renewal'] as const
type ContractType = (typeof CONTRACT_TYPES)[number]

// The .type-desc literals from form.html's four contract-type cards.
const typeDescs: Record<string, string> = {
  New: 'Creates a brand new contract.',
  Extension: 'Extends the existing contract period.',
  Revision: 'Amend existing contract terms such as salary, conditions, or duration.',
  Renewal: 'Issue a fresh contract term, optionally with a new designation.',
}

const typeBadgeClass: Record<string, string> = {
  New: 'badge-blue',
  Extension: 'badge-blue',
  Revision: 'badge-amber',
  Renewal: 'badge-green',
}

function fmtDate(d: string) {
  if (!d) return '—'
  const [y, m, day] = d.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${day} ${months[parseInt(m, 10) - 1]} ${y}`
}

function fmtMoney(v: string) {
  if (!v) return '—'
  return 'BDT ' + Number(v).toLocaleString('en-BD')
}

async function downloadContractPdf(contractId: number, pin: string) {
  const { data } = await api.get<Blob>(`/contracts/${contractId}/pdf/`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `contract_${pin}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// contracts/templates/contracts/form.html -- <style> block, verbatim.
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
    --c-accent-light: #EFF4FF;
    --c-success: #16A34A;
    --c-success-light: #F0FDF4;
    --c-danger: #DC2626;
    --c-danger-light: #FEF2F2;
    --c-amber-light: #FFFBEB;
    --c-amber: #D97706;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--c-bg);
    color: var(--c-text);
  }

  .cc-wrapper {
    max-width: 780px;
    margin: 0 auto;
    padding: 2.5rem 1.5rem;
  }

  /* ── Page header ── */
  .cc-header {
    margin-bottom: 2rem;
  }
  .cc-header h1 {
    font-size: 1.6rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--c-text);
  }
  .cc-header p {
    font-size: 0.875rem;
    color: var(--c-muted);
    margin-top: 4px;
  }

  /* ── Step indicator ── */
  .steps {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 2rem;
  }
  .step {
    display: flex;
    align-items: center;
    gap: 8px;
    position: relative;
  }
  .step-bubble {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 1.5px solid var(--c-border-strong);
    background: var(--c-surface);
    color: var(--c-muted);
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    font-family: 'DM Mono', monospace;
    flex-shrink: 0;
  }
  .step-bubble.active {
    background: var(--c-accent);
    border-color: var(--c-accent);
    color: #fff;
    box-shadow: 0 0 0 4px rgba(37,99,235,0.12);
  }
  .step-bubble.done {
    background: var(--c-success);
    border-color: var(--c-success);
    color: #fff;
  }
  .step-text {
    font-size: 12px;
    font-weight: 500;
    color: var(--c-muted);
    white-space: nowrap;
    transition: color 0.3s;
  }
  .step-text.active { color: var(--c-accent); }
  .step-text.done   { color: var(--c-success); }
  .step-line {
    flex: 1;
    height: 1px;
    background: var(--c-border);
    margin: 0 10px;
    transition: background 0.4s;
  }
  .step-line.done { background: var(--c-success); }

  /* ── Progress bar ── */
  .progress-track {
    height: 3px;
    background: var(--c-border);
    border-radius: 3px;
    margin-bottom: 2rem;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--c-accent), #60A5FA);
    border-radius: 3px;
    transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
  }

  /* ── Card ── */
  .cc-card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .cc-card-body { padding: 1.75rem; }

  .section-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--c-hint);
    margin-bottom: 1.25rem;
  }

  /* ── Grid ── */
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }

  @media (max-width: 600px) {
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
  }

  /* ── Fields ── */
  .field { display: flex; flex-direction: column; gap: 5px; }
  .field label {
    font-size: 13px;
    font-weight: 500;
    color: var(--c-muted);
  }
  .field .req { color: var(--c-danger); margin-left: 2px; }
  .field input,
  .field select {
    height: 40px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    padding: 0 12px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    color: var(--c-text);
    background: var(--c-bg);
    transition: border-color 0.2s, box-shadow 0.2s;
    outline: none;
    width: 100%;
  }
  .field input:focus,
  .field select:focus {
    border-color: var(--c-accent);
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
    background: #fff;
  }
  .field input:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .field input.error { border-color: var(--c-danger); }
  .field-hint {
    font-size: 11px;
    color: var(--c-danger);
    display: none;
    margin-top: 2px;
  }
  .field-hint.visible { display: block; }

  /* ── Contract type cards ── */
  .type-grid { display: flex; flex-direction: column; gap: 10px; }
  .type-card {
    border: 1px solid var(--c-border);
    border-radius: var(--radius-sm);
    padding: 14px 16px;
    display: flex;
    align-items: center;
    gap: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--c-bg);
    user-select: none;
  }
  .type-card:hover {
    border-color: var(--c-accent);
    background: var(--c-accent-light);
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }
  .type-card.selected {
    border-color: var(--c-accent);
    background: var(--c-accent-light);
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
  }
  .type-icon {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }
  .type-info { flex: 1; }
  .type-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--c-text);
    margin-bottom: 2px;
  }
  .type-desc { font-size: 12px; color: var(--c-muted); }
  .type-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
  }
  .badge-blue   { background: var(--c-accent-light); color: var(--c-accent); }
  .badge-amber  { background: var(--c-amber-light); color: var(--c-amber); }
  .badge-green  { background: var(--c-success-light); color: var(--c-success); }

  .type-radio {
    width: 18px; height: 18px;
    border-radius: 50%;
    border: 2px solid var(--c-border-strong);
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s;
  }
  .type-card.selected .type-radio {
    border-color: var(--c-accent);
    background: var(--c-accent);
  }
  .type-card.selected .type-radio::after {
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #fff;
  }

  /* ── Divider ── */
  .divider {
    height: 1px;
    background: var(--c-border);
    margin: 1.5rem 0;
  }

  /* ── Navigation ── */
  .nav-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem 1.75rem;
    border-top: 1px solid var(--c-border);
    background: var(--c-bg);
  }
  .step-counter {
    font-size: 12px;
    color: var(--c-hint);
    font-family: 'DM Mono', monospace;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 20px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.18s;
    text-decoration: none;
  }
  .btn-ghost {
    background: transparent;
    border-color: var(--c-border-strong);
    color: var(--c-muted);
  }
  .btn-ghost:hover {
    background: var(--c-bg);
    color: var(--c-text);
  }
  .btn-primary {
    background: var(--c-accent);
    color: #fff;
    border-color: var(--c-accent);
  }
  .btn-primary:hover {
    background: #1D4ED8;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
  }
  .btn-primary:active { transform: scale(0.98); }
  .btn-success {
    background: var(--c-success);
    color: #fff;
    border-color: var(--c-success);
  }
  .btn-success:hover {
    background: #15803D;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(22,163,74,0.3);
  }
  .btn-success:disabled { opacity: .6; cursor: not-allowed; }

  /* ── Review panel ── */
  .review-table { width: 100%; border-collapse: collapse; }
  .review-table tr { border-bottom: 1px solid var(--c-border); }
  .review-table tr:last-child { border-bottom: none; }
  .review-table td {
    padding: 10px 0;
    font-size: 14px;
  }
  .review-table td:first-child {
    color: var(--c-muted);
    width: 45%;
    font-weight: 400;
  }
  .review-table td:last-child {
    font-weight: 500;
    color: var(--c-text);
    text-align: right;
  }

  /* ── Alert box ── */
  .alert {
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    display: none;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
  }
  .alert.visible { display: flex; }
  .alert-error {
    background: var(--c-danger-light);
    color: var(--c-danger);
    border: 1px solid rgba(220,38,38,0.15);
  }
  .alert-warning {
    background: var(--c-amber-light);
    color: var(--c-amber);
    border: 1px solid rgba(217,119,6,0.15);
  }

  /* ── Success state ── */
  .success-state {
    text-align: center;
    padding: 3rem 2rem;
  }
  .success-icon {
    width: 64px; height: 64px;
    border-radius: 50%;
    background: var(--c-success-light);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 1.25rem;
    font-size: 26px;
    animation: popIn 0.4s cubic-bezier(0.175,0.885,0.32,1.275);
  }
  @keyframes popIn {
    from { transform: scale(0.5); opacity: 0; }
    to   { transform: scale(1); opacity: 1; }
  }
  .success-state h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 6px;
  }
  .success-state p {
    font-size: 14px;
    color: var(--c-muted);
    margin-bottom: 1.75rem;
  }
  .btn-group { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }

  /* ── Panel transitions ── */
  .panel {
    display: none;
    animation: fadeSlide 0.25s ease;
  }
  .panel.active { display: block; }
  @keyframes fadeSlide {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`

interface FieldErrors {
  pin: boolean
  name: boolean
  startDate: boolean
  endDate: boolean
  salary: boolean
}

const noErrors: FieldErrors = { pin: false, name: false, startDate: false, endDate: false, salary: false }

// Replica of contracts/templates/contracts/form.html
export function ContractForm() {
  const queryClient = useQueryClient()

  const [step, setStep] = useState(1)
  const [selectedType, setSelectedType] = useState<ContractType>('New')
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [errors, setErrors] = useState<FieldErrors>(noErrors)
  const [showNewFields, setShowNewFields] = useState(false)
  const [created, setCreated] = useState<Contract | null>(null)
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)
  const ownsFlash = useRefSafe()

  // A failed POST re-renders this page with Django's messages block (main
  // never leaves /hr/contracts/create), so the sentence is shown inline and
  // the shared slot -- which only HrLayout drains on a navigation -- is
  // dropped again rather than leaking onto the next page.
  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  const dateWarn = Boolean(
    draft.start_date && draft.end_date && draft.end_date <= draft.start_date,
  )

  function setField<K extends keyof Draft>(key: K, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }))
  }

  function selectType(t: ContractType) {
    setSelectedType(t)
    if (t !== 'Renewal') {
      setDraft((prev) => ({ ...prev, new_designation: '' }))
    }
  }

  /** form.html's validate(step) -- run only when moving forward. */
  function validate(current: number): boolean {
    if (current === 1) {
      const ok = Boolean(draft.pin.trim()) && Boolean(draft.name.trim())
      setErrors({
        ...noErrors,
        pin: !draft.pin.trim(),
        name: !draft.name.trim(),
      })
      return ok
    }
    if (current === 3) {
      let ok = true
      const next = { ...noErrors }
      if (dateWarn) ok = false
      if (!draft.start_date) {
        next.startDate = true
        ok = false
      }
      if (!draft.end_date) {
        next.endDate = true
        ok = false
      }
      if (!draft.salary || Number(draft.salary) <= 0) {
        next.salary = true
        ok = false
      }
      setErrors(next)
      return ok
    }
    return true
  }

  function goTo(target: number) {
    if (target > step) {
      if (!validate(step)) return
    }
    setStep(target)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // form.html blocks Enter inside steps 1-3 and advances instead.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && step < 4) {
        e.preventDefault()
        if (step === 1) goTo(2)
        else if (step === 2) goTo(3)
        else if (step === 3) goTo(4)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  // form.html's fetchEmployeeDetails() -- fired on the PIN field's blur.
  async function fetchEmployeeDetails() {
    const pin = draft.pin
    if (!pin) return
    try {
      const { data } = await api.get<EmployeeLookup>('/employees/lookup/', {
        params: { pin },
      })
      if (data.exists) {
        setDraft((prev) => ({
          ...prev,
          name: data.name ?? '',
          designation: data.designation ?? '',
          salary: data.salary === null || data.salary === undefined ? '' : String(data.salary),
          phone: data.phone || '',
          email: data.email || '',
          tin: data.tin || '',
        }))
        setShowNewFields(false)
      } else {
        setDraft((prev) => ({
          ...prev,
          name: '',
          designation: '',
          salary: '',
          phone: '',
          email: '',
          tin: '',
        }))
        setShowNewFields(true)
      }
    } catch (error) {
      console.error('Error fetching employee:', error)
    }
  }

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        pin: draft.pin,
        name: draft.name,
        designation: draft.designation,
        new_designation: draft.new_designation,
        start_date: draft.start_date,
        end_date: draft.end_date,
        salary: draft.salary,
        contract_type: selectedType,
      }
      return (await api.post<Contract>('/contracts/', payload)).data
    },
    onSuccess: (data) => {
      ownsFlash.current = false
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      setCreated(data)
      setNotice(null)
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    },
  })

  async function downloadCreatedPdf() {
    if (!created) return
    try {
      await downloadContractPdf(created.id, created.pin)
    } catch (err) {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    }
  }

  /** main re-renders create_contract from scratch after the popup's reload. */
  function createAnother() {
    setCreated(null)
    setDraft(emptyDraft)
    setErrors(noErrors)
    setSelectedType('New')
    setShowNewFields(false)
    setNotice(null)
    setStep(1)
  }

  const pct = [25, 50, 75, 100][step - 1]

  const stepsBar = [
    { n: 1, label: 'Employee' },
    { n: 2, label: 'Type' },
    { n: 3, label: 'Details' },
    { n: 4, label: 'Review' },
  ]

  const typeCards: Array<{
    type: ContractType
    icon: string
    iconBg: string
    name: string
    desc: string
  }> = [
    { type: 'New', icon: '📄', iconBg: '#EFF6FF', name: 'New Contract', desc: typeDescs.New },
    { type: 'Extension', icon: '📅', iconBg: '#EFF6FF', name: 'Extension', desc: typeDescs.Extension },
    { type: 'Revision', icon: '✏️', iconBg: '#FFFBEB', name: 'Revision', desc: typeDescs.Revision },
    { type: 'Renewal', icon: '🔄', iconBg: '#F0FDF4', name: 'Renewal', desc: typeDescs.Renewal },
  ]

  const arrowRight = (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ verticalAlign: 'middle' }}>
      <path
        d="M3 8h10M9 4l4 4-4 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )

  const arrowLeft = (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style={{ verticalAlign: 'middle' }}>
      <path
        d="M13 8H3M7 4L3 8l4 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )

  const rvName = draft.name || '—'
  const rvPinDesig = `PIN: ${draft.pin || '—'}${
    draft.designation ? ` · ${draft.designation}` : ''
  }`

  const reviewRows: Array<[string, string]> = [
    ['Start date', fmtDate(draft.start_date)],
    ['End date', fmtDate(draft.end_date)],
    ['Salary', fmtMoney(draft.salary)],
  ]
  if (selectedType === 'Renewal') {
    reviewRows.push(['New designation', draft.new_designation || '—'])
  }

  return (
    <>
      <PageStyle css={css} />
      <link
        href={'https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap'}
        rel="stylesheet"
      />

      {notice && (
        <div className={`app-message ${notice.level}`}>
          <span className="msg-close" onClick={() => setNotice(null)}>
            &times;
          </span>
          {notice.text}
        </div>
      )}

      <div className="cc-wrapper">
        <div className="cc-header">
          <h1>Create Contract</h1>
          <p>Complete each step carefully — all required fields must be filled before submission.</p>
        </div>

        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>

        <div className="steps">
          {stepsBar.map((s, i) => (
            <div key={s.n} style={{ display: 'contents' }}>
              <div className="step">
                <div
                  className={`step-bubble ${s.n < step ? 'done' : s.n === step ? 'active' : ''}`}
                >
                  {s.n < step ? '✓' : s.n}
                </div>
                <span className={`step-text ${s.n < step ? 'done' : s.n === step ? 'active' : ''}`}>
                  {s.label}
                </span>
              </div>
              {i < stepsBar.length - 1 && (
                <div className={`step-line ${s.n < step ? 'done' : ''}`} />
              )}
            </div>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            save.mutate()
          }}
        >
          <div className="cc-card">
            {/* ── STEP 1: Employee ── */}
            <div className={`panel ${step === 1 ? 'active' : ''}`}>
              <div className="cc-card-body">
                <div className="section-label">Employee information</div>
                <div className="grid-3">
                  <div className="field">
                    <label>
                      PIN <span className="req">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. EMP-2024-001"
                      autoComplete="off"
                      className={errors.pin ? 'error' : ''}
                      value={draft.pin}
                      onChange={(e) => setField('pin', e.target.value)}
                      onBlur={fetchEmployeeDetails}
                    />
                    <span className={`field-hint ${errors.pin ? 'visible' : ''}`}>
                      PIN is required.
                    </span>
                  </div>
                  <div className="field">
                    <label>
                      Full name <span className="req">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="First and last name"
                      className={errors.name ? 'error' : ''}
                      value={draft.name}
                      onChange={(e) => setField('name', e.target.value)}
                    />
                    <span className={`field-hint ${errors.name ? 'visible' : ''}`}>
                      Name is required.
                    </span>
                  </div>
                  <div className="field">
                    <label>Current designation</label>
                    <input
                      type="text"
                      placeholder="e.g. Senior Analyst"
                      value={draft.designation}
                      onChange={(e) => setField('designation', e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ display: showNewFields ? 'block' : 'none' }}>
                  <div className="section-label" style={{ marginTop: '20px' }}>
                    New Employee Details
                  </div>
                  <div className="grid-3">
                    <div className="field">
                      <label>Phone Number</label>
                      <input
                        type="text"
                        placeholder="Phone Number"
                        value={draft.phone}
                        onChange={(e) => setField('phone', e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>Email Address</label>
                      <input
                        type="email"
                        placeholder="Email (optional)"
                        value={draft.email}
                        onChange={(e) => setField('email', e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label>TIN Number</label>
                      <input
                        type="text"
                        placeholder="TIN Number"
                        value={draft.tin}
                        onChange={(e) => setField('tin', e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </div>
              <div className="nav-row">
                <span className="step-counter">Step 1 / 4</span>
                <button type="button" className="btn btn-primary" onClick={() => goTo(2)}>
                  Continue {arrowRight}
                </button>
              </div>
            </div>

            {/* ── STEP 2: Contract Type ── */}
            <div className={`panel ${step === 2 ? 'active' : ''}`}>
              <div className="cc-card-body">
                <div className="section-label">Choose contract type</div>
                <div className="type-grid">
                  {typeCards.map((card) => (
                    <div
                      key={card.type}
                      className={`type-card ${selectedType === card.type ? 'selected' : ''}`}
                      onClick={() => selectType(card.type)}
                    >
                      <div className="type-radio">{selectedType === card.type && <div />}</div>
                      <div className="type-icon" style={{ background: card.iconBg }}>
                        {card.icon}
                      </div>
                      <div className="type-info">
                        <div className="type-name">{card.name}</div>
                        <div className="type-desc">{card.desc}</div>
                      </div>
                      <span className={`type-badge ${typeBadgeClass[card.type]}`}>
                        {card.type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="nav-row">
                <button type="button" className="btn btn-ghost" onClick={() => goTo(1)}>
                  {arrowLeft} Back
                </button>
                <span className="step-counter">Step 2 / 4</span>
                <button type="button" className="btn btn-primary" onClick={() => goTo(3)}>
                  Continue {arrowRight}
                </button>
              </div>
            </div>

            {/* ── STEP 3: Details ── */}
            <div className={`panel ${step === 3 ? 'active' : ''}`}>
              <div className="cc-card-body">
                <div className="section-label">Contract details</div>
                <div className="grid-2">
                  <div className="field">
                    <label>
                      Start date <span className="req">*</span>
                    </label>
                    <input
                      type="date"
                      required
                      className={errors.startDate ? 'error' : ''}
                      value={draft.start_date}
                      onChange={(e) => setField('start_date', e.target.value)}
                    />
                    <span className={`field-hint ${errors.startDate ? 'visible' : ''}`}>
                      Start date is required.
                    </span>
                  </div>
                  <div className="field">
                    <label>
                      End date <span className="req">*</span>
                    </label>
                    <input
                      type="date"
                      required
                      className={errors.endDate ? 'error' : ''}
                      value={draft.end_date}
                      onChange={(e) => setField('end_date', e.target.value)}
                    />
                    <span className={`field-hint ${errors.endDate ? 'visible' : ''}`}>
                      End date is required.
                    </span>
                  </div>
                </div>

                <div className={`alert alert-warning ${dateWarn ? 'visible' : ''}`}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path
                      d="M8 6v3M8 11h.01M2.5 13.5h11L8 2.5 2.5 13.5z"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  End date must be after start date.
                </div>

                <div className="divider" />

                <div className="grid-2">
                  <div className="field">
                    <label>
                      Salary (BDT) <span className="req">*</span>
                    </label>
                    <input
                      type="number"
                      placeholder="0"
                      min="0"
                      required
                      className={errors.salary ? 'error' : ''}
                      value={draft.salary}
                      onChange={(e) => setField('salary', e.target.value)}
                    />
                    <span className={`field-hint ${errors.salary ? 'visible' : ''}`}>
                      Salary is required.
                    </span>
                  </div>
                  <div className="field">
                    <label>
                      New designation{' '}
                      <span
                        style={{
                          fontSize: '11px',
                          color: selectedType === 'Renewal' ? 'var(--c-accent)' : 'var(--c-hint)',
                        }}
                      >
                        {selectedType === 'Renewal' ? '(required for Renewal)' : '(only for Renewal)'}
                      </span>
                    </label>
                    <input
                      type="text"
                      placeholder={selectedType === 'Renewal' ? 'Enter new role title' : 'New role title'}
                      disabled={selectedType !== 'Renewal'}
                      value={draft.new_designation}
                      onChange={(e) => setField('new_designation', e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <div className="nav-row">
                <button type="button" className="btn btn-ghost" onClick={() => goTo(2)}>
                  {arrowLeft} Back
                </button>
                <span className="step-counter">Step 3 / 4</span>
                <button type="button" className="btn btn-primary" onClick={() => goTo(4)}>
                  Review {arrowRight}
                </button>
              </div>
            </div>

            {/* ── STEP 4: Review ── */}
            <div className={`panel ${step === 4 ? 'active' : ''}`}>
              <div className="cc-card-body">
                <div className="section-label">Review &amp; confirm</div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '16px',
                    marginBottom: '1.5rem',
                  }}
                >
                  <div
                    style={{
                      background: 'var(--c-bg)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '14px 16px',
                      border: '1px solid var(--c-border)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--c-hint)',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '.06em',
                        marginBottom: '8px',
                      }}
                    >
                      Employee
                    </div>
                    <div
                      style={{ fontSize: '15px', fontWeight: 600, color: 'var(--c-text)' }}
                    >
                      {rvName}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--c-muted)', marginTop: '2px' }}>
                      {rvPinDesig}
                    </div>
                  </div>
                  <div
                    style={{
                      background: 'var(--c-bg)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '14px 16px',
                      border: '1px solid var(--c-border)',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--c-hint)',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '.06em',
                        marginBottom: '8px',
                      }}
                    >
                      Contract type
                    </div>
                    <div style={{ marginBottom: '4px' }}>
                      <span className={`type-badge ${typeBadgeClass[selectedType]}`}>
                        {selectedType}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--c-muted)' }}>
                      {typeDescs[selectedType]}
                    </div>
                  </div>
                </div>

                <table className="review-table">
                  <tbody>
                    {reviewRows.map(([label, value]) => (
                      <tr key={label}>
                        <td>{label}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div
                  style={{
                    marginTop: '1.25rem',
                    padding: '12px 14px',
                    background: 'var(--c-bg)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--c-border)',
                    fontSize: '13px',
                    color: 'var(--c-muted)',
                    lineHeight: '1.5',
                  }}
                >
                  Please verify all details above. Once submitted, a PDF contract will be generated
                  and available for download.
                </div>
              </div>
              <div className="nav-row">
                <button type="button" className="btn btn-ghost" onClick={() => goTo(3)}>
                  {arrowLeft} Edit
                </button>
                <span className="step-counter">Step 4 / 4</span>
                <button type="submit" className="btn btn-success" disabled={save.isPending}>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="none"
                    style={{ verticalAlign: 'middle' }}
                  >
                    <path
                      d="M2 8l4 4 8-8"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Submit contract
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* ── SUCCESS POPUP (created_contract) ── */}
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
              boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
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
            <h3
              style={{
                fontFamily: "'DM Sans',sans-serif",
                fontWeight: 600,
                fontSize: '1.2rem',
                marginBottom: '6px',
              }}
            >
              Contract created
            </h3>
            <p style={{ fontSize: '14px', color: '#6B6A66', marginBottom: '1.75rem' }}>
              Successfully created for <strong>{created.name}</strong>
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={downloadCreatedPdf}
                style={{
                  display: 'block',
                  padding: '10px 20px',
                  background: '#2563EB',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontFamily: "'DM Sans',sans-serif",
                  fontWeight: 500,
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                Download PDF
              </button>
              <Link
                to={`/hr/contracts/email/${created.id}`}
                style={{
                  display: 'block',
                  padding: '10px 20px',
                  background: '#059669',
                  color: '#fff',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontFamily: "'DM Sans',sans-serif",
                  fontWeight: 500,
                  fontSize: '14px',
                }}
              >
                📧 Send Email
              </Link>
              <button
                onClick={createAnother}
                style={{
                  padding: '10px 20px',
                  background: 'transparent',
                  border: '1px solid rgba(0,0,0,0.12)',
                  borderRadius: '8px',
                  color: '#6B6A66',
                  fontFamily: "'DM Sans',sans-serif",
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

/** `useRef` without pulling React's import order out of shape. */
function useRefSafe() {
  return useState<{ current: boolean }>(() => ({ current: false }))[0]
}
