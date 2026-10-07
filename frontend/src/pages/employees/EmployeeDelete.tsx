import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash } from '@/lib/flash'

interface Employee {
  id: number
  pin: string
  name: string
  designation: string
}

// employees/templates/employees/delete.html -- <style> block, verbatim.
const css = `
  :root { --c-bg: #F7F6F3; --c-surface: #FFFFFF; --c-border: rgba(0,0,0,0.08); --c-danger: #DC2626; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', Arial, sans-serif; background: var(--c-bg); }
  .wrapper { max-width: 500px; margin: 2rem auto; padding: 0 1rem; text-align: center; }
  .card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  h1 { margin-bottom: 1rem; }
  .employee-info { background: #FEF2F2; padding: 1rem; border-radius: 8px; margin: 1.5rem 0; }
  .employee-info p { margin: 5px 0; }
  .btn { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; text-decoration: none; cursor: pointer; }
  .btn-danger { background: var(--c-danger); color: white; border: none; }
  .btn-secondary { background: #6B7280; color: white; }
`

// Replica of employees/templates/employees/delete.html
export function EmployeeDelete() {
  const { pin } = useParams<{ pin: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [error, setError] = useState<string | null>(null)
  // HrLayout drains the shared flash slot only on a location change, so a
  // failure shown here is rendered inline as well and the pending slot is
  // dropped on unmount rather than surfacing on the next page.
  const ownsFlash = useRef(false)

  const { data: employee, isLoading, error: queryError } = useQuery({
    queryKey: ['employees', pin],
    queryFn: async () =>
      (await api.get<Employee>(`/employees/${encodeURIComponent(pin!)}/`)).data,
    enabled: Boolean(pin),
  })

  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  useEffect(() => {
    if (queryError) setError(flashFromError(queryError).text)
  }, [queryError])

  const remove = useMutation({
    mutationFn: async () =>
      api.delete(`/employees/${encodeURIComponent(pin!)}/`),
    onSuccess: () => {
      ownsFlash.current = false
      // The view clears the contract history hanging off the same PIN too.
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      setFlash(
        'success',
        'Employee and all related contracts deleted successfully.',
      )
      navigate('/hr/employees')
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setError(text)
    },
  })

  return (
    <>
      <PageStyle css={css} />

      {error && (
        <div className="app-message error">
          <span className="msg-close" onClick={() => setError(null)}>
            &times;
          </span>
          {error}
        </div>
      )}

      <div className="wrapper">
        <h1>Delete Employee</h1>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            setError(null)
            remove.mutate()
          }}
        >
          <div className="card">
            {employee && (
              <div className="employee-info">
                <p>
                  <strong>PIN:</strong> {employee.pin}
                </p>
                <p>
                  <strong>Name:</strong> {employee.name}
                </p>
                <p>
                  <strong>Designation:</strong> {employee.designation}
                </p>
              </div>
            )}

            <p style={{ color: '#DC2626', marginBottom: '1.5rem' }}>
              Are you sure you want to delete this employee?
            </p>

            <button
              type="submit"
              className="btn btn-danger"
              disabled={isLoading || remove.isPending}
            >
              Delete
            </button>
            <Link to="/hr/employees" className="btn btn-secondary">
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
