export function FormBuilder() {
  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Form Builder & Workflows</h2>
          <p className="text-muted mb-0 small">Configure requisition forms and approval workflows</p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <i className="bi bi-puzzle me-2" style={{ color: '#2563eb' }}></i>Form Builder
        </div>
        <div className="card-body text-center py-5">
          <i className="bi bi-puzzle" style={{ fontSize: '3rem', color: '#cbd5e1' }}></i>
          <p className="text-muted mt-3 mb-0">
            Configure form fields, steps, and approval workflows for each requisition module.
          </p>
        </div>
      </div>
    </>
  )
}
