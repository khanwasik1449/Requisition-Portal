import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/auth/hooks'
import { api, endpoints } from '@/api/axios'

export interface StaffDefaults {
  /** "First Last", falling back to the username when no name is on file. */
  full_name: string
  email_address: string
  mobile_number: string
  /** From the HR employee record, matched on the account's email address. */
  pin_number: string
  designation: string
  /**
   * True until the employee lookup has resolved.
   *
   * The lookup is asynchronous, and a `defaultValue` prop is only read when the
   * input mounts -- so a form that renders before this flips to false would
   * pre-fill the account's own values and never pick up the employee's PIN.
   * Forms must hold off rendering until it is false.
   */
  loading: boolean
}

export interface EmployeeRecord {
  found: boolean
  pin: string
  name: string
  designation: string
  phone: string
  email: string
}

/**
 * The HR employee record belonging to the signed-in user, if there is one.
 *
 * `Employee` has no foreign key to `User`, so the record is matched on the
 * email address HR entered when it was created. This is what tells the portal
 * that the signed-in user *is* an employee -- the Requisitions menu and the
 * BRAC University email form are employees-only, and the admin account has no
 * employee record.
 */
export function useEmployeeRecord() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['my-employee'],
    queryFn: async () => (await api.get(endpoints.myEmployee())).data as EmployeeRecord,
    enabled: !!user,
  })
}

/**
 * Personal details every requisition form asks for, taken from the signed-in
 * account so a returning member of staff never re-types them.
 *
 * All fields stay ordinary inputs — the values are only the initial ones, and
 * the applicant can edit any of them before submitting.
 *
 * The account record holds a name, an email and a phone number, but **not** a
 * PIN: that lives on the HR `employees` row, which has no foreign key to the
 * user. `/api/employees/mine/` finds that row by matching the email address HR
 * entered when the employee was created, and the PIN and designation are read
 * from it. When there is no match the PIN and designation are simply left
 * empty rather than blocking the form.
 */
export function useStaffDefaults(): StaffDefaults {
  const { user } = useAuth()
  const { data, isLoading } = useEmployeeRecord()

  if (!user) {
    return {
      full_name: '',
      email_address: '',
      mobile_number: '',
      pin_number: '',
      designation: '',
      loading: true,
    }
  }

  const composed = [user.first_name, user.last_name].filter(Boolean).join(' ')
  const emp = data?.found ? data : null

  return {
    // The employee record wins where HR spelt the name differently.
    full_name: emp?.name || composed || user.username || '',
    email_address: emp?.email || user.email || '',
    mobile_number: emp?.phone || user.phone || '',
    pin_number: emp?.pin || '',
    designation: emp?.designation || '',
    loading: isLoading,
  }
}
