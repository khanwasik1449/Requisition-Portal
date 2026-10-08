import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/axios'

// Source of truth: templates/public_home.html.
//
// The landing page renders `homeCards` in this order, each gated on the
// VISIBLE_MODULES flag for its `module`, then the Staff Sign In card. The
// dashboard's "Requisitions" menu renders exactly the same list minus
// Staff Sign In, so the two can never drift apart.

export interface HomeCard {
  key: string
  title: string
  description: string
  icon: string
  bg: string
  fg: string
  linkText: string
  linkIcon: string
  /** In-app route. Mutually exclusive with `href`. */
  to?: string
  /** Off-site URL, opened in a new tab. */
  href?: string
  /** Portal module that must be in VISIBLE_MODULES for this card to show. */
  module?: string
}

// Mirrors settings.EXTERNAL_FORMS (static config in the Django backend).
const externalForms: HomeCard[] = [
  {
    key: 'bu_email',
    title: 'BRAC University Email',
    description: 'Request a BRAC University email address for staff and students.',
    // In-app, like Transport Request: the request is e-mailed to the internal
    // team and the applicant's details are pre-filled. `main` links out to a
    // Google Form here instead.
    to: '/bu-email/request',
    icon: 'bi-envelope-paper',
    bg: '#EDE9FE',
    fg: '#6D28D9',
    linkText: 'Start request',
    linkIcon: 'bi-arrow-right',
  },
  {
    key: 'ict_form',
    title: 'ICT Requisition',
    description: 'Request IT equipment, software licences and accessories.',
    // In-app, like Transport Request: the portal has its own ICT form
    // (ict_requisition/form.html), and only that one can pre-fill the
    // applicant's details. `main` links out to a Google Form here instead.
    to: '/ict/create',
    icon: 'bi-pc-display',
    bg: '#EFF6FF',
    fg: '#2563EB',
    linkText: 'Start request',
    linkIcon: 'bi-arrow-right',
  },
  {
    key: 'mail_service',
    title: 'Mail Service',
    description:
      'BRAC University email with an additional 50 GB of cloud storage — for @bracu.ac.bd addresses only.',
    href: 'https://signup.microsoft.com/signup?skug=Education&StepsData.Email=sdfsd%40bracu.ac.bd&sku=314c4481-f395-4525-be8b-2ec4bb1e9d91',
    icon: 'bi-envelope-at',
    bg: '#FEF2F2',
    fg: '#DC2626',
    linkText: 'Sign up',
    linkIcon: 'bi-box-arrow-up-right',
  },
]

export const homeCards: HomeCard[] = [
  {
    key: 'transport',
    title: 'Transport Request',
    description: 'Book official transport. No login needed — just fill in the trip details.',
    to: '/transport/create',
    icon: 'bi-truck',
    bg: '#FEF3C7',
    fg: '#D97706',
    linkText: 'Start request',
    linkIcon: 'bi-arrow-right',
    module: 'transport',
  },
  {
    key: 'meetspace',
    title: 'Meeting Room Booking',
    description: 'Book a meeting room for your team. Check availability and request a slot.',
    to: '/meetspace/bookings/new',
    icon: 'bi-door-open',
    bg: '#E0E7FF',
    fg: '#4338CA',
    linkText: 'Book a room',
    linkIcon: 'bi-arrow-right',
    module: 'meetspace',
  },
  ...externalForms,
  {
    key: 'track_transport',
    title: 'Track Transport Request',
    description: 'Check your approval status using the email address you submitted with.',
    to: '/transport/track',
    icon: 'bi-search',
    bg: '#DBEAFE',
    fg: '#2563EB',
    linkText: 'Track now',
    linkIcon: 'bi-arrow-right',
    module: 'transport',
  },
  // public_home.html renders this card too, right after Track Transport; it was
  // never carried over, so enabling the meetspace module would have left the
  // landing page with one fewer card than main.
  {
    key: 'track_meetspace',
    title: 'Track Meeting Room Booking',
    description: 'Check your meeting room booking status using your email address.',
    to: '/meetspace/track',
    icon: 'bi-search',
    bg: '#DBEAFE',
    fg: '#2563EB',
    linkText: 'Track now',
    linkIcon: 'bi-arrow-right',
    module: 'meetspace',
  },
]

export const signInCard: HomeCard = {
  key: 'sign_in',
  title: 'Staff Sign In',
  description: 'Approve requests, manage drivers and access reporting tools.',
  to: '/login',
  icon: 'bi-person-badge',
  bg: '#F1F5F9',
  fg: '#475569',
  linkText: 'Sign in',
  linkIcon: 'bi-arrow-right',
}

export interface VisibleHomeCards {
  cards: HomeCard[]
  loading: boolean
}

/**
 * The landing-page cards the signed-in user is allowed to see, i.e. the same
 * VISIBLE_MODULES gate the Django template applies.
 */
export function useVisibleHomeCards(): VisibleHomeCards {
  const { data, isPending } = useQuery({
    queryKey: ['publicModules'],
    queryFn: async () => (await api.get<{ key: string }[]>('/public/modules/')).data,
    staleTime: 5 * 60 * 1000,
  })

  // Don't render a partial list while the visibility flags are in flight —
  // otherwise the menu flickers from 3 items to 5.
  if (isPending) return { cards: [], loading: true }

  const visible = (data ?? []).map((m) => m.key)
  return {
    cards: homeCards.filter((card) => !card.module || visible.includes(card.module)),
    loading: false,
  }
}
