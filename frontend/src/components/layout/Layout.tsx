import { useState, useEffect, useRef } from 'react'
import { Outlet, NavLink, Link, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/hooks'
import { useVisibleHomeCards, type HomeCard } from '@/lib/homeCards'

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
  // main points these at contracts:dashboard / employees:employee_list /
  // payslip:create_payslip, i.e. the /hr/... routes.
  { name: 'Contracts', href: '/hr/contracts', icon: '📄', roles: ['admin', 'hr_admin'] },
  { name: 'Employees', href: '/hr/employees', icon: '👤', roles: ['admin', 'hr_admin'] },
  { name: 'Payslips', href: '/hr/payslip', icon: '💵', roles: ['admin', 'hr_admin'] },

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
  const [reqOpen, setReqOpen] = useState(false)
  const reqRef = useRef<HTMLDivElement>(null)

  // The landing-page cards, gated on VISIBLE_MODULES exactly as the Django
  // template gates them — this is the "Requisitions" menu contents.
  const { cards: requisitionCards, loading: cardsLoading } = useVisibleHomeCards()

  // Close sidebar and the Requisitions menu on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false)
    setReqOpen(false)
  }, [location.pathname])

  // Close the Requisitions menu when clicking anywhere outside it
  useEffect(() => {
    if (!reqOpen) return
    const onPointerDown = (event: MouseEvent) => {
      if (reqRef.current && !reqRef.current.contains(event.target as Node)) setReqOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [reqOpen])

  const requisitionItem = (card: HomeCard) => {
    const label = (
      <>
        <i className={`bi ${card.icon} me-2`}></i>
        {card.title}
      </>
    )

    if (card.href) {
      return (
        <a
          className="dropdown-item d-flex align-items-center justify-content-between"
          href={card.href}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => setReqOpen(false)}
        >
          <span>{label}</span>
          <i className="bi bi-box-arrow-up-right ms-3 small opacity-50"></i>
        </a>
      )
    }

    return (
      <Link className="dropdown-item d-flex align-items-center" to={card.to || '/'} onClick={() => setReqOpen(false)}>
        {label}
      </Link>
    )
  }

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
  } else if (path === '/transport/history') {
    pageTitle = 'Tracking History'
    pageSubtitle = 'Enterprise Resource Management'
  } else if (path === '/transport/report') {
    pageTitle = 'Transport Requisition Report'
    pageSubtitle = 'Enterprise Resource Management'
  } else if (path.startsWith('/transport')) {
    pageTitle = 'Transport Requisitions'
  } else if (path.startsWith('/ict')) {
    pageTitle = 'ICT Requisitions'
  } else if (path.startsWith('/internal')) {
    pageTitle = 'Internal Requisitions'
  } else if (path === '/meetspace') {
    pageTitle = 'MeetSpace'
  } else if (path === '/meetspace/bookings') {
    pageTitle = 'Bookings — MeetSpace'
  } else if (path === '/meetspace/availability') {
    pageTitle = 'Find a Room — MeetSpace'
  } else if (path === '/meetspace/rooms/new') {
    pageTitle = 'Add Room — MeetSpace'
  } else if (/^\/meetspace\/rooms\/\d+\/edit$/.test(path)) {
    pageTitle = `Edit Room — MeetSpace`
  } else if (path === '/meetspace/rooms') {
    pageTitle = 'Rooms — MeetSpace'
  } else if (path === '/meetspace/announcements/new') {
    pageTitle = 'Post Announcement — MeetSpace'
  } else if (/^\/meetspace\/bookings\/\d+$/.test(path)) {
    // booking_detail.html: "Booking #12 — MeetSpace"
    pageTitle = `Booking #${path.split('/').pop()} — MeetSpace`
  } else if (path.startsWith('/admin/users')) {
    pageTitle = 'User Management'
  } else if (path.startsWith('/admin/email-settings')) {
    pageTitle = 'Email Configurations'
    pageSubtitle = 'Enterprise Resource Management'
  } else if (path.startsWith('/admin/email-logs')) {
    pageTitle = 'Email Logs'
    pageSubtitle = 'Enterprise Resource Management'
  } else if (path.startsWith('/admin/audit-log')) {
    pageTitle = 'Audit Log'
    pageSubtitle = 'Track all requisition activity'
  } else if (path.startsWith('/admin/form-builder')) {
    pageTitle = 'Portal Configuration'
    pageSubtitle = 'Enterprise Resource Management'
  } else if (path.startsWith('/admin/workflow-editor')) {
    pageTitle = 'Approval Workflow'
    pageSubtitle = 'Enterprise Resource Management'
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
            {/* Requisitions launcher — the landing-page cards, minus Staff Sign In */}
            <div className="dropdown topbar-requisitions" ref={reqRef}>
              <button
                type="button"
                className={`btn btn-primary dropdown-toggle ${reqOpen ? 'show' : ''}`}
                onClick={() => setReqOpen((open) => !open)}
                aria-haspopup="menu"
                aria-expanded={reqOpen}
              >
                <i className="bi bi-plus-circle me-1"></i> Requisitions
              </button>
              <ul
                className={`dropdown-menu dropdown-menu-end ${reqOpen ? 'show' : ''}`}
                role="menu"
              >
                {cardsLoading ? (
                  <li>
                    <span className="dropdown-item-text small text-muted">Loading…</span>
                  </li>
                ) : (
                  requisitionCards.map((card) => <li key={card.key}>{requisitionItem(card)}</li>)
                )}
              </ul>
            </div>

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
