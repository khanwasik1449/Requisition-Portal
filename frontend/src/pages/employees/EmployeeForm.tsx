import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash } from '@/lib/flash'

interface Employee {
  id: number
  pin: string
  name: string
  designation: string
  gender: string | null
  tin: string | null
  phone: string | null
  email: string | null
  salary: number | string | null
}

interface FormState {
  pin: string
  name: string
  designation: string
  gender: string
  tin: string
  phone: string
  email: string
  salary: string
}

const emptyForm: FormState = {
  pin: '',
  name: '',
  designation: '',
  gender: '',
  tin: '',
  phone: '',
  email: '',
  salary: '',
}

function str(v: string | number | null | undefined) {
  return v === null || v === undefined ? '' : String(v)
}

// employees/templates/employees/add.html -- <style> block, verbatim.
const addCss = `
  :root { --c-bg: #F7F6F3; --c-surface: #FFFFFF; --c-border: rgba(0,0,0,0.08); --c-accent: #2563EB; --c-muted: #6B6A66; --c-success: #16A34A; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', Arial, sans-serif; background: var(--c-bg); }
  .wrapper { max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
  .card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  h1 { margin-bottom: 1.5rem; }
  .field { margin-bottom: 1rem; }
  .field label { display: block; margin-bottom: 5px; font-weight: 500; color: var(--c-muted); font-size: 13px; }
  .field input, .field select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
  .field input:focus, .field select:focus { outline: none; border-color: var(--c-accent); }
  .btn { background: var(--c-success); color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; }
  .btn:hover { background: #15803D; }
  .btn-secondary { background: #6B7280; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; }
  .btn-secondary:hover { background: #4B5563; }
  .row { display: flex; gap: 1rem; }
  .row .field { flex: 1; }
`

// employees/templates/employees/edit.html -- <style> block, verbatim.
const editCss = `
  :root { --c-bg: #F7F6F3; --c-surface: #FFFFFF; --c-border: rgba(0,0,0,0.08); --c-accent: #2563EB; --c-muted: #6B6A66; --c-success: #16A34A; --c-danger: #DC2626; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', Arial, sans-serif; background: var(--c-bg); }
  .wrapper { max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
  .card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  h1 { margin-bottom: 1.5rem; }
  .field { margin-bottom: 1rem; }
  .field label { display: block; margin-bottom: 5px; font-weight: 500; color: var(--c-muted); font-size: 13px; }
  .field input, .field select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
  .field input:focus, .field select:focus { outline: none; border-color: var(--c-accent); }
  .btn { padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; text-decoration: none; }
  .btn-success { background: var(--c-success); color: white; border: none; }
  .btn-danger { background: var(--c-danger); color: white; border: none; }
  .btn-secondary { background: #6B7280; color: white; }
  .row { display: flex; gap: 1rem; }
  .row .field { flex: 1; }
`

// add.html when there is no `:pin` in the route, edit.html when there is.
export function EmployeeForm() {
  const { pin } = useParams<{ pin: string }>()
  const isEdit = Boolean(pin)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [form, setForm] = useState<FormState>(emptyForm)
  const [error, setError] = useState<string | null>(null)
  // HrLayout only drains the shared flash slot when the location changes, so a
  // failure raised here is also rendered inline (like base.html does on the
  // re-rendered template) and the pending slot is dropped on unmount instead
  // of popping up on whatever page the user visits next.
  const ownsFlash = useRef(false)

  const existing = useQuery({
    queryKey: ['employees', pin],
    queryFn: async () =>
      (await api.get<Employee>(`/employees/${encodeURIComponent(pin!)}/`)).data,
    enabled: isEdit,
  })

  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  useEffect(() => {
    const employee = existing.data
    if (!employee) return
    setForm({
      pin: employee.pin,
      name: employee.name,
      designation: employee.designation,
      gender: str(employee.gender),
      tin: str(employee.tin),
      phone: str(employee.phone),
      email: str(employee.email),
      salary: str(employee.salary),
    })
  }, [existing.data])

  const set = (key: keyof FormState, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const save = useMutation({
    mutationFn: async () => {
      // employees/views.py strips designation/email and coerces the blanks to
      // NULL before writing the row.
      const payload = {
        pin: form.pin,
        name: form.name,
        designation: form.designation.trim(),
        gender: form.gender || null,
        tin: form.tin || null,
        phone: form.phone || null,
        email: form.email.trim(),
        salary: Number(form.salary) || 0,
      }
      if (isEdit) {
        // Employee is addressed by PIN -- the original pin identifies the row,
        // the form may still post a new one (edit_employee(request, pk)).
        return api.put(`/employees/${encodeURIComponent(pin!)}/`, payload)
      }
      return api.post('/employees/', payload)
    },
    onSuccess: () => {
      ownsFlash.current = false
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      setFlash(
        'success',
        isEdit
          ? 'Employee updated successfully!'
          : 'Employee added successfully!',
      )
      navigate('/hr/employees')
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setError(text)
    },
  })

  // A bad :pin in the route (the edit template's 404) lands in the same banner
  // the POST failures use, so the one close button clears both.
  useEffect(() => {
    if (existing.isError) setError(flashFromError(existing.error).text)
  }, [existing.isError, existing.error])

  return (
    <>
      <PageStyle css={isEdit ? editCss : addCss} />

      {error && (
        <div className="app-message error">
          <span className="msg-close" onClick={() => setError(null)}>
            &times;
          </span>
          {error}
        </div>
      )}

      <div className="wrapper">
        <h1>{isEdit ? 'Edit Employee' : 'Add Employee'}</h1>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            setError(null)
            save.mutate()
          }}
        >
          <div className="card">
            <div className="field">
              <label>
                PIN <span style={{ color: 'red' }}>*</span>
              </label>
              <input
                type="text"
                name="pin"
                required
                placeholder={isEdit ? undefined : 'Employee PIN'}
                value={form.pin}
                onChange={(e) => set('pin', e.target.value)}
              />
            </div>

            <div className="field">
              <label>
                Name <span style={{ color: 'red' }}>*</span>
              </label>
              <input
                type="text"
                name="name"
                required
                placeholder={isEdit ? undefined : 'Full Name'}
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
              />
            </div>

            <div className="row">
              <div className="field">
                <label>
                  Designation <span style={{ color: 'red' }}>*</span>
                </label>
                <input
                  type="text"
                  name="designation"
                  required
                  placeholder={isEdit ? undefined : 'Job Title'}
                  value={form.designation}
                  onChange={(e) => set('designation', e.target.value)}
                />
              </div>

              <div className="field">
                <label>Gender</label>
                <select
                  name="gender"
                  value={form.gender}
                  onChange={(e) => set('gender', e.target.value)}
                >
                  <option value="">Select</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
              </div>
            </div>

            <div className="field">
              <label>TIN Number</label>
              <input
                type="text"
                name="tin"
                placeholder={isEdit ? undefined : 'TIN Number'}
                value={form.tin}
                onChange={(e) => set('tin', e.target.value)}
              />
            </div>

            <div className="row">
              <div className="field">
                <label>Phone Number</label>
                <input
                  type="text"
                  name="phone"
                  placeholder={isEdit ? undefined : 'Phone Number'}
                  value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                />
              </div>

              <div className="field">
                <label>
                  Email Address <span style={{ color: 'red' }}>*</span>
                </label>
                <input
                  type="email"
                  name="email"
                  required
                  placeholder={isEdit ? undefined : 'Email Address'}
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                />
              </div>
            </div>

            <div className="field">
              <label>Salary</label>
              <input
                type="number"
                name="salary"
                placeholder={isEdit ? undefined : 'Basic Salary'}
                step="0.01"
                value={form.salary}
                onChange={(e) => set('salary', e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem' }}>
              <button
                type="submit"
                className={isEdit ? 'btn btn-success' : 'btn'}
                disabled={save.isPending}
              >
                {isEdit ? 'Save Changes' : 'Add Employee'}
              </button>
              <Link
                to="/hr/employees"
                className={isEdit ? 'btn btn-secondary' : 'btn-secondary'}
              >
                Cancel
              </Link>
            </div>
          </div>
        </form>
      </div>
    </>
  )
}
