import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { apiErrorMessages } from '@/lib/utils'
import type { Room } from '@/lib/meetspace'

interface RoomDraft {
  room_number: string
  floor: string
  min_occupancy: number
  max_occupancy: number
}

const emptyDraft: RoomDraft = { room_number: '', floor: '', min_occupancy: 1, max_occupancy: 10 }

// Exact replica of meetspace/templates/meetspace/room_form.html
export function RoomForm() {
  const { roomId } = useParams<{ roomId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEdit = Boolean(roomId)

  const [draft, setDraft] = useState<RoomDraft>(emptyDraft)
  const [errors, setErrors] = useState<string[]>([])

  const existing = useQuery({
    queryKey: ['rooms', roomId],
    queryFn: async () => (await api.get<Room>(`/rooms/${roomId}/`)).data,
    enabled: isEdit,
  })

  useEffect(() => {
    if (existing.data) {
      setDraft({
        room_number: existing.data.room_number,
        floor: existing.data.floor,
        min_occupancy: existing.data.min_occupancy,
        max_occupancy: existing.data.max_occupancy,
      })
    }
  }, [existing.data])

  const save = useMutation({
    mutationFn: async () => {
      if (isEdit) return api.patch(`/rooms/${roomId}/`, draft)
      return api.post('/rooms/', draft)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      navigate('/meetspace/rooms')
    },
    onError: (err: any) => setErrors(apiErrorMessages(err.response?.data, 'Failed to save the room.')),
  })

  const field = (key: keyof RoomDraft, value: string) => {
    setDraft((prev) => ({
      ...prev,
      [key]: key === 'room_number' || key === 'floor' ? value : Number(value),
    }))
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-6">
        <div className="card">
          <div className="card-header">
            <i className="bi bi-door-open me-1"></i>
            {isEdit ? `Edit Room ${draft.room_number}` : 'Add a Room'}
          </div>
          <div className="card-body">
            {/* room_create/room_edit flash their sentences instead of rendering
                them beside a field, so they arrive as one alert. */}
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
                save.mutate()
              }}
            >
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label">Room number</label>
                  <input
                    type="text"
                    name="room_number"
                    className="form-control"
                    value={draft.room_number}
                    onChange={(e) => field('room_number', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Floor</label>
                  <input
                    type="text"
                    name="floor"
                    className="form-control"
                    value={draft.floor}
                    onChange={(e) => field('floor', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Minimum occupancy</label>
                  <input
                    type="number"
                    name="min_occupancy"
                    className="form-control"
                    min={1}
                    value={draft.min_occupancy}
                    onChange={(e) => field('min_occupancy', e.target.value)}
                    required
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Maximum occupancy</label>
                  <input
                    type="number"
                    name="max_occupancy"
                    className="form-control"
                    min={1}
                    value={draft.max_occupancy}
                    onChange={(e) => field('max_occupancy', e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="d-flex gap-2 mt-4">
                <button type="submit" className="btn btn-primary" disabled={save.isPending}>
                  <i className="bi bi-check-lg me-1"></i> Save
                </button>
                <Link to="/meetspace/rooms" className="btn btn-outline-secondary">
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
