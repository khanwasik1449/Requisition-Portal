import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const accessToken = localStorage.getItem('access_token')
    if (accessToken && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle token refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post('/api/auth/refresh/', { refresh: refreshToken })
          const { access } = response.data

          localStorage.setItem('access_token', access)
          api.defaults.headers.common['Authorization'] = `Bearer ${access}`
          originalRequest.headers.Authorization = `Bearer ${access}`

          processQueue(null, access)
          return api(originalRequest)
        } catch (refreshError) {
          processQueue(refreshError, null)
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          delete api.defaults.headers.common['Authorization']
          window.location.href = '/login'
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      } else {
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

// API endpoint helpers
export const endpoints = {
  // Auth
  login: () => '/auth/login/',
  refresh: () => '/auth/refresh/',
  logout: () => '/auth/logout/',
  me: () => '/auth/me/',
  changePassword: () => '/auth/change-password/',
  register: () => '/auth/register/',

  // Users
  users: () => '/users/',
  user: (id: number) => `/users/${id}/`,
  approveUser: (id: number) => `/users/${id}/approve/`,
  rejectUser: (id: number) => `/users/${id}/reject/`,

  // Transport
  transport: () => '/transport/',
  transportDetail: (id: number) => `/transport/${id}/`,
  transportApprove: (id: number) => `/transport/${id}/approve/`,
  transportDecline: (id: number) => `/transport/${id}/decline/`,
  transportAmend: (id: number) => `/transport/${id}/amend/`,
  transportAssign: (id: number) => `/transport/${id}/assign/`,
  transportMyRequests: () => '/transport/my_requests/',
  transportPending: () => '/transport/pending/',
  vehicles: () => '/vehicles/',
  drivers: () => '/drivers/',

  // MeetSpace
  rooms: () => '/rooms/',
  bookings: () => '/bookings/',
  bookingDetail: (id: number) => `/bookings/${id}/`,
  bookingApprove: (id: number) => `/bookings/${id}/approve/`,
  bookingDecline: (id: number) => `/bookings/${id}/decline/`,
  bookingSuggestAlternative: (id: number) => `/bookings/${id}/suggest_alternative/`,
  bookingMyBookings: () => '/bookings/my_bookings/',
  bookingAvailability: () => '/bookings/availability/',
  announcements: () => '/announcements/',

  // ICT
  ict: () => '/ict/',
  ictDetail: (id: number) => `/ict/${id}/`,
  ictApprove: (id: number) => `/ict/${id}/approve/`,
  ictDecline: (id: number) => `/ict/${id}/decline/`,
  ictMyRequests: () => '/ict/my_requests/',

  // Internal
  internal: () => '/internal/',
  internalDetail: (id: number) => `/internal/${id}/`,
  internalApprove: (id: number) => `/internal/${id}/approve/`,
  internalDecline: (id: number) => `/internal/${id}/decline/`,
  internalMyRequests: () => '/internal/my_requests/',

  // Contracts
  contracts: () => '/contracts/',
  emailConfigs: () => '/email-configs/',
  emailLogs: () => '/email-logs/',

  // Employees
  employees: () => '/employees/',

  // Payslips
  payslips: () => '/payslips/',
  payslipRequests: () => '/payslip-requests/',

  // Portal Config
  modules: () => '/modules/',
  formFields: () => '/form-fields/',
  workflowStages: () => '/workflow-stages/',

  // Notifications
  auditLogs: () => '/audit-logs/',
  notificationEmailLogs: () => '/notification-email-logs/',

  // Dashboard
  dashboardStats: () => '/dashboard/stats/',

  // Public
  publicModules: () => '/public/modules/',
  publicModuleFields: (key: string) => `/public/modules/${key}/fields/`,
  publicModuleWorkflow: (key: string) => `/public/modules/${key}/workflow/`,
}