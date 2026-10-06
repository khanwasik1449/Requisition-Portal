import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
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
  field_type: string
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

interface Choice {
  value: string
  label: string
}

interface FormState {
  module: number
  label: string
  key: string
  field_type: string
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

// Every default is the model's, so a freshly opened "Add field" form matches
// what {{ form }} renders in field_edit.html -- including `is_system` ticking
// itself, which is why a brand-new key has to be unticked to save.
const EMPTY: Omit<FormState, 'module'> = {
  label: '',
  key: '',
  field_type: 'text',
  help_text: '',
  placeholder: '',
  step: 1,
  order: 0,
  required: false,
  is_system: true,
  visible_to_requester: true,
  show_in_review: true,
  options: '',
}

type ErrorMap = Record<string, string[]>

/**
 * Replica of portal_config/templates/portal_config/field_edit.html.
 *
 * Route shapes:
 *   /admin/form-builder/fields/new?module=<key>
 *   /admin/form-builder/fields/<id>/edit
 */
export function FormFieldEdit() {
  const { fieldId } = useParams<{ fieldId: string }>()
  const isEdit = !!fieldId
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [form, setForm] = useState<FormState>({ ...EMPTY, module: 0 })
  const [errors, setErrors] = useState<ErrorMap>({})
  const [nonField, setNonField] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [dirty, setDirty] = useState(false)

  const { data: modules } = useQuery({
    queryKey: ['modules'],
    queryFn: async () => getAllResults<Module>('/modules/'),
  })

  const { data: record, isLoading: recordLoading } = useQuery({
    queryKey: ['formField', fieldId],
    enabled: isEdit,
    queryFn: async () => (await api.get<FormField>(`/form-fields/${fieldId}/`)).data,
  })

  const { data: choices } = useQuery({
    queryKey: ['portalChoices'],
    queryFn: async () => (await api.get<{ field_types: Choice[] }>('/portal-choices/')).data,
  })

  // When editing, the module comes from the record; when adding, from ?module=.
  const moduleKey = isEdit
    ? modules?.results.find((m) => m.id === record?.module)?.key || ''
    : searchParams.get('module') || ''
  const currentModule = modules?.results.find((m) => m.key === moduleKey)

  useEffect(() => {
    if (dirty) return
    if (isEdit) {
      if (record) setForm({ ...record })
    } else if (currentModule) {
      setForm({ ...EMPTY, module: currentModule.id })
    }
  }, [record, currentModule, isEdit, dirty])

  const set = <K extends keyof FormState>(name: K, value: FormState[K]) => {
    setDirty(true)
    setForm((prev) => ({ ...prev, [name]: value }))
    // Clear the field's own error as soon as the user starts fixing it.
    setErrors((prev) => {
      if (!prev[name as string]) return prev
      const next = { ...prev }
      delete next[name as string]
      return next
    })
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentModule) return
    setBusy(true)
    setErrors({})
    setNonField([])
    try {
      const payload = { ...form, module: currentModule.id }
      if (isEdit) await api.patch(`/form-fields/${fieldId}/`, payload)
      else await api.post('/form-fields/', payload)
      // Without this the list reads the rows it cached before the change and
      // a freshly saved field is invisible until a manual reload.
      await queryClient.invalidateQueries({ queryKey: ['formFields'] })
      await queryClient.invalidateQueries({ queryKey: ['formField', fieldId] })
      navigate(`/admin/form-builder/fields?module=${currentModule.key}`)
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

  if (!isEdit && !searchParams.get('module') && modules) {
    return (
      <div className="alert alert-warning">
        Choose a module first. <Link to="/admin/form-builder">Back to Configuration</Link>
      </div>
    )
  }

  if (recordLoading || (isEdit && !record)) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  if (isEdit && record && !currentModule) {
    return <div className="alert alert-danger">Could not work out which module this field belongs to.</div>
  }

  const backUrl = `/admin/form-builder/fields?module=${moduleKey}`

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <nav aria-label="breadcrumb">
          <ol className="breadcrumb">
            <li className="breadcrumb-item">
              <Link to="/admin/form-builder">Configuration</Link>
            </li>
            <li className="breadcrumb-item">
              <Link to={backUrl}>{currentModule?.name || 'Module'} fields</Link>
            </li>
            <li className="breadcrumb-item active">{isEdit ? 'Edit' : 'Add field'}</li>
          </ol>
        </nav>

        <div className="card">
          <div className="card-header d-flex align-items-center gap-2">
            <i className="bi bi-pencil-square" style={{ color: '#d97706' }}></i>
            {isEdit ? 'Edit field' : 'Add a field'}
          </div>
          <div className="card-body">
            <form onSubmit={submit}>
              {nonField.length > 0 &&
                nonField.map((message, i) => (
                  <div className="alert alert-danger small" key={i}>
                    {message}
                  </div>
                ))}

              <div className="row g-3">
                <div className="col-md-8">
                  <label className="form-label" htmlFor="ff-label">
                    Label shown to the user
                  </label>
                  <input
                    id="ff-label"
                    type="text"
                    className="form-control"
                    maxLength={200}
                    required
                    value={form.label}
                    onChange={(e) => set('label', e.target.value)}
                  />
                  {fieldError('label')}
                </div>
                <div className="col-md-4">
                  <label className="form-label" htmlFor="ff-key">
                    Key
                  </label>
                  <input
                    id="ff-key"
                    type="text"
                    className="form-control"
                    maxLength={60}
                    required
                    value={form.key}
                    onChange={(e) => set('key', e.target.value)}
                  />
                  {fieldError('key')}
                </div>

                <div className="col-md-6">
                  <label className="form-label" htmlFor="ff-type">
                    Field type
                  </label>
                  <select
                    id="ff-type"
                    className="form-select"
                    value={form.field_type}
                    onChange={(e) => set('field_type', e.target.value)}
                  >
                    {(choices?.field_types || [{ value: 'text', label: 'Text' }]).map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                  {fieldError('field_type')}
                </div>
                <div className="col-md-3">
                  <label className="form-label" htmlFor="ff-step">
                    Step
                  </label>
                  <input
                    id="ff-step"
                    type="number"
                    className="form-control"
                    min={0}
                    required
                    value={form.step}
                    onChange={(e) => set('step', Number(e.target.value))}
                  />
                  {fieldError('step')}
                </div>
                <div className="col-md-3">
                  <label className="form-label" htmlFor="ff-order">
                    Order within step
                  </label>
                  <input
                    id="ff-order"
                    type="number"
                    className="form-control"
                    min={0}
                    required
                    value={form.order}
                    onChange={(e) => set('order', Number(e.target.value))}
                  />
                  {fieldError('order')}
                </div>

                <div className="col-12">
                  <label className="form-label" htmlFor="ff-help">
                    Help text
                  </label>
                  <input
                    id="ff-help"
                    type="text"
                    className="form-control"
                    value={form.help_text}
                    onChange={(e) => set('help_text', e.target.value)}
                  />
                  {fieldError('help_text')}
                </div>
                <div className="col-12">
                  <label className="form-label" htmlFor="ff-placeholder">
                    Placeholder
                  </label>
                  <input
                    id="ff-placeholder"
                    type="text"
                    className="form-control"
                    maxLength={200}
                    value={form.placeholder}
                    onChange={(e) => set('placeholder', e.target.value)}
                  />
                  {fieldError('placeholder')}
                </div>
                <div className="col-12">
                  <label className="form-label" htmlFor="ff-options">
                    Choices (dropdown and radio only)
                  </label>
                  <textarea
                    id="ff-options"
                    className="form-control"
                    rows={4}
                    value={form.options}
                    onChange={(e) => set('options', e.target.value)}
                  />
                  <div className="form-text">
                    One per line, written as <code>value|Label shown to the user</code>.
                  </div>
                  {fieldError('options')}
                </div>

                <div className="col-12">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ff-required"
                      checked={form.required}
                      onChange={(e) => set('required', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="ff-required">
                      Required
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ff-is-system"
                      checked={form.is_system}
                      onChange={(e) => set('is_system', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="ff-is-system">
                      Stored in a database column
                    </label>
                  </div>
                  {fieldError('is_system')}
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ff-visible"
                      checked={form.visible_to_requester}
                      onChange={(e) => set('visible_to_requester', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="ff-visible">
                      Visible on the form
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ff-review"
                      checked={form.show_in_review}
                      onChange={(e) => set('show_in_review', e.target.checked)}
                    />
                    <label className="form-check-label" htmlFor="ff-review">
                      Show on the review screen
                    </label>
                  </div>
                </div>
              </div>

              <div className="d-flex gap-2 mt-4">
                <button type="submit" className="btn btn-primary" disabled={busy}>
                  {busy ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1" role="status"></span>
                      Saving...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-check-lg me-1"></i> Save field
                    </>
                  )}
                </button>
                <Link to={backUrl} className="btn btn-outline-secondary">
                  Cancel
                </Link>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
