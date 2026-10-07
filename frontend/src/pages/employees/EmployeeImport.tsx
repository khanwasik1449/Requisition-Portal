import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash } from '@/lib/flash'

interface ImportResult {
  detail: string
  warning: string
  created: number
  failed: number
}

// employees/templates/employees/import.html -- <style> block, verbatim.
const css = `
  :root { --c-success: #16A34A; --c-bg: #F7F6F3; --c-surface: #FFFFFF; --c-border: rgba(0,0,0,0.08); --c-accent: #2563EB; --c-muted: #6B6A66; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Arial, sans-serif; background: var(--c-bg); }
  .wrapper { max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
  .card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 1.5rem; }
  h1 { margin-bottom: 1rem; }
  .field { margin-bottom: 1rem; }
  .field label { display: block; margin-bottom: 5px; font-weight: 500; color: var(--c-muted); }
  .field input, .field select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; }
  .btn { background: var(--c-success); color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; }
  .helper { font-size: 12px; color: var(--c-muted); margin-top: 4px; }
  .alert { padding: 12px; border-radius: 8px; margin-bottom: 1rem; }
  .alert-success { background: #d4edda; color: #155724; }
`

// Replica of employees/templates/employees/import.html
export function EmployeeImport() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  // A failed import re-renders this page in main (import.html's own messages
  // block), so the sentence is shown inline -- and the shared flash slot is
  // dropped on unmount, because HrLayout only drains it on a navigation.
  const ownsFlash = useRef(false)

  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  const upload = useMutation({
    mutationFn: async (csv: File) => {
      const body = new FormData()
      body.append('file', csv)
      const response = await api.post<ImportResult>('/employees/import/', body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: (data) => {
      ownsFlash.current = false
      queryClient.invalidateQueries({ queryKey: ['employees'] })
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
      // main queues the count as a success and the failed rows as a warning;
      // the slot holds one message, so both sentences ride together.
      if (data.warning) setFlash('warning', `${data.detail} ${data.warning}`)
      else setFlash('success', data.detail)
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

      <div className="wrapper">
        <h1>Import Employees</h1>

        {error && (
          <div className="alert alert-success">{error}</div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault()
            setError(null)
            if (file) upload.mutate(file)
          }}
        >
          <div className="card">
            <div className="field">
              <label>Employee CSV (PIN, Name, Designation, Gender, TIN)</label>
              <input
                type="file"
                name="file"
                accept=".csv"
                required
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <div className="helper">Upload CSV with employee details</div>
            </div>
            <button type="submit" className="btn" disabled={upload.isPending}>
              Import
            </button>
          </div>
        </form>
      </div>
    </>
  )
}
