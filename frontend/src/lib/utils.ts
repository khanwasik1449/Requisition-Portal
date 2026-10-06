import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Django's settings.TIME_ZONE.
 *
 * main formats every `|date:` filter in this zone, so the React pages must too
 * or every approval stamp drifts by the difference between the server and the
 * viewer's clock. Keep this in sync with requisition_portal/settings.py.
 */
export const SERVER_TIME_ZONE = 'Africa/Nairobi'

/**
 * Django's `date:"M d, Y"` filter — "Oct 10, 2026", the date-only form used
 * for pick-up, drop-off and requisition dates.
 */
export function formatDateDMY(value?: string | Date | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: SERVER_TIME_ZONE,
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('month').slice(0, 3)} ${get('day')}, ${get('year')}`
}

/**
 * Django's `date:"M d"` filter — "Oct 09".
 *
 * dashboard.html's recent-bookings column uses this shorter shape rather than
 * the `M d, Y` form, so it needs its own helper.
 */
export function formatDateMD(value?: string | Date | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: SERVER_TIME_ZONE,
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('month').slice(0, 3)} ${get('day')}`
}

/**
 * Django's `|title` filter — Python's `str.title()`, underscore and all.
 *
 * dashboard.html prints each stats key through it, so `total_rooms` comes out
 * as `Total_Rooms`: a non-letter (the `_`) starts a new "word". A plain
 * capitalize would render `Total_rooms` and show.
 */
export function djangoTitle(value: string): string {
  let out = ''
  let atWordStart = true
  for (const ch of value) {
    if (/[A-Za-z]/.test(ch)) {
      out += atWordStart ? ch.toUpperCase() : ch.toLowerCase()
      atWordStart = false
    } else {
      out += ch
      atWordStart = true
    }
  }
  return out
}

/**
 * Django's `date:"d M Y"` filter — "05 Oct 2026".
 *
 * my_requisitions.html is the only template in main that uses this day-first
 * shape, so it gets its own helper rather than a format argument nobody else
 * needs.
 */
export function formatDateDayMonthYear(value?: string | Date | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: SERVER_TIME_ZONE,
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).formatToParts(d)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('day')} ${get('month').slice(0, 3)} ${get('year')}`
}

/**
 * Django's `time:"H:i"` filter — "09:00".
 *
 * Accepts both a bare time ("09:00:00", what TimeField serialises) and a full
 * timestamp, and deliberately does not shift either through the viewer's clock.
 */
export function formatTimeHM(value?: string | null): string {
  if (!value) return ''
  const m = /^(\d{2}):(\d{2})/.exec(value)
  return m ? `${m[1]}:${m[2]}` : value
}

export function formatDate(date: string | Date, format = 'PPP'): string {
  const d = new Date(date)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Django's `date:"M d, Y H:i"` filter, byte-for-byte.
 *
 * Every detail.html template in main stamps an approver or an assignment with
 * this exact shape — "Oct 05, 2026 17:12" — so all of them share this helper.
 *
 * The stamp is rendered in Django's timezone, not the viewer's: with USE_TZ on,
 * `{{ x|date:"..." }}` formats in settings.TIME_ZONE, so a Nairobi-time approval
 * must not read three hours later just because the browser sits in another zone.
 */
export function formatStamp(value?: string | Date | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)

  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: SERVER_TIME_ZONE,
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(d)

  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  // Some engines report midnight as hour "24" under hour12:false.
  const hour = get('hour') === '24' ? '00' : get('hour')
  return `${get('month').slice(0, 3)} ${get('day')}, ` +
         `${get('year')} ${hour}:${get('minute')}`
}

/**
 * Flattens a DRF error body into the lines main would have flashed.
 *
 * main collects its messages into a list and shows them one per alert; DRF
 * reports them per field (`{"floor": ["..."]}`) or grouped under
 * `non_field_errors`, so both shapes have to be read to reproduce the same
 * set of sentences.
 */
export function apiErrorMessages(data: unknown, fallback: string): string[] {
  const out: string[] = []
  const walk = (value: unknown) => {
    if (value == null) return
    if (Array.isArray(value)) return value.forEach(walk)
    if (typeof value === 'object') return Object.values(value).forEach(walk)
    out.push(String(value))
  }
  if (data && typeof data === 'object') walk(data)
  return out.length ? out : [fallback]
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    pending_first: 'bg-blue-100 text-blue-800',
    pending_grants: 'bg-purple-100 text-purple-800',
    pending_transport: 'bg-orange-100 text-orange-800',
    approved: 'bg-green-100 text-green-800',
    assigned: 'bg-indigo-100 text-indigo-800',
    rejected: 'bg-red-100 text-red-800',
    alternative_suggested: 'bg-teal-100 text-teal-800',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

export function getRoleColor(role: string): string {
  const colors: Record<string, string> = {
    admin: 'bg-red-100 text-red-800',
    supervisor: 'bg-blue-100 text-blue-800',
    grants: 'bg-purple-100 text-purple-800',
    transport_admin: 'bg-orange-100 text-orange-800',
    ict_admin: 'bg-green-100 text-green-800',
    internal_admin: 'bg-indigo-100 text-indigo-800',
    hr_admin: 'bg-pink-100 text-pink-800',
    requester: 'bg-gray-100 text-gray-800',
  }
  return colors[role] || 'bg-gray-100 text-gray-800'
}