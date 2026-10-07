import { useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/hooks'
import { takeFlash, type Flash } from '@/lib/flash'

// Exact replica of contracts/templates/contracts/base.html — the shell the
// whole HR module (contracts, employees, payslips) renders inside. main swaps
// the portal sidebar for this "HR System / Contract Management" one the moment
// you cross into /hr/..., and never links back out of it: the sidebar ends at
// Logout, exactly as the template does.

interface HrNavItem {
  icon: string
  name: string
  to: string
  /** The template's `{% if ... in request.path %}` active test, verbatim. */
  active: (path: string) => boolean
}

const hrNav: HrNavItem[] = [
  {
    icon: '➕',
    name: 'Create Contract',
    to: '/hr/contracts/create',
    active: (p) => p.includes('create') && p.includes('contracts'),
  },
  {
    icon: '📦',
    name: 'Bulk Contracts',
    to: '/hr/contracts/bulk-create',
    active: (p) => p.includes('bulk') && p.includes('contracts'),
  },
  {
    icon: '📄',
    name: 'Contracts List',
    to: '/hr/contracts/list',
    active: (p) => p.includes('list') && p.includes('contracts'),
  },
  {
    icon: '📧',
    name: 'Email Log',
    to: '/hr/contracts/email-log',
    active: (p) => p.includes('email-log'),
  },
  {
    icon: '⚙️',
    name: 'Email Settings',
    to: '/hr/contracts/email-settings',
    active: (p) => p.includes('email-settings'),
  },
  {
    icon: '💰',
    name: 'Create Payslip',
    to: '/hr/payslip',
    active: (p) => p.includes('payslip') && !p.includes('list'),
  },
  {
    icon: '📊',
    name: 'Payslip List',
    to: '/hr/payslip/list',
    active: (p) => p.includes('payslip/list'),
  },
  {
    icon: '📩',
    name: 'Payslip Requests',
    to: '/hr/payslip/requests',
    active: (p) => p.includes('payslip/requests'),
  },
  {
    icon: '👥',
    name: 'Employees',
    to: '/hr/employees',
    active: (p) => p.includes('employees'),
  },
  {
    icon: '📖',
    name: 'Manual',
    to: '/hr/contracts/manual',
    active: (p) => p.includes('manual'),
  },
]

export function HrLayout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [message, setMessage] = useState<Flash | null>(null)

  // contracts/base.html drains Django's message queue on every render; here
  // the queue is drained whenever a HR page hands one over.
  useEffect(() => {
    const flash = takeFlash()
    if (flash) setMessage(flash)
    setSidebarOpen(false)
  }, [location.pathname])

  const path = location.pathname

  return (
    <>
      <button className="hr-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
        ☰
      </button>

      <div
        className={`hr-overlay ${sidebarOpen ? 'show' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* SIDEBAR */}
      <div className={`hr-sidebar ${sidebarOpen ? 'show' : ''}`} id="hr-sidebar">
        <div className="hr-brand">
          <div className="hr-brand-icon">
            <img
              src="http://bracied.com/wp-content/uploads/2025/06/BRAC-IED-Color_PNG.png"
              alt="BRAC IED Logo"
            />
          </div>
          <div>
            <h4>HR System</h4>
            <small>Contract Management</small>
          </div>
        </div>

        <div className="hr-menu-title">Main Menu</div>

        {hrNav.map((item) => (
          <Link
            key={item.name}
            to={item.to}
            className={item.active(path) ? 'active' : ''}
          >
            <span>{item.icon}</span>
            {item.name}
          </Link>
        ))}

        <div className="hr-userbox">
          <small>
            Logged in as
            <br />
            <strong style={{ color: '#fff' }}>{user?.username}</strong>
          </small>
          <button type="button" className="hr-logout" onClick={() => logout()}>
            Logout
          </button>
        </div>
      </div>

      {/* MAIN */}
      <div className="hr-main">
        {/* messages */}
        {message && (
          <div className={`app-message ${message.level}`}>
            <span className="msg-close" onClick={() => setMessage(null)}>
              &times;
            </span>
            {message.text}
          </div>
        )}

        {/* TOPBAR */}
        <div className="hr-topbar">
          <div>
            <h5>Dashboard</h5>
            <p>HR Contract Management System</p>
          </div>
          <div className="hr-topbar-user">{user?.username}</div>
        </div>

        {/* PAGE CONTENT */}
        <div className="hr-card">
          <Outlet />
        </div>

        <div className="hr-foot">
          &copy; {new Date().getFullYear()} BRAC Institute of Educational
          Development. All rights reserved.
        </div>
      </div>
    </>
  )
}
