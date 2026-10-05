import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { useAuth } from '@/auth/hooks'

interface Module {
  id: number
  key: string
  name: string
  description: string
  is_active: boolean
  order: number
  is_enabled: boolean
  is_visible: boolean
}

interface FormField {
  id: number
  module: number
  key: string
  label: string
  field_type: string
  field_type_display: string
  step: number
  required: boolean
}

interface WorkflowStage {
  id: number
  module: number
  key: string
  name: string
  order: number
  approver_role: string
  approver_role_display: string | null
  actions: string
  is_terminal: boolean
  is_active: boolean
}

// Replica of portal_config/templates/portal_config/module_list.html
export function FormBuilder() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const isSuper = user?.role === 'admin'
  const [expanded, setExpanded] = useState<number | null>(null)
  // Unsaved switch positions, keyed by module id.
  const [drafts, setDrafts] = useState<Record<number, { enabled: boolean; visible: boolean }>>({})

  const { data: modules, isLoading, isError } = useQuery({
    queryKey: ['modules'],
    queryFn: async () => {
      const response = await api.get<{ results: Module[] }>('/modules/')
      return response.data
    },
  })

  const { data: fields } = useQuery({
    queryKey: ['formFields'],
    queryFn: async () => {
      const response = await api.get<{ results: FormField[] }>('/form-fields/')
      return response.data
    },
  })

  const { data: stages } = useQuery({
    queryKey: ['workflowStages'],
    queryFn: async () => {
      const response = await api.get<{ results: WorkflowStage[] }>('/workflow-stages/')
      return response.data
    },
  })

  const saveMutation = useMutation({
    mutationFn: ({ id, is_enabled, is_visible }: { id: number; is_enabled: boolean; is_visible: boolean }) =>
      api.patch(`/modules/${id}/`, { is_enabled, is_visible }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['modules'] }),
  })

  const activeModules = (modules?.results || [])
    .filter((m) => m.is_active)
    .sort((a, b) => a.order - b.order || a.name.localeCompare(b.name))

  const fieldsByModule = (fields?.results || []).reduce<Record<number, FormField[]>>(
    (acc, f) => {
      ;(acc[f.module] = acc[f.module] || []).push(f)
      return acc
    },
    {}
  )

  const stagesByModule = (stages?.results || []).reduce<Record<number, WorkflowStage[]>>(
    (acc, s) => {
      ;(acc[s.module] = acc[s.module] || []).push(s)
      return acc
    },
    {}
  )

  Object.values(stagesByModule).forEach((list) => list.sort((a, b) => a.order - b.order))

  const draftFor = (m: Module) => drafts[m.id] ?? { enabled: m.is_enabled, visible: m.is_visible }

  // portal_config.views.module_toggle: a module that is off is always hidden,
  // and the "Show in menu" switch is disabled (never submitted) in that state.
  const submitToggle = (m: Module) => {
    const { enabled, visible } = draftFor(m)
    let nextVisible = visible
    if (enabled && !visible) nextVisible = true
    if (!enabled) nextVisible = false
    saveMutation.mutate({ id: m.id, is_enabled: enabled, is_visible: nextVisible })
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
    return <div className="alert alert-danger">Could not load portal configuration.</div>
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-10">
        <div className="card mb-3">
          <div className="card-header d-flex align-items-center gap-2">
            <i className="bi bi-sliders" style={{ color: '#d97706' }}></i>
            Form Builder &amp; Workflows
          </div>
          <div className="card-body">
            <p className="text-muted mb-0">
              Change the fields on a requisition form and the approval chain it follows.
              Changes apply immediately — new submissions use the new configuration, and
              requisitions already in flight stay at the stage they reached.
            </p>
          </div>
        </div>

        {activeModules.length === 0 ? (
          <div className="alert alert-warning">No modules are configured yet.</div>
        ) : (
          activeModules.map((m) => {
            const moduleFields = fieldsByModule[m.id] || []
            const moduleStages = stagesByModule[m.id] || []
            const draft = draftFor(m)
            const dirty =
              draft.enabled !== m.is_enabled || draft.visible !== m.is_visible

            return (
              <div className="card mb-3" key={m.id}>
                <div className="card-header d-flex align-items-center justify-content-between flex-wrap gap-2">
                  <div>
                    <i className="bi bi-box-seam me-1"></i>
                    <strong>{m.name}</strong>
                    <code className="ms-2 small text-muted">{m.key}</code>
                    {!m.is_enabled ? (
                      <span className="badge text-bg-secondary ms-2">Off — not routed</span>
                    ) : !m.is_visible ? (
                      <span className="badge text-bg-light border ms-2">Hidden from menu</span>
                    ) : null}
                  </div>
                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => setExpanded(expanded === m.id ? null : m.id)}
                    >
                      <i className="bi bi-list-ul me-1"></i> Fields ({moduleFields.length})
                    </button>
                    <Link
                      to={`/admin/workflow-editor?module=${m.key}`}
                      className="btn btn-sm btn-outline-secondary"
                    >
                      <i className="bi bi-diagram-3 me-1"></i> Workflow ({moduleStages.length})
                    </Link>
                  </div>
                </div>

                <div className="card-body py-2">
                  {moduleStages.length > 0 ? (
                    <div className="d-flex align-items-center flex-wrap gap-1 small">
                      {moduleStages.map((s, i) => (
                        <span key={s.id} className="d-inline-flex align-items-center gap-1">
                          {i > 0 && <i className="bi bi-chevron-right text-muted"></i>}
                          <span
                            className={`badge ${
                              s.is_terminal
                                ? 'text-bg-success'
                                : i === 0
                                  ? 'text-bg-warning'
                                  : 'text-bg-light border'
                            }`}
                          >
                            {s.name}
                            {s.approver_role && (
                              <span className="fw-light"> ({s.approver_role_display})</span>
                            )}
                          </span>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted small">No workflow configured yet.</span>
                  )}

                  {expanded === m.id && (
                    <div className="border rounded p-2 mt-3" style={{ maxHeight: 200, overflow: 'auto' }}>
                      {moduleFields.length === 0 ? (
                        <span className="text-muted small">This module has no form fields yet.</span>
                      ) : (
                        moduleFields.map((f) => (
                          <div key={f.id} className="d-flex align-items-center gap-2 small py-1">
                            <code className="text-muted">{f.key}</code>
                            <span>{f.label}</span>
                            <span className="badge bg-light text-dark border ms-auto">
                              {f.field_type_display}
                            </span>
                            {f.required && <span className="badge bg-warning text-dark">required</span>}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {isSuper && (
                    <div className="mt-3 pt-3 border-top">
                      <div className="d-flex flex-wrap gap-4">
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id={`en-${m.key}`}
                            checked={draft.enabled}
                            onChange={(e) =>
                              setDrafts({
                                ...drafts,
                                [m.id]: { ...draft, enabled: e.target.checked },
                              })
                            }
                          />
                          <label className="form-check-label small" htmlFor={`en-${m.key}`}>
                            <strong>On</strong>
                            <span className="d-block text-muted" style={{ fontSize: '.72rem' }}>
                              Routed. Off means the URLs 404 and the data is unreachable.
                            </span>
                          </label>
                        </div>
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id={`vis-${m.key}`}
                            checked={draft.visible}
                            disabled={!draft.enabled}
                            onChange={(e) =>
                              setDrafts({
                                ...drafts,
                                [m.id]: { ...draft, visible: e.target.checked },
                              })
                            }
                          />
                          <label className="form-check-label small" htmlFor={`vis-${m.key}`}>
                            <strong>Show in menu</strong>
                            <span className="d-block text-muted" style={{ fontSize: '.72rem' }}>
                              Off hides it from the nav and dashboard but keeps it routed.
                            </span>
                          </label>
                        </div>
                      </div>
                      <button
                        className="btn btn-sm btn-primary mt-2"
                        disabled={saveMutation.isPending}
                        onClick={() => submitToggle(m)}
                      >
                        <i className="bi bi-check-lg me-1"></i>
                        {dirty ? 'Apply' : 'Saved'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
