/**
 * Stand-in for Django's `messages` framework.
 *
 * Every HR view in main redirects with `messages.success(...)` /
 * `messages.error(...)` and `contracts/base.html` renders the queue in
 * `#django-messages`. A React app has no request/session boundary to hang
 * those on, so the flash lives in a module slot: a page sets it just before
 * navigating, and `HrLayout` drains it on the next location change.
 */

export type FlashLevel = 'success' | 'error' | 'warning' | 'info'

export interface Flash {
  level: FlashLevel
  text: string
}

let pending: Flash | null = null

export function setFlash(level: FlashLevel, text: string): void {
  pending = { level, text }
}

/** Take the pending flash, if any, clearing it on the way out. */
export function takeFlash(): Flash | null {
  const flash = pending
  pending = null
  return flash
}

/** Pull the message out of a DRF error body (`detail`, `non_field_errors`,
 *  or a field->messages map) so an API failure reads like a Django message. */
export function flashFromError(error: unknown): Flash {
  const fallback = 'Something went wrong. Please try again.'
  if (!error || typeof error !== 'object') return { level: 'error', text: fallback }
  const body = (error as { response?: { data?: unknown } }).response?.data
  if (!body) return { level: 'error', text: fallback }
  if (typeof body === 'string') return { level: 'error', text: body }
  const data = body as Record<string, unknown>
  if (typeof data.detail === 'string') return { level: 'error', text: data.detail }
  if (Array.isArray(data.non_field_errors)) {
    return { level: 'error', text: data.non_field_errors.join(' ') }
  }
  const parts: string[] = []
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value)) parts.push(value.join(' '))
    else if (typeof value === 'string') parts.push(value)
  }
  if (parts.length) return { level: 'error', text: parts.join(' ') }
  return { level: 'error', text: fallback }
}
