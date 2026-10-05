import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { useStaffDefaults } from '@/lib/staffDefaults'

// Replica of templates/transport_requisition/form.html (multi-step wizard)
const stepTitles = ['Personal Information', 'Trip Details', 'Additional Information', 'Review']

const safetyNotes = [
  'Wear a seatbelt at all times.',
  'Report any unsafe driving to your supervisor.',
  'Do not overload the vehicle beyond its passenger capacity.',
  'Keep valuables out of plain sight.',
  'Confirm the vehicle registration before boarding.',
]

const vendorNotes = [
  'Provide at least 24 hours advance notice for bookings.',
  'Trips outside the city require Grants approval.',
  'Fuel and toll costs are charged to the project budget code.',
  'The driver will call 30 minutes before the pick-up time.',
]

interface FieldConfig {
  name: string
  label: string
  type: string
  required?: boolean
  placeholder?: string
  options?: { value: string; label: string }[]
}

const stepFields: FieldConfig[][] = [
  // Step 1: Personal Information
  [
    { name: 'full_name', label: 'Full Name', type: 'text', required: true, placeholder: 'Your full name' },
    { name: 'email_address', label: 'Email Address', type: 'email', required: true, placeholder: 'email@example.com' },
    { name: 'mobile_number', label: 'Mobile Number', type: 'text', required: true, placeholder: 'e.g. 017XX-XXXXXX' },
    { name: 'designation', label: 'Designation', type: 'text', required: true, placeholder: 'e.g. Software Engineer' },
    { name: 'pin', label: 'PIN', type: 'text', required: true, placeholder: 'Staff PIN number' },
    { name: 'num_passengers', label: 'Number of Passengers', type: 'number', required: true, placeholder: '1' },
  ],
  // Step 2: Trip Details
  [
    {
      name: 'vehicle_type', label: 'Vehicle Type', type: 'select', required: true,
      options: [
        { value: '', label: '-- Select Vehicle Type --' },
        { value: 'sedan', label: 'Sedan' },
        { value: 'suv', label: 'SUV' },
        { value: 'van', label: 'Van' },
        { value: 'bus', label: 'Bus' },
        { value: 'other', label: 'Other' },
      ],
    },
    { name: 'pick_up_date', label: 'Pick-up Date', type: 'date', required: true },
    { name: 'pick_up_time', label: 'Pick-up Time', type: 'time', required: true },
    { name: 'pick_up_location', label: 'Pick-up Location', type: 'text', required: true, placeholder: 'e.g. BRAC IED Office' },
    { name: 'destination', label: 'Destination', type: 'text', required: true, placeholder: 'e.g. BRAC Head Office' },
    { name: 'drop_off_date', label: 'Drop-off Date', type: 'date', required: true },
    { name: 'drop_off_time', label: 'Drop-off Time', type: 'time', required: true },
    { name: 'drop_off_location', label: 'Drop-off Location', type: 'text', required: true, placeholder: 'e.g. BRAC IED Office' },
  ],
  // Step 3: Additional Information
  [
    { name: 'travelling_reason', label: 'Travelling Reason', type: 'textarea', required: true, placeholder: 'Why do you need this trip?' },
    { name: 'project_name_code', label: 'Project Name & Code', type: 'text', required: true, placeholder: 'e.g. Project Alpha (PRJ-001)' },
    { name: 'budget_code', label: 'Budget Code', type: 'text', required: true, placeholder: 'e.g. BC-2024-001' },
    { name: 'comments_remarks', label: 'Comments / Remarks', type: 'textarea', placeholder: 'Any additional notes...' },
  ],
  // Step 4: Review (handled separately)
  [],
]

export function TransportCreate() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [showSafety, setShowSafety] = useState(false)
  const [showVendor, setShowVendor] = useState(false)

  const staffDefaults = useStaffDefaults()

  // Pre-fill the applicant's personal details from their account. The auth
  // call resolves after mount on a hard refresh of this (public) route, so the
  // values are pushed in as they arrive — and never over anything the
  // applicant has already typed.
  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      full_name: prev.full_name || staffDefaults.full_name,
      email_address: prev.email_address || staffDefaults.email_address,
      mobile_number: prev.mobile_number || staffDefaults.mobile_number,
    }))
  }, [staffDefaults.full_name, staffDefaults.email_address, staffDefaults.mobile_number])

  const totalSteps = stepTitles.length

  const handleFieldChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const validateStep = (step: number): boolean => {
    const fields = stepFields[step - 1]
    if (!fields) return true
    for (const field of fields) {
      if (field.required && !formData[field.name]?.trim()) {
        setError(`Please fill in: ${field.label}`)
        return false
      }
    }
    setError('')
    return true
  }

  const goNext = () => {
    if (!validateStep(currentStep)) return
    if (currentStep < totalSteps) setCurrentStep(currentStep + 1)
  }

  const goBack = () => {
    setError('')
    if (currentStep > 1) setCurrentStep(currentStep - 1)
  }

  const handleSubmit = async () => {
    setError('')
    setIsSubmitting(true)
    try {
      await api.post('/transport/', formData)
      navigate('/transport')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit requisition.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const progressPercent = ((currentStep - 1) / (totalSteps - 1)) * 100

  const renderField = (field: FieldConfig) => {
    const value = formData[field.name] || ''
    const label = (
      <label className="form-label">
        {field.label} {field.required && <span className="text-danger">*</span>}
      </label>
    )

    if (field.type === 'select') {
      return (
        <div className="vs-field" key={field.name}>
          {label}
          <select
            className="form-select"
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            required={field.required}
          >
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )
    }

    if (field.type === 'textarea') {
      return (
        <div className="vs-field" key={field.name}>
          {label}
          <textarea
            className="form-control"
            rows={3}
            placeholder={field.placeholder}
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            required={field.required}
          />
        </div>
      )
    }

    return (
      <div className="vs-field" key={field.name}>
        {label}
        <input
          type={field.type}
          className="form-control"
          placeholder={field.placeholder}
          value={value}
          onChange={(e) => handleFieldChange(field.name, e.target.value)}
          required={field.required}
        />
      </div>
    )
  }

  const renderReview = () => (
    <div className="vs-review">
      <h4>Review Your Information</h4>
      <dl>
        {stepFields.flat().map(
          (field) =>
            formData[field.name] && (
              <div key={field.name} style={{ display: 'contents' }}>
                <dt>{field.label}</dt>
                <dd>{formData[field.name]}</dd>
              </div>
            )
        )}
      </dl>
    </div>
  )

  return (
    <>
      <style>{`
        .vs-req{ color:#DC2626; font-weight:700; margin-left:2px; }
        .vs-rail{ display:flex; align-items:flex-start; list-style:none; margin:0 0 14px; padding:0; gap:0; }
        .vs-node{ flex:1 1 0; min-width:0; position:relative; }
        .vs-node-btn{ display:flex; flex-direction:column; align-items:center; gap:7px; background:none; border:0; padding:0; width:100%; cursor:pointer; font:inherit; color:inherit; }
        .vs-dot{ width:32px; height:32px; border-radius:50%; background:#fff; border:2px solid #CBD5E1; color:#94A3B8; display:flex; align-items:center; justify-content:center; font-size:.82rem; font-weight:700; position:relative; z-index:2; transition:.15s ease; }
        .vs-tick{ display:none; font-size:.95rem; }
        .vs-node:not(:last-child)::after{ content:''; position:absolute; top:16px; left:50%; right:-50%; height:2px; background:#E2E8F0; z-index:1; }
        .vs-label{ font-size:.72rem; font-weight:600; color:#94A3B8; text-align:center; line-height:1.3; padding:0 4px; }
        .vs-node.done .vs-dot{ background:#0EA5E9; border-color:#0EA5E9; color:#fff; }
        .vs-node.done .vs-label{ color:#0369A1; }
        .vs-node.done:not(:last-child)::after{ background:#0EA5E9; }
        .vs-node.active .vs-dot{ background:var(--primary,#2563EB); border-color:var(--primary,#2563EB); color:#fff; box-shadow:0 0 0 4px rgba(37,99,235,.14); }
        .vs-node.active .vs-label{ color:#0F172A; }
        .vs-node.done .vs-num{ display:none; }
        .vs-node.done .vs-tick{ display:block; }
        .vs-bar{ height:4px; background:#E2E8F0; border-radius:99px; overflow:hidden; }
        .vs-bar-fill{ display:block; height:100%; background:var(--primary,#2563EB); transition:width .2s ease; }
        .vs-count{ font-size:.75rem; color:#64748B; margin:8px 0 0; }
        .vs-intro{ font-size:.92rem; color:#475569; margin-bottom:14px; }
        .vs-note{ border:1px solid #E2E8F0; border-radius:12px; margin-bottom:8px; background:#F8FAFC; }
        .vs-note > summary{ cursor:pointer; padding:10px 15px; font-size:.87rem; font-weight:600; list-style:none; }
        .vs-note > summary::-webkit-details-marker{ display:none; }
        .vs-note > summary::before{ content:'\\25B8'; display:inline-block; margin-right:9px; color:#64748B; transition:transform .15s ease; }
        .vs-note[open] > summary::before{ transform:rotate(90deg); }
        .vs-note-body{ padding:0 15px 13px 34px; font-size:.84rem; color:#475569; }
        .vs-note-body ul{ padding-left:18px; margin-bottom:0; }
        .vs-note-body li{ margin-bottom:2px; }
        .vs-title{ font-size:1.05rem; font-weight:700; margin:22px 0 0; letter-spacing:-.01em; }
        .vs-rule{ height:1px; background:#E2E8F0; margin:10px 0 18px; }
        .vs-field{ margin-bottom:20px; }
        .vs-field .form-label{ font-weight:600; font-size:.9rem; margin-bottom:5px; }
        .vs-field .form-control, .vs-field .form-select{ border-radius:10px; }
        .vs-review{ background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:14px 16px; margin:6px 0 18px; font-size:.86rem; }
        .vs-review h4{ font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#64748B; margin:0 0 10px; }
        .vs-review dl{ display:grid; grid-template-columns:auto 1fr; gap:6px 14px; margin:0; }
        .vs-review dt{ color:#64748B; font-weight:600; }
        .vs-review dd{ margin:0; color:#0F172A; }
        .vs-nav{ display:flex; gap:10px; margin-top:6px; }
        .vs-help{ font-size:.83rem; color:#64748B; margin:18px 0 0; }
        .vs-wait{ font-size:.8rem; color:#64748B; margin:0 0 6px; }
        @media (max-width:768px){ .vs-label{ display:none; } }
      `}</style>

      <div className="row justify-content-center">
        <div className="col-lg-10">
          <div className="card">
            <div className="card-header">
              <strong>BRAC IED Vehicle Requisition Form</strong>
            </div>
            <div className="card-body">
              {/* Progress rail */}
              <ol className="vs-rail">
                {stepTitles.map((title, index) => {
                  const stepNum = index + 1
                  const state = stepNum < currentStep ? 'done' : stepNum === currentStep ? 'active' : ''
                  return (
                    <li className={`vs-node ${state}`} key={title}>
                      <button type="button" className="vs-node-btn" onClick={() => stepNum <= currentStep && setCurrentStep(stepNum)}>
                        <span className="vs-dot">
                          <span className="vs-num">{stepNum}</span>
                          <i className="bi bi-check-lg vs-tick"></i>
                        </span>
                        <span className="vs-label">{title}</span>
                      </button>
                    </li>
                  )
                })}
              </ol>

              <div className="vs-bar">
                <span className="vs-bar-fill" style={{ width: `${progressPercent}%` }}></span>
              </div>

              <p className="vs-count">
                Step <span>{currentStep}</span> of {totalSteps}
              </p>

              {/* Error */}
              {error && (
                <div className="alert alert-danger py-2 small" role="alert">
                  {error}
                </div>
              )}

              {/* Steps */}
              <div className="vs-step">
                {currentStep === 1 && (
                  <>
                    <div className="vs-intro">
                      <p>
                        Please fill this form carefully. Use the correct budget code for your
                        department — an incorrect code can cancel the booking.
                      </p>
                    </div>

                    <details className="vs-note" open={showSafety} onToggle={(e) => setShowSafety((e.target as HTMLDetailsElement).open)}>
                      <summary>
                        <i className="bi bi-shield-check"></i> DOS AND DON'TS FOR SAFE JOURNEY
                      </summary>
                      <div className="vs-note-body">
                        <p className="fw-semibold mb-1">Your responsibility</p>
                        <ul>
                          {safetyNotes.map((note, i) => (
                            <li key={i}>{note}</li>
                          ))}
                        </ul>
                        <p className="fw-semibold mb-1 mt-3">The driver will</p>
                        <ul>
                          <li>Not take food, smoke, drink or drugs while driving.</li>
                          <li>Not use a mobile phone while driving.</li>
                          <li>Not gossip with passengers or play music or video.</li>
                          <li>Take a 10–15 minute break every 2 hours on long journeys.</li>
                          <li>Avoid travelling at midnight unless it is an emergency.</li>
                          <li>Behave in a gender-friendly manner.</li>
                        </ul>
                      </div>
                    </details>

                    <details className="vs-note" open={showVendor} onToggle={(e) => setShowVendor((e.target as HTMLDetailsElement).open)}>
                      <summary>
                        <i className="bi bi-journal-check"></i> VENDOR NOTES
                      </summary>
                      <div className="vs-note-body">
                        <ul>
                          {vendorNotes.map((note, i) => (
                            <li key={i}>{note}</li>
                          ))}
                        </ul>
                      </div>
                    </details>

                    <div className="vs-rule"></div>
                    {stepFields[0].map(renderField)}
                  </>
                )}

                {currentStep > 1 && currentStep < totalSteps && (
                  <>
                    <h3 className="vs-title">{stepTitles[currentStep - 1]}</h3>
                    <div className="vs-rule"></div>
                    {stepFields[currentStep - 1].map(renderField)}
                  </>
                )}

                {currentStep === totalSteps && (
                  <>
                    <h3 className="vs-title">Review & Submit</h3>
                    <div className="vs-rule"></div>
                    {renderReview()}
                    <p className="vs-wait">
                      After submitting, please wait up to 15 minutes to receive the "Car Requisition
                      Received" email. You will also be told the driver's name by email shortly. If
                      nothing arrives, you may submit again.
                    </p>
                  </>
                )}
              </div>

              {/* Nav */}
              <div className="vs-nav">
                {currentStep > 1 && (
                  <button type="button" className="btn btn-outline-secondary" onClick={goBack}>
                    Back
                  </button>
                )}
                {currentStep < totalSteps ? (
                  <button type="button" className="btn btn-primary" onClick={goNext}>
                    Next
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                  >
                    <i className="bi bi-send me-1"></i>{' '}
                    {isSubmitting ? 'Submitting...' : 'Submit'}
                  </button>
                )}
              </div>

              <p className="vs-help">
                For any help, email <a href="mailto:ict.support@bracied.com">ict.support@bracied.com</a>{' '}
                or call <a href="tel:+8801700000000">+880 1700-000000</a>.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
