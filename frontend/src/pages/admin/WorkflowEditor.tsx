export function WorkflowEditor() {
  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Workflow Editor</h2>
          <p className="text-muted mb-0 small">Configure approval workflow stages</p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <i className="bi bi-diagram-3 me-2" style={{ color: '#2563eb' }}></i>Workflow Configuration
        </div>
        <div className="card-body text-center py-5">
          <i className="bi bi-diagram-3" style={{ fontSize: '3rem', color: '#cbd5e1' }}></i>
          <p className="text-muted mt-3 mb-0">
            Define approval stages, assign approvers, and configure workflow rules.
          </p>
        </div>
      </div>
    </>
  )
}
