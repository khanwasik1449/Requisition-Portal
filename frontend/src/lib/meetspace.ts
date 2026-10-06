// Shared by the screens that reproduce meetspace/templates/meetspace/*.html,
// so the same two rules cannot drift apart across six pages.

/**
 * meetspace.views._is_hr_admin — `user.is_admin() or user.is_hr_admin()`,
 * which on the account model is simply the admin or hr_admin role.
 *
 * Templates gate rooms, announcements and the extra list column on this flag,
 * and it is only available client-side through the signed-in role.
 */
export function isHrAdmin(role?: string | null): boolean {
  return role === 'admin' || role === 'hr_admin'
}

/**
 * The four-way badge condition booking_list.html, dashboard.html and
 * track.html all repeat verbatim: approved -> success, pending -> warning,
 * rejected or cancelled -> danger, anything else (alternatives) -> info.
 */
export function statusBadgeClass(status: string): string {
  if (status === 'approved') return 'bg-success'
  if (status === 'pending') return 'bg-warning text-dark'
  if (status === 'rejected' || status === 'cancelled') return 'bg-danger'
  return 'bg-info'
}

/** A booking row as BookingListSerializer / BookingTrackSerializer emit it. */
export interface BookingRow {
  id: number
  meeting_title: string
  date?: string
  start_time: string
  end_time: string
  status: string
  status_display?: string
  number_of_participants?: number
  requirements?: string
  cancellation_reason?: string
  room_number?: string
  room?: { room_number: string; floor: string }
  user_name?: string
}

/** A room row, including the `booking_count` room_list.html prints. */
export interface Room {
  id: number
  room_number: string
  floor: string
  min_occupancy: number
  max_occupancy: number
  is_active: boolean
  booking_count?: number
}
