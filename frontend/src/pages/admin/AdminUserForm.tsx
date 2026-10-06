import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'

interface AdminUser {
  id: number
  username: string
  email: string
  phone: string
  role: string
  role_display?: string
  is_active: boolean
}

/**
 * The seven roles accounts/user_form.html lists, in its order. `User.Role`
 * actually defines ten -- grants, grants_admin and hr_admin are left out of the
 * template -- so those three are appended below when a record carries one,
 * purely so an edit cannot silently rewrite the role to the first option.
 */
const FORM_ROLES: Array<[string, string]> = [
  ['requester', 'Requester'],
  ['supervisor', 'Supervisor (1st Approver)'],
  ['ict_approver', 'ICT Approver (2nd Approver)'],
  ['ict_admin', 'ICT Admin'],
  ['transport_admin', 'Transport Admin'],
  ['internal_admin', 'Internal Admin'],
  ['admin', 'Admin'],
]

type ErrorMap = Record<string, string[]>

/**
 * Replica of templates/accounts/user_form.html.
 *
 * Route shapes: /admin/users/create  and  /admin/users/<id>/edit
 */
export function AdminUserForm() {
  const { userId } = useParams<{ userId: string }>()
  const isEdit = !!userId
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [role, setRole] = useState('requester')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [errors, setErrors] = useState<ErrorMap>({})
  const [nonField, setNonField] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [dirty, setDirty] = useState(false)

  const { data: user, isLoading } = useQuery({
    queryKey: ['adminUser', userId],
    enabled: isEdit,
    queryFn: async () => (await api.get<AdminUser>(`/users/${userId}/`)).data,
  })

  useEffect(() => {
    if (dirty || !user) return
    setUsername(user.username)
    setEmail(user.email || '')
    setPhone(user.phone || '')
    setRole(user.role)
    setIsActive(user.is_active)
  }, [user, dirty])

  const roleOptions = [...FORM_ROLES]
  if (isEdit && user && !FORM_ROLES.some(([value]) => value === user.role)) {
    roleOptions.push([user.role, user.role_display || user.role])
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setNonField([])
    try {
      if (isEdit) {
        // user_form.html submits the blank box rather than omitting it, and
        // `password: ''` is what means "keep the current one".
        await api.patch(`/users/${userId}/`, { email, phone, role, is_active: isActive, password })
      } else {
        await api.post('/users/', { username, password, email, phone, role, is_active: isActive })
      }
      // Elsewhere the list would keep showing the rows it cached before this
      // save, so the change only appeared on a manual reload.
      await queryClient.invalidateQueries({ queryKey: ['adminUsers'] })
      await queryClient.invalidateQueries({ queryKey: ['adminUser', userId] })
      navigate('/admin/users')
    } catch (error) {
      const data = (error as { response?: { data?: unknown } })?.response?.data
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        const body = data as Record<string, unknown>
        const rest: ErrorMap = {}
        let nonFieldErrors: string[] = []
        Object.entries(body).forEach(([field, value]) => {
          const list = Array.isArray(value) ? value.map(String) : [String(value)]
          if (field === 'non_field_errors') nonFieldErrors = list
          else rest[field] = list
        })
        setErrors(rest)
        setNonField(nonFieldErrors)
      } else {
        setNonField(['Something went wrong. Please try again.'])
      }
    } finally {
      setBusy(false)
    }
  }

  const fieldError = (name: string) =>
    errors[name]?.map((message, i) => (
      <div className="text-danger small" key={i}>
        {message}
      </div>
    ))

  if (isEdit && isLoading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-6">
        <div className="card">
          <div className="card-header d-flex align-items-center gap-2">
            <i
              className={`bi bi-${isEdit ? 'pencil' : 'person-plus'}`}
              style={{ color: '#2563eb' }}
            ></i>
            {isEdit ? 'Edit User' : 'Add New User'}
          </div>
          <div className="card-body">
            {nonField.length > 0 &&
              nonField.map((message, i) => (
                <div className="alert alert-danger py-2 small" key={i}>
                  {message}
                </div>
              ))}

            <form onSubmit={submit}>
              <div className="mb-3">
                <label className="form-label" htmlFor="uf-username">
                  Username <span className="text-danger">*</span>
                </label>
                <input
                  id="uf-username"
                  type="text"
                  className="form-control"
                  required
                  readOnly={isEdit}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                {fieldError('username')}
              </div>

              <div className="row mb-3">
                <div className="col-md-6">
                  <label className="form-label" htmlFor="uf-email">
                    Email
                  </label>
                  <input
                    id="uf-email"
                    type="email"
                    className="form-control"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  {fieldError('email')}
                </div>
                <div className="col-md-6">
                  <label className="form-label" htmlFor="uf-phone">
                    Phone
                  </label>
                  <input
                    id="uf-phone"
                    type="text"
                    className="form-control"
                    maxLength={15}
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                  {fieldError('phone')}
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label" htmlFor="uf-role">
                  Role <span className="text-danger">*</span>
                </label>
                <select
                  id="uf-role"
                  className="form-select"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                >
                  {roleOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                {fieldError('role')}
              </div>

              <div className="mb-3">
                <label className="form-label" htmlFor="uf-password">
                  Password {!isEdit && <span className="text-danger">*</span>}
                </label>
                <input
                  id="uf-password"
                  type="password"
                  className="form-control"
                  required={!isEdit}
                  placeholder={isEdit ? 'Leave blank to keep current' : 'Set password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {fieldError('password')}
              </div>

              <div className="mb-3 form-check">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="is_active"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="is_active">
                  Active (can log in)
                </label>
                {fieldError('is_active')}
              </div>

              <hr />
              <div className="d-flex gap-2">
                <button type="submit" className="btn btn-primary" disabled={busy}>
                  {busy ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status"></span>
                      Saving...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-check-lg me-1"></i>{' '}
                      {isEdit ? 'Save Changes' : 'Create User'}
                    </>
                  )}
                </button>
                <Link to="/admin/users" className="btn btn-outline-secondary">
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
