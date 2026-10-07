import { useState } from 'react'
import { api, endpoints } from '@/api/axios'

/**
 * "Send Email Reminder" -- the per-row button main's requisition list pages
 * carry (`notifications:send_reminder`).
 *
 * main renders the outcome as a Django message on the list page it redirects
 * back to; the portal `Layout.tsx` has no flash-message consumer, so the
 * sentence is kept in a local notice slot instead. `useReminder` owns that
 * slot and the in-flight row, `ReminderButton` is the button itself.
 */

export type ReminderNotice = {
  level: 'success' | 'info' | 'error'
  text: string
} | null

export type ReminderType = 'ict' | 'transport' | 'internal'

export function useReminder() {
  const [notice, setNotice] = useState<ReminderNotice>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const send = async (reqType: ReminderType, id: number) => {
    setBusyId(id)
    setNotice(null)
    try {
      const { data } = await api.post(endpoints.sendReminder(reqType, id))
      setNotice({
        level: data.level === 'info' ? 'info' : 'success',
        text: data.detail,
      })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail
      setNotice({ level: 'error', text: detail || 'Could not send the reminder.' })
    } finally {
      setBusyId(null)
    }
  }

  return { notice, busyId, send }
}

export function ReminderButton({
  reqType,
  id,
  busy,
  onClick,
}: {
  reqType: ReminderType
  id: number
  busy: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className="btn btn-sm btn-outline-info"
      title="Send Email Reminder"
      disabled={busy}
      onClick={onClick}
    >
      <i className="bi bi-envelope"></i>
    </button>
  )
}
