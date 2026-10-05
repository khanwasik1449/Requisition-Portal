import { Link } from 'react-router-dom'
import { signInCard, useVisibleHomeCards, type HomeCard } from '@/lib/homeCards'

function QuickCard({ card }: { card: HomeCard }) {
  const inner = (
    <>
      <div className="quick-icon" style={{ background: card.bg, color: card.fg }}>
        <i className={`bi ${card.icon}`}></i>
      </div>
      <h3>{card.title}</h3>
      <p>{card.description}</p>
      <span className="quick-link">
        {card.linkText} <i className={`bi ${card.linkIcon}`}></i>
      </span>
    </>
  )

  if (card.href) {
    return (
      <a href={card.href} className="quick-card" target="_blank" rel="noopener noreferrer">
        {inner}
      </a>
    )
  }

  return (
    <Link to={card.to || '/'} className="quick-card">
      {inner}
    </Link>
  )
}

// Exact replica of templates/public_home.html
export function Home() {
  const { cards } = useVisibleHomeCards()

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
          {cards.map((card) => (
            <QuickCard key={card.key} card={card} />
          ))}
          <QuickCard card={signInCard} />
        </div>
      </div>

      <div className="home-footer">
        &copy; {new Date().getFullYear()} BRAC Institute of Educational Development. All rights
        reserved.
      </div>
    </>
  )
}
