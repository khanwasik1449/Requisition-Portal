// API Response Types
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiError {
  detail?: string
  non_field_errors?: string[]
  [key: string]: unknown
}

// User Types
export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  /** Not returned by the API — the account has no such column. */
  full_name?: string
  role: UserRole
  role_display: string
  department?: string
  employee_id?: string
  phone?: string
  is_active: boolean
  is_staff: boolean
  date_joined: string
  last_login: string | null
}

export type UserRole =
  | 'admin'
  | 'supervisor'
  | 'grants'
  | 'transport_admin'
  | 'ict_admin'
  | 'internal_admin'
  | 'hr_admin'
  | 'requester'

// Transport Types
export interface Vehicle {
  id: number
  name: string
  registration_number: string
  capacity: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Driver {
  id: number
  name: string
  license_number: string
  phone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TransportRequisition {
  id: number
  request_number: string
  user: number
  user_name?: string
  user_email?: string
  destination: string
  purpose: string
  departure_date: string
  departure_time: string
  return_date: string
  return_time: string
  passenger_count: number
  project_code?: string
  budget_code?: string
  status: TransportStatus
  status_display: string
  vehicle?: number | Vehicle
  vehicle_name?: string
  driver?: number | Driver
  driver_name?: string
  extra_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type TransportStatus =
  | 'pending_first'
  | 'pending_grants'
  | 'pending_transport'
  | 'approved'
  | 'assigned'
  | 'rejected'
  | 'pending_second'

export interface TransportAction {
  action: 'approve' | 'decline' | 'amend' | 'assign'
  comment?: string
  project_code?: string
  budget_code?: string
  vehicle_id?: number | null
  driver_id?: number | null
}

// MeetSpace Types
export interface Room {
  id: number
  name: string
  capacity: number
  location?: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Booking {
  id: number
  room: number | Room
  room_name?: string
  user?: number | User
  user_name?: string
  email: string
  title: string
  description?: string
  start_time: string
  end_time: string
  attendees_count?: number
  status: BookingStatus
  status_display: string
  created_at: string
  updated_at: string
}

export type BookingStatus = 'pending' | 'approved' | 'rejected' | 'alternative_suggested'

export interface BookingAction {
  action: 'approve' | 'decline' | 'suggest_alternative'
  comment?: string
  alternative_room_id?: number | null
  alternative_start_time?: string | null
  alternative_end_time?: string | null
}

export interface Announcement {
  id: number
  title: string
  content: string
  attachment?: string
  created_by: number | User
  is_published: boolean
  created_at: string
  updated_at: string
}

// ICT Types
export interface ICTRequisition {
  id: number
  request_number: string
  user: number
  user_name?: string
  device_equipment: string
  quantity: number
  justification: string
  specifications?: string
  status: ICTStatus
  status_display: string
  extra_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type ICTStatus = 'pending' | 'approved' | 'rejected'

export interface ICTAction {
  action: 'approve' | 'decline'
  comment?: string
}

// Internal Types
export interface InternalRequisition {
  id: number
  request_number: string
  user: number
  user_name?: string
  department: string
  item_description: string
  quantity: number
  estimated_cost: number
  justification?: string
  status: InternalStatus
  status_display: string
  extra_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type InternalStatus = 'pending' | 'approved' | 'rejected'

export interface InternalAction {
  action: 'approve' | 'decline'
  comment?: string
}

// Contracts Types
export interface Contract {
  id: number
  employee: number | User
  employee_name?: string
  contract_type: string
  start_date: string
  end_date?: string
  salary: number
  status: string
  status_display: string
  file?: string
  created_at: string
  updated_at: string
}

export interface EmailConfig {
  id: number
  name: string
  host: string
  port: number
  username: string
  password: string
  use_tls: boolean
  use_ssl: boolean
  from_email: string
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface EmailLog {
  id: number
  config: number
  recipient: string
  subject: string
  status: string
  error_message?: string
  created_at: string
}

// Employees Types
export interface Employee {
  id: number
  user: number | User
  employee_id: string
  department: string
  designation: string
  date_of_joining: string
  salary: number
  bank_account?: string
  pan_number?: string
  created_at: string
  updated_at: string
}

// Payslip Types
export interface Payslip {
  id: number
  employee: number | Employee
  employee_name?: string
  month: number
  year: number
  basic_salary: number
  house_rent: number
  conveyance: number
  medical: number
  other_allowances: number
  gross_salary: number
  income_tax: number
  provident_fund: number
  professional_tax: number
  other_deductions: number
  net_salary: number
  generated_at: string
  created_at: string
  updated_at: string
}

export interface PayslipRequest {
  id: number
  employee: number | Employee
  employee_name?: string
  month: number
  year: number
  status: string
  status_display: string
  file?: string
  created_at: string
  updated_at: string
}

// Portal Config Types
export interface Module {
  id: number
  key: string
  name: string
  description?: string
  is_enabled: boolean
  is_visible: boolean
  order: number
  icon?: string
  created_at: string
  updated_at: string
}

export interface FormField {
  id: number
  module: number
  key: string
  label: string
  field_type: string
  is_required: boolean
  step: number
  order: number
  choices?: string
  help_text?: string
  placeholder?: string
  default_value?: string
  validation_regex?: string
  db_column?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WorkflowStage {
  id: number
  module: number
  name: string
  approver_role: string
  order: number
  actions: string
  amendable_fields?: string
  is_terminal: boolean
  created_at: string
  updated_at: string
}

// Notifications Types
export interface AuditLog {
  id: number
  user?: number | User
  user_name?: string
  action: string
  action_display: string
  content_type?: string
  object_id?: number
  object_repr?: string
  comment?: string
  ip_address?: string
  user_agent?: string
  created_at: string
}

export interface NotificationEmailLog {
  id: number
  recipient: string
  subject: string
  status: string
  error_message?: string
  created_at: string
}

// Dashboard Types
export interface DashboardStats {
  transport?: { total: number; pending: number }
  meetspace?: { total: number; pending: number }
  ict?: { total: number; pending: number }
  internal?: { total: number; pending: number }
  pending_users?: number
  my_requests?: {
    transport: number
    ict: number
    internal: number
    bookings: number
  }
}

// Public Types
export interface PublicModule {
  id: number
  key: string
  name: string
  description?: string
  is_enabled: boolean
  is_visible: boolean
  order: number
  icon?: string
}