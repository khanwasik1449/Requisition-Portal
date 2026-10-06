import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { apiErrorMessages } from '@/lib/utils'

// Exact replica of meetspace/templates/meetspace/announcement_form.html
export function AnnouncementForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const attachmentRef = useRef<HTMLInputElement>(null)
  const [errors, setErrors] = useState<string[]>([])

  const post = useMutation({
    mutationFn: async (body: FormData) =>
      api.post('/announcements/', body, {
        // The shared axios client defaults to application/json, which would
        // make axios JSON-encode the FormData and drop the file outright.
        // `false` removes the header, so the browser writes the boundary.
        headers: { 'Content-Type': false },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetspaceDashboard'] })
      navigate('/meetspace')
    },
    onError: (err: any) =>
      setErrors(
        apiErrorMessages(err.response?.data, 'Failed to post the announcement.'),
      ),
  })

  return (
    <div className="row justify-content-center">
      <div className="col-lg-7">
        <div className="card">
          <div className="card-header">
            <i className="bi bi-megaphone me-1"></i> Post an announcement
          </div>
          <div className="card-body">
            {errors.length > 0 && (
              <div className="alert alert-danger py-2 small mb-3">
                {errors.map((message, i) => (
                  <div key={i}>{message}</div>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault()
                setErrors([])
                const form = e.currentTarget
                const body = new FormData()
                const message = (form.message as HTMLTextAreaElement).value
                if (message) body.append('message', message)
                const file = attachmentRef.current?.files?.[0]
                if (file) body.append('attachment', file)
                post.mutate(body)
              }}
            >
              <div className="mb-3">
                <label className="form-label">Message</label>
                <textarea
                  name="message"
                  rows={4}
                  className="form-control"
                  placeholder="What should everyone know?"
                />
              </div>
              <div className="mb-3">
                <label className="form-label">
                  Attachment <span className="text-muted">(optional)</span>
                </label>
                <input type="file" name="attachment" className="form-control" ref={attachmentRef} />
              </div>
              <div className="d-flex gap-2">
                <button type="submit" className="btn btn-primary" disabled={post.isPending}>
                  <i className="bi bi-check-lg me-1"></i> Post
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => navigate('/meetspace')}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
