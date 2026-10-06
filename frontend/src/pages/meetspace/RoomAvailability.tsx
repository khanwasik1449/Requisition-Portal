import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { apiErrorMessages, formatDateDMY, formatTimeHM } from '@/lib/utils'
import type { Room } from '@/lib/meetspace'

interface Suggestion {
  room: Room
  date: string
  start_time: string
  end_time: string
}

interface SearchData {
  searched: boolean
  results: Room[]
  suggestions: Suggestion[]
}

// Exact replica of meetspace/templates/meetspace/availability.html
export function RoomAvailability() {
  // main renders the bare form on GET and only fills in results after a POST,
  // so nothing is fetched until the first search.
  const [queryString, setQueryString] = useState<string | null>(null)

  const { data, isFetching, error } = useQuery({
    queryKey: ['roomSearch', queryString],
    queryFn: async () => (await api.get<SearchData>(`/meetspace/room-search/?${queryString}`)).data,
    enabled: queryString !== null,
    // A bad date/time is a normal answer from main's view, not a transient
    // failure -- retrying it would just multiply the same 400.
    retry: false,
  })

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const params = new URLSearchParams({
      date: (form.date as HTMLInputElement).value,
      start_time: (form.start_time as HTMLInputElement).value,
      end_time: (form.end_time as HTMLInputElement).value,
      number_of_participants: (form.number_of_participants as HTMLInputElement).value,
    })
    setQueryString(params.toString())
  }

  const results = data?.searched ? data.results : []
  const suggestions = data?.searched ? data.suggestions : []
  // availability view answers a malformed search with its own sentence.
  const searchError = error
    ? apiErrorMessages((error as any)?.response?.data, 'Enter a valid date, time range and participant count.')
    : []

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <div className="card mb-4">
          <div className="card-header">
            <i className="bi bi-search me-1"></i> Check availability
          </div>
          <div className="card-body">
            <form onSubmit={onSubmit} className="row g-2 align-items-end">
              <div className="col-md-3">
                <label className="form-label small">Date</label>
                <input type="date" name="date" className="form-control form-control-sm" required />
              </div>
              <div className="col-md-2">
                <label className="form-label small">From</label>
                <input
                  type="time"
                  name="start_time"
                  className="form-control form-control-sm"
                  required
                />
              </div>
              <div className="col-md-2">
                <label className="form-label small">To</label>
                <input
                  type="time"
                  name="end_time"
                  className="form-control form-control-sm"
                  required
                />
              </div>
              <div className="col-md-3">
                <label className="form-label small">Participants</label>
                <input
                  type="number"
                  name="number_of_participants"
                  className="form-control form-control-sm"
                  min={1}
                  required
                />
              </div>
              <div className="col-md-2">
                <button type="submit" className="btn btn-primary btn-sm w-100" disabled={isFetching}>
                  Search
                </button>
              </div>
            </form>
          </div>
        </div>

        {searchError.length > 0 && (
          <div className="alert alert-danger py-2 small">{searchError.join(' ')}</div>
        )}

        {data?.searched && (
          <>
            {results.length > 0 ? (
              <div className="card">
                <div className="card-header">
                  <i className="bi bi-check-circle me-1"></i> Available rooms
                </div>
                <div className="table-responsive">
                  <table className="table table-sm align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th>Room</th>
                        <th>Floor</th>
                        <th>Capacity</th>
                        <th className="text-end"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((room) => (
                        <tr key={room.id}>
                          <td className="fw-semibold">{room.room_number}</td>
                          <td>{room.floor}</td>
                          <td>
                            {room.min_occupancy}–{room.max_occupancy}
                          </td>
                          <td className="text-end">
                            <Link to="/meetspace/bookings/new" className="btn btn-sm btn-primary">
                              Book
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="alert alert-warning">
                <i className="bi bi-exclamation-triangle me-1"></i>
                No rooms are free for that slot
                {suggestions.length > 0 ? '. Here are the nearest alternatives' : ''}.
              </div>
            )}

            {suggestions.length > 0 && (
              <div className="card mt-3">
                <div className="card-header">
                  <i className="bi bi-lightbulb me-1"></i> Suggested slots
                </div>
                <div className="table-responsive">
                  <table className="table table-sm align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th>Room</th>
                        <th>Date</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {suggestions.map((s, i) => (
                        <tr key={i}>
                          <td className="fw-semibold">Room {s.room.room_number}</td>
                          <td>{formatDateDMY(s.date)}</td>
                          <td>
                            {formatTimeHM(s.start_time)}–{formatTimeHM(s.end_time)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
