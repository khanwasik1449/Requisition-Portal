import { Link } from 'react-router-dom'

interface PublicLayoutProps {
  children: React.ReactNode
  /** Replaces base_public.html's `{% block public_actions %}`. */
  actions?: React.ReactNode
}

/**
 * Exact replica of templates/base_public.html — the shell every signed-out
 * page uses: white sticky top bar, a single `.pub-card`, and the institute
 * footer. The Django file carries its CSS inline; here it lives in index.css.
 */
export function PublicLayout({ children, actions }: PublicLayoutProps) {
  return (
    <>
      <div className="pub-topbar">
        <Link className="pub-brand" to="/home">
          <div className="pub-brand-icon">
            <img
              src="http://bracied.com/wp-content/uploads/2025/10/BRAC-IED-Color_PNG.png"
              alt="BRAC IED"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
          <div>
            <h1>BRAC IED</h1>
          </div>
        </Link>

        <div className="pub-actions">
          {/* base_public.html's default public_actions block */}
          {actions ?? (
            <>
              <Link to="/transport/create" className="pub-btn pub-btn-primary">
                <i className="bi bi-truck"></i> Transport Request
              </Link>
              <Link to="/transport/track" className="pub-btn pub-btn-ghost">
                <i className="bi bi-search"></i> Track
              </Link>
            </>
          )}
          <Link to="/login" className="pub-btn pub-btn-ghost">
            <i className="bi bi-box-arrow-in-right"></i> Staff Sign In
          </Link>
        </div>
      </div>

      <div className="pub-wrap">
        <div className="pub-card">{children}</div>
      </div>

      <div className="pub-footer">
        &copy; {new Date().getFullYear()} BRAC Institute of Educational Development. All rights
        reserved.
      </div>
    </>
  )
}
