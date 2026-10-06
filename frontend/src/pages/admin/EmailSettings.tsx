import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { getAllResults } from '@/lib/paginate'

interface EmailConfig {
  id: number
  department: string
  department_display: string
  email_host: string
  email_port: number
  email_host_user: string
  email_host_password: string
  email_use_tls: boolean
  from_email: string
  notification_email: string
  is_active: boolean
}

const blank = {
  department: '',
  email_host: 'smtp.gmail.com',
  email_port: 587,
  email_host_user: '',
  email_host_password: '',
  email_use_tls: true,
  from_email: '',
  notification_email: '',
  is_active: true,
}

// Replica of templates/notifications/config_list.html
export function EmailSettings() {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<EmailConfig | 'new' | null>(null)
  const [form, setForm] = useState({ ...blank })
  const [error, setError] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['emailConfigs'],
    queryFn: async () => {
      return getAllResults<EmailConfig>('/email-configs/')
    },
  })

  const saveMutation = useMutation({
    mutationFn: (id: number | null) =>
      id
        ? api.put(`/email-configs/${id}/`, form)
        : api.post('/email-configs/', form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emailConfigs'] })
      setEditing(null)
      setError(null)
    },
    onError: (e: any) => {
      setError(
        e?.response?.data
          ? JSON.stringify(e.response.data).slice(0, 300)
          : 'Could not save this configuration.'
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/email-configs/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['emailConfigs'] }),
  })

  const results = data?.results || []

  const openEdit = (c: EmailConfig) => {
    setForm({
      department: c.department,
      email_host: c.email_host,
      email_port: c.email_port,
      email_host_user: c.email_host_user,
      email_host_password: c.email_host_password,
      email_use_tls: c.email_use_tls,
      from_email: c.from_email,
      notification_email: c.notification_email,
      is_active: c.is_active,
    })
    setEditing(c)
    setError(null)
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Email Configurations</h2>
          <p className="text-muted mb-0 small">Manage SMTP settings per department</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => {
            setForm({ ...blank })
            setEditing('new')
            setError(null)
          }}
        >
          <i className="bi bi-plus-lg me-1"></i> Add
        </button>
      </div>

      {editing && (
        <div className="card mb-4">
          <div className="card-header bg-white">
            <i className="bi bi-envelope me-2" style={{ color: '#2563eb' }}></i>
            {editing === 'new' ? 'Add email configuration' : 'Edit email configuration'}
          </div>
          <div className="card-body">
            {error && <div className="alert alert-danger py-2">{error}</div>}
            <form
              className="row g-3"
              onSubmit={(e) => {
                e.preventDefault()
                saveMutation.mutate(editing === 'new' ? null : editing.id)
              }}
            >
              <div className="col-md-3">
                <label className="form-label small">Department</label>
                <select
                  className="form-select form-select-sm"
                  required
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                >
                  <option value="">Choose…</option>
                  <option value="ict">ICT</option>
                  <option value="transport">Transport</option>
                  <option value="internal">Internal</option>
                </select>
              </div>
              <div className="col-md-3">
                <label className="form-label small">From email</label>
                <input
                  type="email"
                  className="form-control form-control-sm"
                  required
                  value={form.from_email}
                  onChange={(e) => setForm({ ...form, from_email: e.target.value })}
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">Notification email</label>
                <input
                  type="email"
                  className="form-control form-control-sm"
                  required
                  value={form.notification_email}
                  onChange={(e) => setForm({ ...form, notification_email: e.target.value })}
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">SMTP host</label>
                <input
                  className="form-control form-control-sm"
                  value={form.email_host}
                  onChange={(e) => setForm({ ...form, email_host: e.target.value })}
                />
              </div>
              <div className="col-md-2">
                <label className="form-label small">Port</label>
                <input
                  type="number"
                  className="form-control form-control-sm"
                  value={form.email_port}
                  onChange={(e) =>
                    setForm({ ...form, email_port: parseInt(e.target.value, 10) || 0 })
                  }
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">SMTP user</label>
                <input
                  className="form-control form-control-sm"
                  value={form.email_host_user}
                  onChange={(e) => setForm({ ...form, email_host_user: e.target.value })}
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">SMTP password</label>
                <input
                  type="password"
                  className="form-control form-control-sm"
                  value={form.email_host_password}
                  onChange={(e) => setForm({ ...form, email_host_password: e.target.value })}
                />
              </div>
              <div className="col-md-4 d-flex align-items-end gap-4">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="useTls"
                    checked={form.email_use_tls}
                    onChange={(e) => setForm({ ...form, email_use_tls: e.target.checked })}
                  />
                  <label className="form-check-label small" htmlFor="useTls">
                    Use TLS
                  </label>
                </div>
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="isActive"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                  <label className="form-check-label small" htmlFor="isActive">
                    Active
                  </label>
                </div>
              </div>
              <div className="col-12 d-flex gap-2">
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={saveMutation.isPending}
                >
                  <i className="bi bi-check-lg me-1"></i> Save
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => setEditing(null)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Department</th>
                  <th>From Email</th>
                  <th>Notification Email</th>
                  <th>SMTP Host</th>
                  <th>Active</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : isError ? (
                  <tr>
                    <td colSpan={6} className="text-center text-danger py-4">
                      Could not load email configurations.
                    </td>
                  </tr>
                ) : results.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-5 text-muted">
                      No email configurations found.
                    </td>
                  </tr>
                ) : (
                  results.map((c) => (
                    <tr key={c.id}>
                      <td className="fw-semibold">{c.department_display}</td>
                      <td>{c.from_email}</td>
                      <td>{c.notification_email}</td>
                      <td className="text-muted small">
                        {c.email_host}:{c.email_port}
                      </td>
                      <td>
                        {c.is_active ? (
                          <span className="badge bg-success">Active</span>
                        ) : (
                          <span className="badge bg-secondary">Inactive</span>
                        )}
                      </td>
                      <td className="text-end">
                        <div className="d-flex gap-1 justify-content-end">
                          <button
                            className="btn btn-sm btn-outline-primary"
                            title="Edit"
                            onClick={() => openEdit(c)}
                          >
                            <i className="bi bi-pencil"></i>
                          </button>
                          <button
                            className="btn btn-sm btn-outline-danger"
                            title="Remove"
                            onClick={() => {
                              if (
                                window.confirm(
                                  `Delete ${c.department_display} email configuration?`
                                )
                              ) {
                                deleteMutation.mutate(c.id)
                              }
                            }}
                          >
                            <i className="bi bi-trash"></i>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
