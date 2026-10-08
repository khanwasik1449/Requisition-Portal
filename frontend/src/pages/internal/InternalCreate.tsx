import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { FormLoading } from '@/components/FormLoading'
import { useStaffDefaults } from '@/lib/staffDefaults'

interface ItemRow {
  name: string
  quantity: number
  purpose: string
}

// Exact replica of templates/internal_requisition/form.html
export function InternalCreate() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [items, setItems] = useState<ItemRow[]>([{ name: '', quantity: 1, purpose: '' }])
  const staffDefaults = useStaffDefaults()

  // The employee lookup is async and `defaultValue` is only read on mount, so
  // hold the form until it lands — otherwise the PIN stays blank.
  if (staffDefaults.loading) return <FormLoading />

  const addItem = () => {
    setItems([...items, { name: '', quantity: 1, purpose: '' }])
  }

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index))
    }
  }

  const updateItem = (index: number, field: keyof ItemRow, value: string | number) => {
    const updated = [...items]
    updated[index] = { ...updated[index], [field]: value }
    setItems(updated)
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const form = e.currentTarget
      const data = {
        email_address: (form.email_address as HTMLInputElement).value,
        full_name: (form.full_name as HTMLInputElement).value,
        mobile_number: (form.mobile_number as HTMLInputElement).value,
        designation: (form.designation as HTMLInputElement).value,
        pin: (form.pin as HTMLInputElement).value,
        department: (form.department as HTMLInputElement).value,
        equipment_items: items.filter((item) => item.name.trim()),
      }
      await api.post('/internal/', data)
      navigate('/internal')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit requisition.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card">
          <div className="card-header d-flex align-items-center gap-2">
            <i className="bi bi-plus-circle" style={{ color: '#16a34a' }}></i> New Internal
            Requisition
          </div>
          <div className="card-body">
            <form onSubmit={handleSubmit}>
              {error && <div className="alert alert-danger py-2 small">{error}</div>}

              <h6 className="fw-bold mb-3" style={{ color: '#16a34a' }}>
                <i className="bi bi-person me-1"></i> Personal Information
              </h6>
              <div className="row mb-3">
                <div className="col-md-4">
                  <label className="form-label">
                    Email Address <span className="text-danger">*</span>
                  </label>
                  <input
                    type="email"
                    name="email_address"
                    className="form-control"
                    defaultValue={staffDefaults.email_address}
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    Full Name <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="full_name"
                    className="form-control"
                    defaultValue={staffDefaults.full_name}
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    Mobile Number <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="mobile_number"
                    className="form-control"
                    placeholder="e.g. 017XX-XXXXXX"
                    defaultValue={staffDefaults.mobile_number}
                    required
                  />
                </div>
              </div>
              <div className="row mb-4">
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
                <div className="col-md-4">
                  <label className="form-label">
                    PIN <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="pin"
                    className="form-control"
                    placeholder="Staff PIN number"
                    required
                  />
                </div>
                <div className="col-md-4">
                  <label className="form-label">
                    Department <span className="text-danger">*</span>
                  </label>
                  <input
                    type="text"
                    name="department"
                    className="form-control"
                    placeholder="e.g. Finance, HR, Operations"
                    required
                  />
                </div>
              </div>

              <hr />
              <div className="d-flex justify-content-between align-items-center mb-2">
                <h6 className="fw-bold mb-0">Equipment Items</h6>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-success"
                  onClick={addItem}
                >
                  <i className="bi bi-plus-lg me-1"></i> Add Item
                </button>
              </div>

              <div id="itemsContainer">
                {items.map((item, index) => (
                  <div className="row item-row g-2 mb-2" key={index}>
                    <div className="col-4">
                      <input
                        type="text"
                        className="form-control form-control-sm"
                        placeholder="Equipment name"
                        value={item.name}
                        onChange={(e) => updateItem(index, 'name', e.target.value)}
                        required
                      />
                    </div>
                    <div className="col-2">
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        placeholder="Qty"
                        min={1}
                        value={item.quantity}
                        onChange={(e) => updateItem(index, 'quantity', Number(e.target.value))}
                        required
                      />
                    </div>
                    <div className="col-5">
                      <input
                        type="text"
                        className="form-control form-control-sm"
                        placeholder="Purpose / reason"
                        value={item.purpose}
                        onChange={(e) => updateItem(index, 'purpose', e.target.value)}
                      />
                    </div>
                    <div className="col-1 d-flex align-items-center">
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger remove-row"
                        title="Remove"
                        onClick={() => removeItem(index)}
                      >
                        <i className="bi bi-trash"></i>
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <hr />
              <div className="d-flex gap-2">
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                  <i className="bi bi-send me-1"></i>{' '}
                  {isSubmitting ? 'Submitting...' : 'Submit Request'}
                </button>
                <Link to="/internal" className="btn btn-outline-secondary">
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
