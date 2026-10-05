import { useAuth } from '@/auth/hooks'

export interface StaffDefaults {
  /** "First Last", falling back to the username when no name is on file. */
  full_name: string
  email_address: string
  mobile_number: string
}

/**
 * Personal details every requisition form asks for, taken from the signed-in
 * account so a returning member of staff never re-types them.
 *
 * All fields stay ordinary inputs — the values are only the initial ones, and
 * the applicant can edit any of them before submitting.
 *
 * Designation, PIN and department are deliberately absent: they are not stored
 * on the account record (they live in the HR employees table, which is keyed by
 * PIN rather than by user), so there is nothing to pre-fill them from.
 */
export function useStaffDefaults(): StaffDefaults {
  const { user } = useAuth()
  if (!user) return { full_name: '', email_address: '', mobile_number: '' }

  const composed = [user.first_name, user.last_name].filter(Boolean).join(' ')

  return {
    full_name: composed || user.username || '',
    email_address: user.email || '',
    mobile_number: user.phone || '',
  }
}
