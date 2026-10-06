import { useMemo, useState } from 'react'
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

interface FormField {
  id: number
  module: number
  key: string
  label: string
}

interface Stage {
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
  amendable_fields: number[]
}

interface Choice {
  value: string
  label: string
}

interface StageDraft {
  /** null = not yet saved, so it is created on the next Save. */
  id: number | null
  key: string
  name: string
  approver_role: string
  actions: string
  is_terminal: boolean
  is_active: boolean
  amendable_fields: number[]
  removed: boolean
}

function toDraft(s: Stage): StageDraft {
  return {
    id: s.id,
    key: s.key,
    name: s.name,
    approver_role: s.approver_role,
    actions: s.actions,
    is_terminal: s.is_terminal,
    is_active: s.is_active,
    amendable_fields: [...(s.amendable_fields || [])],
    removed: false,
  }
}

function slugify(name: string) {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || 'stage'
  )
}

// Replica of portal_config/templates/portal_config/workflow.html
export function WorkflowEditor() {
  const [params] = useSearchParams()
  const queryClient = useQueryClient()
  const [drafts, setDrafts] = useState<StageDraft[] | null>(null)
  const [message, setMessage] = useState<{ kind: 'success' | 'danger'; text: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const { data: modules } = useQuery({
    queryKey: ['modules'],
    queryFn: async () => getAllResults<Module>('/modules/'),
  })

  const activeModules = useMemo(
    () => (modules?.results || []).filter((m) => m.is_active),
    [modules]
  )
  const moduleKey = params.get('module') || activeModules[0]?.key || ''
  const currentModule = activeModules.find((m) => m.key === moduleKey)

  const { data: stages, isLoading } = useQuery({
    queryKey: ['workflowStages', moduleKey],
    enabled: !!moduleKey,
    queryFn: async () => getAllResults<Stage>('/workflow-stages/'),
  })

  const { data: fields } = useQuery({
    queryKey: ['formFields', moduleKey],
    enabled: !!currentModule,
    queryFn: async () => getAllResults<FormField>('/form-fields/'),
  })

  const { data: choices } = useQuery({
    queryKey: ['portalChoices'],
    queryFn: async () => (await api.get<{ roles: Choice[]; stage_actions: Choice[] }>('/portal-choices/')).data,
  })

  const serverStages = useMemo(
    () => (stages?.results || []).filter((s) => s.module === currentModule?.id),
    [stages, currentModule]
  )

  // Seed the editor from the server once, then work entirely from local state
  // so a partially edited chain is never half-saved by a refetch.
  if (drafts === null && serverStages.length > 0) {
    setDrafts(serverStages.map(toDraft))
  }

  const moduleFields = (fields?.results || []).filter((f) => f.module === currentModule?.id)
  const roleChoices = choices?.roles || []
  const actionChoices = choices?.stage_actions || []
  const validActions = new Set(actionChoices.map((a) => a.value))
  const visible = (drafts ?? serverStages.map(toDraft)).filter((d) => !d.removed)

  const patch = (index: number, next: Partial<StageDraft>) => {
    setDrafts((prev) => {
      const list = [...(prev ?? serverStages.map(toDraft))]
      list[index] = { ...list[index], ...next }
      return list
    })
  }

  const addStage = () => {
    setDrafts((prev) => {
      const list = [...(prev ?? serverStages.map(toDraft))]
      list.push({
        id: null,
        key: '',
        name: '',
        approver_role: '',
        actions: 'approve,decline',
        is_terminal: false,
        is_active: true,
        amendable_fields: [],
        removed: false,
      })
      return list
    })
    setMessage(null)
  }

  const save = async () => {
    if (!currentModule) return
    const list = drafts ?? serverStages.map(toDraft)
    const kept = list.filter((d) => !d.removed)

    if (kept.length === 0) {
      setMessage({ kind: 'danger', text: 'A workflow needs at least one stage.' })
      return
    }

    for (const d of kept) {
      const actions = d.actions
        .split(',')
        .map((a) => a.trim())
        .filter(Boolean)
      const bad = actions.filter((a) => !validActions.has(a))
      if (bad.length > 0) {
        setMessage({
          kind: 'danger',
          text: `"${d.name || d.key}": unknown action(s) ${bad.join(', ')}. Valid actions are: ${actionChoices
            .map((a) => a.value)
            .sort()
            .join(', ')}.`,
        })
        return
      }
    }

    setSaving(true)
    setMessage(null)
    try {
      // 1. Remove first, so a renamed key never collides with a stage leaving.
      for (const d of list.filter((x) => x.removed && x.id !== null)) {
        await api.delete(`/workflow-stages/${d.id}/`)
      }

      // 2. Update survivors and add new ones, carrying the row order with them.
      let order = 1
      for (const d of kept) {
        const payload = {
          module: currentModule.id,
          key: d.id === null ? slugify(d.name) : d.key,
          name: d.name.trim() || d.key,
          order: order++,
          approver_role: d.approver_role,
          actions: d.actions,
          is_terminal: d.is_terminal,
          is_active: d.is_active,
          amendable_fields: d.amendable_fields,
        }
        if (d.id === null) {
          await api.post('/workflow-stages/', payload)
        } else {
          await api.patch(`/workflow-stages/${d.id}/`, payload)
        }
      }

      await queryClient.invalidateQueries({ queryKey: ['workflowStages'] })
      setMessage({
        kind: 'success',
        text: `${currentModule.name} workflow saved. It applies to new requisitions immediately.`,
      })
    } catch (e: any) {
      setMessage({
        kind: 'danger',
        text: e?.response?.data
          ? JSON.stringify(e.response.data).slice(0, 300)
          : 'Could not save the workflow.',
      })
    } finally {
      setSaving(false)
    }
  }

  if (isLoading || !currentModule) {
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
      <div className="col-lg-10">
        <div className="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <nav aria-label="breadcrumb">
              <ol className="breadcrumb mb-1">
                <li className="breadcrumb-item">
                  <Link to="/admin/form-builder">Configuration</Link>
                </li>
                <li className="breadcrumb-item active">{currentModule.name}</li>
              </ol>
            </nav>
            <h5 className="mb-0">Approval workflow</h5>
          </div>
          <div className="d-flex gap-2">
            <Link to="/admin/form-builder" className="btn btn-sm btn-outline-secondary">
              <i className="bi bi-list-ul me-1"></i> Fields
            </Link>
            <button className="btn btn-sm btn-primary" onClick={addStage}>
              <i className="bi bi-plus-lg me-1"></i> Add stage
            </button>
          </div>
        </div>

        {message && (
          <div className={`alert alert-${message.kind} py-2 small`}>{message.text}</div>
        )}

        {visible.length === 0 ? (
          <div className="alert alert-warning">
            This workflow has no stages. Use <strong>Add stage</strong> to start a chain.
          </div>
        ) : (
          (drafts ?? serverStages.map(toDraft)).map((stage, index) => {
            if (stage.removed) return null
            return (
              <div className="card mb-3" key={stage.id ?? `new-${index}`}>
                <div className="card-header d-flex align-items-center justify-content-between py-2">
                  <div>
                    <span className="badge text-bg-secondary me-2">
                      {(drafts ?? serverStages.map(toDraft))
                        .filter((d) => !d.removed)
                        .findIndex((d) => d === stage) + 1}
                    </span>
                    <strong>{stage.name || 'New stage'}</strong>
                    <code className="ms-2 small text-muted">
                      {stage.id === null ? slugify(stage.name) : stage.key}
                    </code>
                  </div>
                  <div className="form-check form-switch mb-0">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id={`stage-${index}-active`}
                      checked={stage.is_active}
                      onChange={(e) => patch(index, { is_active: e.target.checked })}
                    />
                    <label className="form-check-label small" htmlFor={`stage-${index}-active`}>
                      Active
                    </label>
                  </div>
                </div>
                <div className="card-body">
                  <div className="row g-3">
                    <div className="col-md-5">
                      <label className="form-label">Stage name</label>
                      <input
                        type="text"
                        className="form-control form-control-sm"
                        value={stage.name}
                        onChange={(e) => patch(index, { name: e.target.value })}
                      />
                      <div className="form-text">Shown to approvers and on the tracking page.</div>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Who can act here</label>
                      <select
                        className="form-select form-select-sm"
                        value={stage.approver_role}
                        onChange={(e) => patch(index, { approver_role: e.target.value })}
                      >
                        <option value="">Any approver</option>
                        {roleChoices.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                      <div className="form-text">
                        Superadmin can always act, whatever this is set to.
                      </div>
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Allowed actions</label>
                      <input
                        type="text"
                        className="form-control form-control-sm"
                        value={stage.actions}
                        onChange={(e) => patch(index, { actions: e.target.value })}
                      />
                      <div className="form-text">
                        {actionChoices.map((a, i) => (
                          <span key={a.value}>
                            <code>{a.value}</code>
                            {i < actionChoices.length - 1 ? ', ' : ''}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="col-12">
                      <label className="form-label">
                        Fields this stage may correct before approving
                      </label>
                      <div
                        className="border rounded p-2"
                        style={{ maxHeight: 170, overflow: 'auto' }}
                      >
                        {moduleFields.length === 0 ? (
                          <span className="text-muted small">
                            This module has no form fields yet.
                          </span>
                        ) : (
                          moduleFields.map((f) => (
                            <div className="form-check" key={f.id}>
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id={`amend-${index}-${f.id}`}
                                checked={stage.amendable_fields.includes(f.id)}
                                onChange={(e) =>
                                  patch(index, {
                                    amendable_fields: e.target.checked
                                      ? [...stage.amendable_fields, f.id]
                                      : stage.amendable_fields.filter((x) => x !== f.id),
                                  })
                                }
                              />
                              <label className="form-check-label small" htmlFor={`amend-${index}-${f.id}`}>
                                {f.label} <code className="text-muted">{f.key}</code>
                              </label>
                            </div>
                          ))
                        )}
                      </div>
                      <div className="form-text">
                        Tick <code>amend</code> in the actions above for these inputs to appear on
                        the approval screen.
                      </div>
                    </div>

                    <div className="col-12 d-flex align-items-center justify-content-between">
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id={`stage-${index}-terminal`}
                          checked={stage.is_terminal}
                          onChange={(e) => patch(index, { is_terminal: e.target.checked })}
                        />
                        <label className="form-check-label" htmlFor={`stage-${index}-terminal`}>
                          Final stage — end of the workflow
                        </label>
                      </div>
                      {visible.length > 1 && (
                        <div className="form-check">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id={`stage-${index}-delete`}
                            checked={stage.removed}
                            onChange={(e) => patch(index, { removed: e.target.checked })}
                          />
                          <label
                            className="form-check-label text-danger"
                            htmlFor={`stage-${index}-delete`}
                          >
                            Remove this stage
                          </label>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })
        )}

        <div className="alert alert-warning small">
          Removing a stage does not change requisitions already sitting at it — they keep their
          status until acted on. Add the new stage first if you are rearranging a live chain.
        </div>

        <button className="btn btn-primary" onClick={save} disabled={saving}>
          <i className="bi bi-check-lg me-1"></i> Save workflow
        </button>
      </div>
    </div>
  )
}
