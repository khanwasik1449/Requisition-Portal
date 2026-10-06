import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/api/axios'
import { getAllResults } from '@/lib/paginate'
import { useAuth } from '@/auth/hooks'
import { isHrAdmin, type Room } from '@/lib/meetspace'

// Exact replica of meetspace/templates/meetspace/room_list.html
export function RoomList() {
  const { user } = useAuth()
  const hrAdmin = isHrAdmin(user?.role)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['rooms'],
    queryFn: async () => getAllResults<Room>('/rooms/'),
  })

  // room_list.html's Retire/Restore link flips `is_active` and comes straight
  // back, so this only needs to put the row back in the cache.
  const toggle = useMutation({
    mutationFn: async (room: Room) =>
      api.patch(`/rooms/${room.id}/`, { is_active: !room.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rooms'] }),
  })

  const rooms = data?.results ?? []

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="page-title mb-1">Rooms</h2>
          <p className="text-muted mb-0 small">Meeting rooms available for booking</p>
        </div>
        {hrAdmin && (
          <Link to="/meetspace/rooms/new" className="btn btn-primary">
            <i className="bi bi-plus-lg me-1"></i> Add Room
          </Link>
        )}
      </div>

      <div className="card">
        <div className="table-responsive">
          <table className="table align-middle mb-0">
            <thead className="table-light">
              <tr>
                <th>Room</th>
                <th>Floor</th>
                <th>Capacity</th>
                <th>Approved bookings</th>
                <th>Status</th>
                {hrAdmin && <th className="text-end">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  </td>
                </tr>
              ) : rooms.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center text-muted py-4">
                    No rooms configured.
                  </td>
                </tr>
              ) : (
                rooms.map((room) => (
                  <tr key={room.id}>
                    <td className="fw-semibold">{room.room_number}</td>
                    <td>{room.floor}</td>
                    <td>
                      {room.min_occupancy}–{room.max_occupancy}
                    </td>
                    <td>{room.booking_count ?? 0}</td>
                    <td>
                      {room.is_active ? (
                        <span className="badge bg-success">Available</span>
                      ) : (
                        <span className="badge bg-secondary">Retired</span>
                      )}
                    </td>
                    {hrAdmin && (
                      <td className="text-end">
                        <Link
                          to={`/meetspace/rooms/${room.id}/edit`}
                          className="btn btn-sm btn-outline-secondary"
                        >
                          <i className="bi bi-pencil"></i>
                        </Link>{' '}
                        <button
                          type="button"
                          className={`btn btn-sm btn-outline-${room.is_active ? 'danger' : 'success'}`}
                          onClick={() => toggle.mutate(room)}
                        >
                          {room.is_active ? 'Retire' : 'Restore'}
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
