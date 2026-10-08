/**
 * Spinner shown while a form waits on its pre-fill lookup.
 *
 * The personal details on the request forms come from `/api/employees/mine/`,
 * which resolves after the form's first render. `defaultValue` is only read
 * when an input mounts, so a form that rendered straight away would show the
 * account's own values and never pick up the employee's PIN. The forms using
 * `useStaffDefaults()` hold off until `loading` is false instead.
 */
export function FormLoading() {
  return (
    <div className="d-flex justify-content-center py-5">
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  )
}
