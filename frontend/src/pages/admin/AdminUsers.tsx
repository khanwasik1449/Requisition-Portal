import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'

interface AdminUser {
  id: number
  username: string
  email?: string
  phone?: string
  role: string
  role_display?: string
  is_active: boolean
  is_superuser?: boolean
  date_joined: string
}

// Exact replica of templates/accounts/user_list.html
export function AdminUsers() {
  const queryClient = useQueryClient()

  const { data: users, isLoading } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: async () => {
      const response = await api.get<{ results: AdminUser[] }>('/admin/users/')
      return response.data
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: number) => api.post(`/admin/users/${id}/approve/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adminUsers'] }),
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => api.post(`/admin/users/${id}/deactivate/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adminUsers'] }),
  })

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">User Management</h2>
          <p className="text-muted mb-0 small">
            Manage users, approve accounts, and assign roles
          </p>
        </div>
        <button className="btn btn-primary">
          <i className="bi bi-plus-lg me-1"></i> Add User
        </button>
      </div>

      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : users?.results.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-5">
                      <i
                        className="bi bi-people"
                        style={{ fontSize: '2.5rem', color: '#cbd5e1' }}
                      ></i>
                      <p className="text-muted mt-2 mb-0">No users found.</p>
                    </td>
                  </tr>
                ) : (
                  users?.results.map((u) => (
                    <tr key={u.id}>
                      <td className="fw-semibold">{u.id}</td>
                      <td>
                        {u.username}{' '}
                        {u.is_superuser && <span className="badge bg-dark ms-1">Super</span>}
                      </td>
                      <td>{u.email || <span className="text-muted">—</span>}</td>
                      <td>{u.phone || <span className="text-muted">—</span>}</td>
                      <td>
                        <span className="badge bg-light text-dark border">
                          {u.role_display || u.role}
                        </span>
                      </td>
                      <td>
                        {u.is_active ? (
                          <span className="badge bg-success">
                            <i className="bi bi-check-circle me-1"></i>Active
                          </span>
                        ) : (
                          <span className="badge bg-warning">
                            <i className="bi bi-clock me-1"></i>Pending
                          </span>
                        )}
                      </td>
                      <td className="text-muted small">{u.date_joined}</td>
                      <td className="text-end">
                        <div className="d-flex gap-1 justify-content-end">
                          <button className="btn btn-sm btn-outline-secondary" title="Edit">
                            <i className="bi bi-pencil"></i>
                          </button>
                          {!u.is_active ? (
                            <button
                              className="btn btn-sm btn-success"
                              title="Approve"
                              onClick={() => approveMutation.mutate(u.id)}
                              disabled={approveMutation.isPending}
                            >
                              <i className="bi bi-check-lg"></i>
                            </button>
                          ) : (
                            <button
                              className="btn btn-sm btn-outline-danger"
                              title="Deactivate"
                              onClick={() => {
                                if (window.confirm(`Deactivate user ${u.username}?`)) {
                                  deactivateMutation.mutate(u.id)
                                }
                              }}
                              disabled={deactivateMutation.isPending}
                            >
                              <i className="bi bi-pause"></i>
                            </button>
                          )}
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
