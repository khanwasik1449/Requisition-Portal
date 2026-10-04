import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/api/axios'

const equipmentOptions = [
  'Audio Recorder', 'Apple Keyboard', 'Apple Pencil', 'Bluetooth Mouse Battery', 'CPU', 'Charger',
  'Dell Laptop Charger', 'Ear Phone / Earphone', 'EPSON L395 Printer', 'Flash Drive / Pen Drive',
  'Graphic Card', 'Hard Disk', 'Head Phone', 'Headphone Connector', 'iPad',
  'iPad Pro Charger (20 Watt)', 'Keyboard', 'Laptop', 'Laptop Bag / Carry Bag', 'Laptop Charger',
  'Laptop Cooler', 'Laptop Stand', 'Modem', 'Monitor', 'Mouse', 'Mouse Pad', 'Multi Plug',
  'Nib (Wacom Intuos CTL6100)', 'Notebook / Diary', 'Original A4 Tech Branded Keyboard and Mouse',
  'Pad', 'Pen Drive', 'Portable Hard Drive', 'Power Supply', 'Printer (Black & White)',
  'Processor', 'RAM', 'RJ Connector', 'Scanner', 'Screen Projector', 'Sound System', 'Speaker',
  'Tab', 'Tab Cover', 'Thermaltake Laptop Stand', 'TV (65")', 'UPS', 'USB Hub',
  'USB Type-C to Type-B Hub', 'Wacom', 'Wacom (Graphic Tab)', 'Wacom Intuos (CTL6100)',
  'Webcam', 'Wireless Mouse Battery',
]

// Exact replica of templates/ict_requisition/form.html
export function ICTCreate() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedEquipment, setSelectedEquipment] = useState<string[]>([])
  const [otherEquipment, setOtherEquipment] = useState('')
  const [otherEnabled, setOtherEnabled] = useState(false)

  const toggleEquipment = (name: string) => {
    setSelectedEquipment((prev) =>
      prev.includes(name) ? prev.filter((e) => e !== name) : [...prev, name]
    )
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')

    const allEquipment = [...selectedEquipment]
    if (otherEnabled && otherEquipment.trim()) {
      allEquipment.push(otherEquipment.trim())
    }

    if (allEquipment.length === 0) {
      setError('Please select at least one equipment item.')
      return
    }

    setIsSubmitting(true)
    try {
      const form = e.currentTarget
      const data = {
        full_name: (form.full_name as HTMLInputElement).value,
        email_address: (form.email_address as HTMLInputElement).value,
        designation: (form.designation as HTMLInputElement).value,
        pin_number: (form.pin_number as HTMLInputElement).value,
        contact_number: (form.contact_number as HTMLInputElement).value,
        requisition_date: (form.requisition_date as HTMLInputElement).value,
        requirement_date: (form.requirement_date as HTMLInputElement).value,
        return_date: (form.return_date as HTMLInputElement).value || null,
        device_equipment: allEquipment,
        equipment_specification: (form.equipment_specification as HTMLTextAreaElement).value,
        purpose: (form.purpose as HTMLTextAreaElement).value,
        supervisor: (form.supervisor as HTMLSelectElement).value,
      }
      await api.post('/ict/', data)
      navigate('/ict')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit requisition.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-10">
        <div className="card">
          <div className="card-header d-flex align-items-center gap-2">
            <i className="bi bi-plus-circle" style={{ color: '#2563eb' }}></i> ICT Requisition Form
          </div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="alert alert-danger py-2 small">{error}</div>}

              <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
                <i className="bi bi-person me-1"></i> Personal Information
              </h6>
              <div className="row mb-3">
                <div className="col-md-4">
                  <label className="form-label">
                    Full Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="full_name"
                    className="form-control"
                    placeholder="Your full name"
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    ICT Email Address <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    name="email_address"
                    className="form-control"
                    placeholder="email@example.com"
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    Designation <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="designation"
                    className="form-control"
                    placeholder="e.g. Software Engineer"
                    required
                  />
                </div>
              </div>

              <div className="row mb-4">
                <div className="col-md-4">
                  <label className="form-label">
                    PIN Number <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="pin_number"
                    className="form-control"
                    placeholder="Staff PIN number"
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    Contact Number <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="contact_number"
                    className="form-control"
                    placeholder="e.g. +254 7XX XXX XXX"
                    required
                  />
                </div>
              </div>

              <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
                <i className="bi bi-calendar me-1"></i> Dates
              </h6>
              <div className="row mb-4">
                <div className="col-md-4">
                  <label className="form-label">
                    Requisition Date <span className="text-danger">*</span>
                  </label>
                  <input type="date" name="requisition_date" className="form-control" required />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    Requirement Date <span className="text-danger">*</span>
                  </label>
                  <input type="date" name="requirement_date" className="form-control" required />
                </div>
                <div className="col-md-4">
                  <label className="form-label">Return Date</label>
                  <input type="date" name="return_date" className="form-control" />
                </div>
              </div>

              <h6 className="fw-bold mb-3" style={{ color: '#2563eb' }}>
                <i className="bi bi-device-ssd me-1"></i> Equipment Details
              </h6>
              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label">
                    Device / Equipment <span className="text-danger">*</span>
                  </label>
                  <div
                    className="border rounded p-3 bg-white"
                    style={{ maxHeight: '280px', overflowY: 'auto' }}
                  >
                    {equipmentOptions.map((item) => (
                      <div className="form-check mb-1" key={item}>
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`eq_${item.replace(/[^a-zA-Z0-9]/g, '_')}`}
                          checked={selectedEquipment.includes(item)}
                          onChange={() => toggleEquipment(item)}
                        />
                        <label
                          className="form-check-label"
                          htmlFor={`eq_${item.replace(/[^a-zA-Z0-9]/g, '_')}`}
                        >
                          {item}
                        </label>
                      </div>
                    ))}
                    <hr className="my-2" />
                    <div className="input-group input-group-sm">
                      <span className="input-group-text">
                        <input
                          className="form-check-input mt-0"
                          type="checkbox"
                          checked={otherEnabled}
                          onChange={(e) => setOtherEnabled(e.target.checked)}
                        />
                      </span>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Type equipment name..."
                        disabled={!otherEnabled}
                        value={otherEquipment}
                        onChange={(e) => setOtherEquipment(e.target.value)}
                      />
                    </div>
                  </div>
                  <small className="text-muted">
                    Check all that apply. Use the field below to add items not listed.
                  </small>
                </div>
                <div className="col-md-6">
                  <label className="form-label">
                    Supervisor <span className="text-danger">*</span>
                  </label>
                  <select name="supervisor" className="form-select" required>
                    <option value="">-- Select Supervisor --</option>
                  </select>
                </div>
              </div>
              <div className="mb-3">
                <label className="form-label">Equipment Specification / Configuration</label>
                <textarea
                  name="equipment_specification"
                  className="form-control"
                  rows={3}
                  placeholder="Detailed specs, model numbers, configuration requirements..."
                />
              </div>
              <div className="mb-4">
                <label className="form-label">
                  Purpose <span className="text-danger">*</span>
                </label>
                <textarea
                  name="purpose"
                  className="form-control"
                  rows={3}
                  placeholder="Why is this equipment needed?"
                  required
                />
              </div>

              <hr />
              <div className="d-flex gap-2">
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  <i className="bi bi-send me-1"></i>{' '}
                  {isSubmitting ? 'Submitting...' : 'Submit Request'}
                </button>
                <Link to="/ict" className="btn btn-outline-secondary">
                  <i className="bi bi-x me-1"></i> Cancel
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
