import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/hooks'
import { Layout } from './components/layout/Layout'
import { PublicLayout } from './components/layout/PublicLayout'
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
import { ContractsList } from './pages/contracts/ContractsList'
import { EmployeesList } from './pages/employees/EmployeesList'
import { PayslipList } from './pages/payslip/PayslipList'
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

        {/* HR */}
        <Route path="/contracts" element={<ContractsList />} />
        <Route path="/employees" element={<EmployeesList />} />
        <Route path="/payslips" element={<PayslipList />} />

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

      {/* Catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
