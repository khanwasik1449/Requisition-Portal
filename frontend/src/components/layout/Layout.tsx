import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/hooks'

// Exact replica of Django templates/base.html layout

interface NavItem {
  section?: string
  name?: string
  href?: string
  icon?: string
  sub?: boolean
  roles?: string[]
}

const navigation: NavItem[] = [
  { section: 'Main Menu' },
  { name: 'Dashboard', href: '/dashboard', icon: '📊' },
  { name: 'My Requisitions', href: '/my-requisitions', icon: '📋' },

  { section: 'Requisitions' },
  { name: 'ICT Requisition', href: '/ict', icon: '💻', roles: ['admin', 'ict_admin', 'ict_approver', 'requester'] },
  { name: 'Transport Requisition', href: '/transport', icon: '🚗', roles: ['admin', 'transport_admin', 'supervisor', 'grants', 'requester'] },
  { name: 'Tracking History', href: '/transport/history', icon: '🕓', sub: true, roles: ['admin', 'transport_admin'] },
  { name: 'Report', href: '/transport/report', icon: '📄', sub: true, roles: ['admin', 'transport_admin'] },
  { name: 'Internal Requisition', href: '/internal', icon: '📋', roles: ['admin', 'internal_admin', 'requester'] },
  { name: 'MeetSpace', href: '/meetspace', icon: '🚪', roles: ['admin', 'hr_admin', 'requester'] },

  { section: 'Human Resources', roles: ['admin', 'hr_admin'] },
  { name: 'Contracts', href: '/contracts', icon: '📄', roles: ['admin', 'hr_admin'] },
  { name: 'Employees', href: '/employees', icon: '👤', roles: ['admin', 'hr_admin'] },
  { name: 'Payslips', href: '/payslips', icon: '💵', roles: ['admin', 'hr_admin'] },

  { section: 'Administration' },
  { name: 'Form Builder & Workflows', href: '/admin/form-builder', icon: '🧩', roles: ['admin', 'transport_admin'] },
  { name: 'User Management', href: '/admin/users', icon: '👥', roles: ['admin'] },
  { name: 'Email Settings', href: '/admin/email-settings', icon: '⚙️', roles: ['admin'] },
  { name: 'Email Logs', href: '/admin/email-logs', icon: '📧', roles: ['admin'] },
  { name: 'Audit Log', href: '/admin/audit-log', icon: '📜', roles: ['admin'] },
]

export function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  const isActive = (href: string) => {
    if (href === '/dashboard') return location.pathname === '/dashboard'
    return location.pathname.startsWith(href)
  }

  const filteredNav = navigation.filter((item) => {
    if (item.section) {
      if (item.roles) {
        return item.roles.includes(user?.role || '')
      }
      return true
    }
    if (item.roles) {
      return item.roles.includes(user?.role || '')
    }
    return true
  })

  const handleLogout = async () => {
    await logout()
  }

  // Dynamic page title/subtitle based on current route (matches Django block page_title/page_subtitle)
  const path = location.pathname
  let pageTitle = 'Dashboard'
  let pageSubtitle = 'Enterprise Resource Management'

  if (path === '/dashboard') {
    pageTitle = user?.role === 'admin' ? 'Admin Dashboard' : 'Dashboard'
    pageSubtitle = 'Enterprise Resource Management'
  } else if (path === '/my-requisitions') {
    pageTitle = 'My Requisitions'
    pageSubtitle = 'All your submissions in one place'
  } else if (path.startsWith('/transport')) {
    pageTitle = 'Transport Requisitions'
    pageSubtitle = 'Vehicle transport and trip requests'
  } else if (path.startsWith('/ict')) {
    pageTitle = 'ICT Requisitions'
    pageSubtitle = 'IT equipment and software requests'
  } else if (path.startsWith('/internal')) {
    pageTitle = 'Internal Requisitions'
    pageSubtitle = 'Office supplies and resource requests'
  } else if (path.startsWith('/meetspace')) {
    pageTitle = 'MeetSpace'
    pageSubtitle = 'Meeting room bookings'
  } else if (path.startsWith('/contracts')) {
    pageTitle = 'Contracts'
    pageSubtitle = 'Contract management'
  } else if (path.startsWith('/employees')) {
    pageTitle = 'Employees'
    pageSubtitle = 'Employee management'
  } else if (path.startsWith('/payslips')) {
    pageTitle = 'Payslips'
    pageSubtitle = 'Payslip management'
  } else if (path.startsWith('/admin/users')) {
    pageTitle = 'User Management'
    pageSubtitle = 'Manage users and roles'
  } else if (path.startsWith('/documentation')) {
    pageTitle = 'Documentation'
    pageSubtitle = 'Guides and references'
  } else if (path.startsWith('/profile')) {
    pageTitle = 'My Profile'
    pageSubtitle = 'Account settings'
  }

  return (
    <>
      {/* SIDEBAR */}
      <div className={`sidebar ${sidebarOpen ? 'show' : ''}`} id="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <img
              src="http://bracied.com/wp-content/uploads/2025/10/BRAC-IED-Color_PNG.png"
              alt="BRAC IED"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
          <div>
            <h4>BRAC IED</h4>
          </div>
        </div>

        {filteredNav.map((item, idx) => {
          if (item.section) {
            return (
              <div key={`section-${idx}`} className="menu-title">
                {item.section}
              </div>
            )
          }

          return (
            <NavLink
              key={item.name}
              to={item.href || '/'}
              className={`nav-link ${item.sub ? 'sub-link' : ''} ${isActive(item.href || '') ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span> {item.name}
            </NavLink>
          )
        })}

        <div className="sidebar-footer">
          <small>
            Logged in as
            <br />
            <strong style={{ color: '#fff' }}>{user?.username}</strong>
          </small>
          <button type="button" className="logout-btn" onClick={handleLogout}>
            <span>🚪</span> Logout
          </button>
        </div>
      </div>

      {/* OVERLAY */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'show' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* MAIN */}
      <div className="main-wrapper">
        {/* TOPBAR */}
        <div className="topbar">
          <div className="topbar-left">
            <button className="topbar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
              <i className="bi bi-list"></i>
            </button>
            <div>
              <h5>{pageTitle}</h5>
              <p>{pageSubtitle}</p>
            </div>
          </div>
          <div className="topbar-right">
            <div className="topbar-user">
              <div className="topbar-user-info">
                <div className="name">{user?.username}</div>
                <div className="role">{user?.role_display || 'User'}</div>
              </div>
              <div className="topbar-avatar">{user?.username?.[0]?.toUpperCase()}</div>
            </div>
          </div>
        </div>

        {/* PAGE CONTENT */}
        <div className="content-card">
          <Outlet />
        </div>

        <footer>
          &copy; {new Date().getFullYear()} BRAC Institute of Educational Development. All rights reserved.
        </footer>
      </div>
    </>
  )
}
