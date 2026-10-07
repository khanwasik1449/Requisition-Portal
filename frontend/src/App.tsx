import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/hooks'
import { Layout } from './components/layout/Layout'
import { PublicLayout } from './components/layout/PublicLayout'
import { HrLayout } from './components/layout/HrLayout'
import { Login } from './pages/Login'
import { Home } from './pages/Home'
import { Dashboard } from './pages/Dashboard'
import { MyRequisitions } from './pages/MyRequisitions'
import { TransportList } from './pages/transport/TransportList'
import { TransportCreate } from './pages/transport/TransportCreate'
import { TransportDetail } from './pages/transport/TransportDetail'
import { TransportTrack } from './pages/transport/TransportTrack'
import { MeetSpaceDashboard } from './pages/meetspace/MeetSpaceDashboard'
import { MeetSpaceList } from './pages/meetspace/MeetSpaceList'
import { MeetSpaceBooking } from './pages/meetspace/MeetSpaceBooking'
import { MeetSpaceDetail } from './pages/meetspace/MeetSpaceDetail'
import { MeetSpaceTrack } from './pages/meetspace/MeetSpaceTrack'
import { RoomList } from './pages/meetspace/RoomList'
import { RoomForm } from './pages/meetspace/RoomForm'
import { RoomAvailability } from './pages/meetspace/RoomAvailability'
import { AnnouncementForm } from './pages/meetspace/AnnouncementForm'
import { ICTList } from './pages/ict/ICTList'
import { ICTCreate } from './pages/ict/ICTCreate'
import { ICTDetail } from './pages/ict/ICTDetail'
import { InternalList } from './pages/internal/InternalList'
import { InternalCreate } from './pages/internal/InternalCreate'
import { InternalDetail } from './pages/internal/InternalDetail'
import { TransportHistory } from './pages/transport/TransportHistory'
import { TransportReport } from './pages/transport/TransportReport'
import { ContractForm } from './pages/contracts/ContractForm'
import { ContractsList } from './pages/contracts/ContractsList'
import { ContractBulkUpload } from './pages/contracts/ContractBulkUpload'
import { ContractEmail } from './pages/contracts/ContractEmail'
import { ContractBulkEmail } from './pages/contracts/ContractBulkEmail'
import { ContractBulkEmailStatus } from './pages/contracts/ContractBulkEmailStatus'
import { ContractManual } from './pages/contracts/ContractManual'
import { HrEmailLog } from './pages/contracts/HrEmailLog'
import { HrEmailSettings } from './pages/contracts/HrEmailSettings'
import { EmployeesList } from './pages/employees/EmployeesList'
import { EmployeeForm } from './pages/employees/EmployeeForm'
import { EmployeeDelete } from './pages/employees/EmployeeDelete'
import { EmployeeImport } from './pages/employees/EmployeeImport'
import { EmployeeDetail } from './pages/employees/EmployeeDetail'
import { PayslipForm } from './pages/payslip/PayslipForm'
import { PayslipList } from './pages/payslip/PayslipList'
import { PayslipBulkUpload } from './pages/payslip/PayslipBulkUpload'
import { PayslipRequestForm } from './pages/payslip/PayslipRequestForm'
import { PayslipRequestsList } from './pages/payslip/PayslipRequestsList'
import { Documentation } from './pages/Documentation'
import { Signup } from './pages/Signup'
import { EmailAction } from './pages/notifications/EmailAction'
import { Track } from './pages/notifications/Track'
import { AdminUsers } from './pages/admin/AdminUsers'
import { AdminUserForm } from './pages/admin/AdminUserForm'
import { FormBuilder } from './pages/admin/FormBuilder'
import { FormFieldList } from './pages/admin/FormFieldList'
import { FormFieldEdit } from './pages/admin/FormFieldEdit'
import { WorkflowEditor } from './pages/admin/WorkflowEditor'
import { EmailSettings } from './pages/admin/EmailSettings'
import { EmailLogs } from './pages/admin/EmailLogs'
import { AuditLog } from './pages/admin/AuditLog'
import { Profile } from './pages/Profile'
import { NotFound } from './pages/NotFound'

function LoadingScreen() {
  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh' }}>
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  )
}

function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: string[] }) {
  const { user, isAuthenticated, loading } = useAuth()

  if (loading) return <LoadingScreen />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return <LoadingScreen />
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      {/* The landing URL is the sign-in screen; the public landing page is
          still reachable at /home for reference. */}
      <Route path="/" element={<Login />} />
      <Route path="/home" element={<Home />} />
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      {/* Public pages — all four extend base_public.html in main, so they get
          the white top-bar shell rather than the signed-in sidebar layout. */}
      <Route
        path="/transport/create"
        element={
          <PublicLayout>
            <TransportCreate />
          </PublicLayout>
        }
      />
      <Route
        path="/transport/track"
        element={
          <PublicLayout>
            <TransportTrack />
          </PublicLayout>
        }
      />
      <Route
        path="/meetspace/bookings/new"
        element={
          <PublicLayout>
            <MeetSpaceBooking />
          </PublicLayout>
        }
      />
      <Route
        path="/meetspace/track"
        element={
          <PublicLayout>
            <MeetSpaceTrack />
          </PublicLayout>
        }
      />

      {/* Protected routes with layout */}
      <Route element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/my-requisitions" element={<MyRequisitions />} />
        <Route path="/profile" element={<Profile />} />

        {/* Transport — `history` and `report` are static segments and must be
            declared before `/transport/:id`, otherwise they are read as a pk. */}
        <Route path="/transport" element={<TransportList />} />
        <Route path="/transport/history" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <TransportHistory />
          </ProtectedRoute>
        } />
        <Route path="/transport/report" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <TransportReport />
          </ProtectedRoute>
        } />
        <Route path="/transport/:id" element={<TransportDetail />} />

        {/* MeetSpace — main's `meetspace:dashboard` is mounted at `''`, so
            `/meetspace` is the dashboard; bookings live under `bookings/`
            exactly as meetspace/urls.py lays them out. Static segments are
            declared before `bookings/:id`. */}
        <Route path="/meetspace" element={<MeetSpaceDashboard />} />
        <Route path="/meetspace/bookings" element={<MeetSpaceList />} />
        <Route path="/meetspace/bookings/:id" element={<MeetSpaceDetail />} />
        <Route path="/meetspace/availability" element={<RoomAvailability />} />
        <Route path="/meetspace/rooms" element={<RoomList />} />
        <Route path="/meetspace/rooms/new" element={<RoomForm />} />
        <Route path="/meetspace/rooms/:roomId/edit" element={<RoomForm />} />
        <Route path="/meetspace/announcements/new" element={<AnnouncementForm />} />

        {/* ICT */}
        <Route path="/ict" element={<ICTList />} />
        <Route path="/ict/create" element={<ICTCreate />} />
        <Route path="/ict/:id" element={<ICTDetail />} />

        {/* Internal */}
        <Route path="/internal" element={<InternalList />} />
        <Route path="/internal/create" element={<InternalCreate />} />
        <Route path="/internal/:id" element={<InternalDetail />} />

        {/* HR pages moved to their own shell — see below. */}

        {/* Admin */}
        <Route path="/admin/users" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminUsers />
          </ProtectedRoute>
        } />
        <Route path="/admin/users/create" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminUserForm />
          </ProtectedRoute>
        } />
        <Route path="/admin/users/:userId/edit" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminUserForm />
          </ProtectedRoute>
        } />
        <Route path="/admin/form-builder" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <FormBuilder />
          </ProtectedRoute>
        } />
        <Route path="/admin/form-builder/fields" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <FormFieldList />
          </ProtectedRoute>
        } />
        <Route path="/admin/form-builder/fields/new" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <FormFieldEdit />
          </ProtectedRoute>
        } />
        <Route path="/admin/form-builder/fields/:fieldId/edit" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <FormFieldEdit />
          </ProtectedRoute>
        } />
        <Route path="/admin/workflow-editor" element={
          <ProtectedRoute allowedRoles={['admin', 'transport_admin']}>
            <WorkflowEditor />
          </ProtectedRoute>
        } />
        <Route path="/admin/email-settings" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <EmailSettings />
          </ProtectedRoute>
        } />
        <Route path="/admin/email-logs" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <EmailLogs />
          </ProtectedRoute>
        } />
        <Route path="/admin/audit-log" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AuditLog />
          </ProtectedRoute>
        } />
      </Route>

      {/* HR module — contracts, employees and payslips all render inside
          contracts/base.html's own shell in main, not the portal sidebar, so
          they get a pathless layout route that mounts HrLayout for each
          /hr/... path. Declared as separate children (rather than nested
          under a `path="/hr"`) so the public payslip-request page below can
          claim its own path without competing with this subtree. */}
      <Route
        element={
          <ProtectedRoute>
            <HrLayout />
          </ProtectedRoute>
        }
      >
        {/* contracts/urls.py */}
        <Route path="/hr/contracts" element={<ContractsList />} />
        <Route path="/hr/contracts/list" element={<ContractsList />} />
        <Route path="/hr/contracts/create" element={<ContractForm />} />
        <Route path="/hr/contracts/bulk-create" element={<ContractBulkUpload />} />
        <Route path="/hr/contracts/email/:id" element={<ContractEmail />} />
        <Route path="/hr/contracts/bulk-email" element={<ContractBulkEmail />} />
        <Route path="/hr/contracts/bulk-email-status" element={<ContractBulkEmailStatus />} />
        <Route path="/hr/contracts/manual" element={<ContractManual />} />
        <Route path="/hr/contracts/email-log" element={<HrEmailLog />} />
        <Route path="/hr/contracts/email-settings" element={<HrEmailSettings />} />

        {/* employees/urls.py */}
        <Route path="/hr/employees" element={<EmployeesList />} />
        <Route path="/hr/employees/add" element={<EmployeeForm />} />
        <Route path="/hr/employees/edit/:pin" element={<EmployeeForm />} />
        <Route path="/hr/employees/delete/:pin" element={<EmployeeDelete />} />
        <Route path="/hr/employees/import" element={<EmployeeImport />} />
        <Route path="/hr/employees/detail/:pin" element={<EmployeeDetail />} />

        {/* payslip/urls.py */}
        <Route path="/hr/payslip" element={<PayslipForm />} />
        <Route path="/hr/payslip/list" element={<PayslipList />} />
        <Route path="/hr/payslip/bulk" element={<PayslipBulkUpload />} />
        <Route path="/hr/payslip/requests" element={<PayslipRequestsList />} />
      </Route>

      {/* payslip/views.request_payslip has no @login_required — it is a
          standalone public document (it extends nothing), so it renders
          outside both shells. */}
      <Route path="/hr/payslip/request" element={<PayslipRequestForm />} />

      {/* Tier 3 — the remaining standalone public pages. None of these
          templates extends base.html either: documentation.html, signup.html,
          pending_approval.html, notifications/action_*.html and
          notifications/track.html are all full documents of their own, so they
          render outside both shells. /notifications/action/:token is public
          because main redirects a signed-out visitor to login with ?next=. */}
      <Route path="/documentation" element={<Documentation />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/notifications/action/:token" element={<EmailAction />} />
      <Route path="/notifications/track/:reqType/:id" element={<Track />} />

      {/* Legacy Tier-1 HR paths, kept resolving to the main-equivalent URLs */}
      <Route path="/contracts" element={<Navigate to="/hr/contracts" replace />} />
      <Route path="/employees" element={<Navigate to="/hr/employees" replace />} />
      <Route path="/payslips" element={<Navigate to="/hr/payslip/list" replace />} />

      {/* Catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
