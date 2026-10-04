import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'

// Mirrors settings.EXTERNAL_FORMS (static config in the Django backend)
const externalForms = [
  {
    key: 'bu_email',
    title: 'BRAC University Email',
    description: 'Request a BRAC University email address for staff and students.',
    url: 'https://docs.google.com/forms/d/e/1FAIpQLSfoS2BCEoAnFxu6DnT00DaAikaCWwuqstZHr7LmIV2Kwqb-nw/viewform',
    icon: 'bi-envelope-paper',
    bg: '#EDE9FE',
    fg: '#6D28D9',
    cta: 'Open form',
  },
  {
    key: 'ict_form',
    title: 'ICT Requisition',
    description: 'Request IT equipment, software licences and accessories.',
    url: 'https://docs.google.com/forms/d/e/1FAIpQLScNgf61ZQ-cV3q4CXbsbZuQN0Q_HFI9Y3jCPNaElVJi7KpV5Q/viewform',
    icon: 'bi-pc-display',
    bg: '#EFF6FF',
    fg: '#2563EB',
    cta: 'Open form',
  },
  {
    key: 'mail_service',
    title: 'Mail Service',
    description:
      'BRAC University email with an additional 50 GB of cloud storage — for @bracu.ac.bd addresses only.',
    url: 'https://signup.microsoft.com/signup?skug=Education&StepsData.Email=sdfsd%40bracu.ac.bd&sku=314c4481-f395-4525-be8b-2ec4bb1e9d91',
    icon: 'bi-envelope-at',
    bg: '#FEF2F2',
    fg: '#DC2626',
    cta: 'Sign up',
  },
]

// Exact replica of templates/public_home.html
export function Home() {
  const { data: modules } = useQuery({
    queryKey: ['publicModules'],
    queryFn: async () => {
      const response = await api.get<{ key: string }[]>('/public/modules/')
      return response.data
    },
    staleTime: 5 * 60 * 1000,
  })

  const visible = (modules || []).map((m) => m.key)
  const showTransport = visible.includes('transport')
  const showMeetspace = visible.includes('meetspace')

  return (
    <>
      <div className="hero">
        <div className="hero-icon">
          <img
            src="http://bracied.com/wp-content/uploads/2025/10/BRAC-IED-Color_PNG.png"
            alt="BRAC IED"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        </div>
        <h1>BRAC IED Central Portal</h1>

        <div className="hero-cta">
          <Link to="/login" className="cta-btn cta-ghost">
            <i className="bi bi-box-arrow-in-right"></i> Staff Sign In
          </Link>
        </div>
      </div>

      <div className="home-wrap">
        <div className="quick-grid">
          {showTransport && (
            <Link to="/transport/create" className="quick-card">
              <div className="quick-icon" style={{ background: '#FEF3C7', color: '#D97706' }}>
                <i className="bi bi-truck"></i>
              </div>
              <h3>Transport Request</h3>
              <p>
                Book official transport. No login needed &mdash; just fill in the trip details.
              </p>
              <span className="quick-link">
                Start request <i className="bi bi-arrow-right"></i>
              </span>
            </Link>
          )}

          {showMeetspace && (
            <Link to="/meetspace/create" className="quick-card">
              <div className="quick-icon" style={{ background: '#E0E7FF', color: '#4338CA' }}>
                <i className="bi bi-door-open"></i>
              </div>
              <h3>Meeting Room Booking</h3>
              <p>Book a meeting room for your team. Check availability and request a slot.</p>
              <span className="quick-link">
                Book a room <i className="bi bi-arrow-right"></i>
              </span>
            </Link>
          )}

          {externalForms.map((form) => (
            <a
              key={form.key}
              href={form.url}
              className="quick-card"
              target="_blank"
              rel="noopener noreferrer"
            >
              <div className="quick-icon" style={{ background: form.bg, color: form.fg }}>
                <i className={`bi ${form.icon}`}></i>
              </div>
              <h3>{form.title}</h3>
              <p>{form.description}</p>
              <span className="quick-link">
                {form.cta} <i className="bi bi-box-arrow-up-right"></i>
              </span>
            </a>
          ))}

          {showTransport && (
            <Link to="/login" className="quick-card">
              <div className="quick-icon" style={{ background: '#DBEAFE', color: '#2563EB' }}>
                <i className="bi bi-search"></i>
              </div>
              <h3>Track Transport Request</h3>
              <p>Check your approval status using the email address you submitted with.</p>
              <span className="quick-link">
                Track now <i className="bi bi-arrow-right"></i>
              </span>
            </Link>
          )}

          {showMeetspace && (
            <Link to="/login" className="quick-card">
              <div className="quick-icon" style={{ background: '#DBEAFE', color: '#2563EB' }}>
                <i className="bi bi-search"></i>
              </div>
              <h3>Track Meeting Room Booking</h3>
              <p>Check your meeting room booking status using your email address.</p>
              <span className="quick-link">
                Track now <i className="bi bi-arrow-right"></i>
              </span>
            </Link>
          )}

          <Link to="/login" className="quick-card">
            <div className="quick-icon" style={{ background: '#F1F5F9', color: '#475569' }}>
              <i className="bi bi-person-badge"></i>
            </div>
            <h3>Staff Sign In</h3>
            <p>Approve requests, manage drivers and access reporting tools.</p>
            <span className="quick-link">
              Sign in <i className="bi bi-arrow-right"></i>
            </span>
          </Link>
        </div>
      </div>

      <div className="home-footer">
        &copy; {new Date().getFullYear()} BRAC Institute of Educational Development. All rights
        reserved.
      </div>
    </>
  )
}
