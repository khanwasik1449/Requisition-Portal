import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { getAllResults } from '@/lib/paginate'

interface Module {
  id: number
  key: string
  name: string
  is_active: boolean
  order: number
}

export interface FormField {
  id: number
  module: number
  key: string
  label: string
  field_type: string
  field_type_display: string
  help_text: string
  placeholder: string
  step: number
  order: number
  required: boolean
  is_system: boolean
  visible_to_requester: boolean
  show_in_review: boolean
  options: string
}

/**
 * Replica of portal_config/templates/portal_config/field_list.html.
 *
 * Reached from module_list's "Fields (n)" button, which is a link there -- the
 * inline list this app used to toggle open was standing in for a page that had
 * not been built yet.
 */
export function FormFieldList() {
  const [searchParams] = useSearchParams()
  const moduleKey = searchParams.get('module') || ''
  const queryClient = useQueryClient()
  const [pendingDelete, setPendingDelete] = useState<FormField | null>(null)
  const [deleteError, setDeleteError] = useState('')

  const { data: modules } = useQuery({
    queryKey: ['modules'],
    queryFn: async () => getAllResults<Module>('/modules/'),
  })

  const currentModule = modules?.results.find((m) => m.key === moduleKey)

  const { data: fields, isLoading, isError } = useQuery({
    queryKey: ['formFields', moduleKey],
    enabled: !!currentModule,
    queryFn: async () => getAllResults<FormField>('/form-fields/'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/form-fields/${id}/`),
    onSuccess: () => {
      setPendingDelete(null)
      setDeleteError('')
      queryClient.invalidateQueries({ queryKey: ['formFields'] })
    },
    onError: (error: unknown) => {
      const data = (error as { response?: { data?: { detail?: string } } })?.response?.data
      setDeleteError(data?.detail || 'Could not remove that field. Please try again.')
    },
  })

  if (!moduleKey) {
    return <div className="alert alert-warning">Choose a module first.</div>
  }

  if (!currentModule) {
    return modules ? (
      <div className="alert alert-danger">
        Unknown module <code>{moduleKey}</code>.{' '}
        <Link to="/admin/form-builder">Back to Configuration</Link>
      </div>
    ) : null
  }

  if (isLoading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  if (isError) {
    return <div className="alert alert-danger">Could not load this module's fields.</div>
  }

  // portal_config.views.field_list groups by step off the same
  // `module, step, order, id` ordering the model declares.
  const moduleFields = (fields?.results || [])
    .filter((f) => f.module === currentModule.id)
    .sort((a, b) => a.step - b.step || a.order - b.order || a.id - b.id)

  const grouped = new Map<number, FormField[]>()
  moduleFields.forEach((f) => {
    const bucket = grouped.get(f.step)
    if (bucket) bucket.push(f)
    else grouped.set(f.step, [f])
  })
  const stepNumbers = [...grouped.keys()].sort((a, b) => a - b)

  return (
    <div className="row justify-content-center">
      <div className="col-lg-11">
        <div className="d-flex align-items-center justify-content-between mb-3">
          <div>
            <nav aria-label="breadcrumb">
              <ol className="breadcrumb mb-1">
                <li className="breadcrumb-item">
                  <Link to="/admin/form-builder">Configuration</Link>
                </li>
                <li className="breadcrumb-item active">{currentModule.name}</li>
              </ol>
            </nav>
            <h5 className="mb-0">Form fields</h5>
          </div>
          <div className="d-flex gap-2">
            <Link
              to={`/admin/workflow-editor?module=${currentModule.key}`}
              className="btn btn-sm btn-outline-secondary"
            >
              <i className="bi bi-diagram-3 me-1"></i> Workflow
            </Link>
            <Link
              to={`/admin/form-builder/fields/new?module=${currentModule.key}`}
              className="btn btn-sm btn-primary"
            >
              <i className="bi bi-plus-lg me-1"></i> Add field
            </Link>
          </div>
        </div>

        <div className="alert alert-info small">
          Fields marked <strong>stored in a column</strong> write to a real database
          column, so reports and exports can use them. Unchecked fields added here
          are saved in the requisition's extra data field — you can add new
          questions without a code change.
        </div>

        {stepNumbers.length === 0 ? (
          <div className="alert alert-warning">
            This module has no form fields yet. Use <strong>Add field</strong> to build its
            form.
          </div>
        ) : (
          stepNumbers.map((number) => {
            const stepFields = grouped.get(number) || []
            return (
              <div className="card mb-3" key={number}>
                <div className="card-header py-2">
                  <i className="bi bi-signpost-split me-1"></i>
                  <strong>Step {number}</strong>
                  <span className="text-muted small ms-1">
                    ({stepFields.length} field{stepFields.length === 1 ? '' : 's'})
                  </span>
                </div>
                <div className="table-responsive">
                  <table className="table table-sm table-hover mb-0 align-middle">
                    <thead className="table-light">
                      <tr>
                        <th style={{ width: 60 }}>Order</th>
                        <th>Label</th>
                        <th style={{ width: 130 }}>Key</th>
                        <th style={{ width: 130 }}>Type</th>
                        <th style={{ width: 110 }}>Required</th>
                        <th style={{ width: 120 }}>Stored in</th>
                        <th style={{ width: 90 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {stepFields.map((field) => (
                        <tr key={field.id}>
                          <td className="text-muted">{field.order}</td>
                          <td>
                            {field.label}
                            {field.help_text && (
                              <div className="small text-muted">{field.help_text}</div>
                            )}
                          </td>
                          <td>
                            <code className="small">{field.key}</code>
                          </td>
                          <td>
                            <span className="badge text-bg-light border">
                              {field.field_type_display}
                            </span>
                          </td>
                          <td>
                            {field.required ? (
                              <span className="badge text-bg-danger">Required</span>
                            ) : (
                              <span className="text-muted small">Optional</span>
                            )}
                          </td>
                          <td>
                            {field.is_system ? (
                              <span className="badge text-bg-success">Column</span>
                            ) : (
                              <span className="badge text-bg-warning">Extra data</span>
                            )}
                          </td>
                          <td className="text-end">
                            <Link
                              to={`/admin/form-builder/fields/${field.id}/edit`}
                              className="btn btn-sm btn-outline-secondary"
                              title="Edit"
                            >
                              <i className="bi bi-pencil"></i>
                            </Link>{' '}
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              title="Remove"
                              onClick={() => {
                                setDeleteError('')
                                setPendingDelete(field)
                              }}
                            >
                              <i className="bi bi-trash"></i>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })
        )}
      </div>

      {pendingDelete && (
        <div className="modal fade show d-block" tabIndex={-1} role="dialog" aria-modal="true">
          <div
            className="modal-dialog modal-dialog-centered"
            onClick={(e) => {
              if (e.target === e.currentTarget) setPendingDelete(null)
            }}
          >
            <div className="modal-content">
              <div className="modal-header bg-danger text-white">
                <h5 className="modal-title d-flex align-items-center gap-2">
                  <i className="bi bi-exclamation-triangle-fill"></i> Confirm removal
                </h5>
                <button
                  type="button"
                  className="btn-close btn-close-white"
                  aria-label="Close"
                  onClick={() => setPendingDelete(null)}
                ></button>
              </div>
              <div className="modal-body">
                <p className="fw-semibold mb-1">
                  Remove this field from the {currentModule.name} form?
                </p>
                <p className="text-muted small mb-0">
                  <strong>{pendingDelete.label}</strong> will stop appearing on the form.
                  Values already submitted are kept in the database, but new
                  submissions will no longer collect it.
                </p>
                {deleteError && (
                  <div className="alert alert-danger py-2 mt-3 mb-0">
                    <i className="bi bi-exclamation-triangle me-1"></i>
                    {deleteError}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => setPendingDelete(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => deleteMutation.mutate(pendingDelete.id)}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? (
                    <>
                      <span
                        className="spinner-border spinner-border-sm me-1"
                        role="status"
                      ></span>
                      Removing...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-trash me-1"></i> Remove field
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {pendingDelete && <div className="modal-backdrop fade show"></div>}
    </div>
  )
}
