import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash, type FlashLevel } from '@/lib/flash'
import { getAllResults } from '@/lib/paginate'

interface Contract {
  id: number
  pin: string
  name: string
  designation: string
  new_designation?: string | null
  salary: number | string
  contract_type: string
  start_date: string
  end_date: string
}

/** A contract row once the client-side status badge has been computed. */
type Row = Contract & { _status: string }

const PAGE_SIZE = 15

function computeStatus(endDate: string): string {
  if (!endDate) return 'Active'
  const end = new Date(endDate)
  const now = new Date()
  const diff = (end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  if (diff < 0) return 'Expired'
  if (diff <= 30) return 'Expiring'
  return 'Active'
}

function fmtDate(d: string) {
  if (!d) return '—'
  const [y, m, day] = d.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${day} ${months[parseInt(m, 10) - 1]} ${y}`
}

function fmtMoney(v: number | string) {
  if (!v && v !== 0) return '—'
  return '৳\u00A0' + Number(v).toLocaleString('en-BD')
}

function initials(name: string) {
  return (
    name
      .trim()
      .split(' ')
      .slice(0, 2)
      .map((w) => w[0] || '')
      .join('')
      .toUpperCase() || '?'
  )
}

function badgeClass(type: string) {
  const map: Record<string, string> = {
    New: 'badge-extension',
    Extension: 'badge-extension',
    Revision: 'badge-revision',
    Renewal: 'badge-renewal',
  }
  return map[type] || 'badge-extension'
}

function statusClass(status: string) {
  const map: Record<string, string> = {
    Active: 'badge-active',
    Expired: 'badge-expired',
    Expiring: 'badge-expiring',
  }
  return map[status]
}

/**
 * The PDF endpoint answers 501 (WeasyPrint's Pango/GObject libraries are not
 * installed on this host) with a JSON `detail`, but the request was made with
 * `responseType: 'blob'` -- so the body arrives as a Blob that the plain error
 * reader cannot see into. Decode it first, then hand the readable body to
 * `flashFromError`.
 */
async function pdfErrorText(err: unknown): Promise<string> {
  const data = (err as { response?: { data?: unknown } } | null)?.response?.data
  if (data instanceof Blob) {
    try {
      const parsed: unknown = JSON.parse(await data.text())
      return flashFromError({ response: { data: parsed } }).text
    } catch {
      // Not JSON after all -- fall through to the plain reader.
    }
  }
  return flashFromError(err).text
}

async function downloadContractPdf(contractId: number, pin: string) {
  const { data } = await api.get<Blob>(`/contracts/${contractId}/pdf/`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `contract_${pin}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// contracts/templates/contracts/list.html -- <style> blocks, verbatim.
const css = `
  :root {
    --c-bg:            #F7F6F3;
    --c-surface:       #FFFFFF;
    --c-border:        rgba(0,0,0,0.08);
    --c-border-strong: rgba(0,0,0,0.14);
    --c-text:          #1A1917;
    --c-muted:         #6B6A66;
    --c-hint:          #A8A79F;
    --c-accent:        #2563EB;
    --c-accent-bg:     #EFF4FF;
    --c-success:       #16A34A;
    --c-success-bg:    #F0FDF4;
    --c-danger:        #DC2626;
    --c-danger-bg:     #FEF2F2;
    --c-amber:         #D97706;
    --c-amber-bg:      #FFFBEB;
    --c-purple:        #7C3AED;
    --c-purple-bg:     #F5F3FF;
    --radius:          12px;
    --radius-sm:       8px;
    --shadow:          0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);
    --shadow-md:    0 4px 12px rgba(0,0,0,0.08),0 2px 4px rgba(0,0,0,0.04);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--c-bg);
    color: var(--c-text);
  }

  .dash-wrap { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }

  /* ── Page header ── */
  .dash-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 1.75rem;
    flex-wrap: wrap;
    gap: 12px;
  }
  .dash-header h1 {
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.02em;
  }
  .dash-header p { font-size: 13px; color: var(--c-muted); margin-top: 3px; }

  /* ── Stat cards ── */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 1.5rem;
  }
  .stat-card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    cursor: pointer;
    transition: border-color .2s, box-shadow .2s;
    user-select: none;
  }
  .stat-card:hover { border-color: var(--c-border-strong); box-shadow: var(--shadow); }
  .stat-card.active { border-color: var(--c-accent); box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
  .stat-label { font-size: 11px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--c-hint); margin-bottom: 6px; }
  .stat-value { font-size: 1.6rem; font-weight: 600; font-family: 'DM Mono', monospace; color: var(--c-text); }
  .stat-sub { font-size: 12px; color: var(--c-muted); margin-top: 2px; }

  /* ── Toolbar ── */
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }
  .search-wrap {
    position: relative;
    flex: 1;
    min-width: 220px;
  }
  .search-wrap svg {
    position: absolute;
    left: 11px;
    top: 50%;
    transform: translateY(-50%);
    width: 15px; height: 15px;
    color: var(--c-hint);
    pointer-events: none;
  }
  .search-wrap input {
    width: 100%;
    height: 38px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    padding: 0 12px 0 34px;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    color: var(--c-text);
    background: var(--c-surface);
    outline: none;
    transition: border-color .2s, box-shadow .2s;
  }
  .search-wrap input:focus {
    border-color: var(--c-accent);
    box-shadow: 0 0 0 3px rgba(37,99,235,.1);
  }
  .filter-select {
    height: 38px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    padding: 0 30px 0 12px;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    color: var(--c-text);
    background: var(--c-surface);
    outline: none;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23A8A79F' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
    transition: border-color .2s;
  }
  .filter-select:focus { border-color: var(--c-accent); }

  .sort-btn {
    height: 38px;
    padding: 0 14px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    background: var(--c-surface);
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    color: var(--c-muted);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: border-color .2s, color .2s;
    white-space: nowrap;
  }
  .sort-btn:hover { border-color: var(--c-border-strong); color: var(--c-text); }
  .sort-btn.active { border-color: var(--c-accent); color: var(--c-accent); background: var(--c-accent-bg); }

  .results-count {
    font-size: 12px;
    color: var(--c-hint);
    font-family: 'DM Mono', monospace;
    white-space: nowrap;
    margin-left: auto;
  }

  /* ── Table ── */
  .table-card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
  }
  .table-scroll { overflow-x: auto; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    table-layout: fixed;
  }
  thead tr {
    background: var(--c-bg);
    border-bottom: 1px solid var(--c-border-strong);
  }
  thead th {
    padding: 10px 14px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--c-hint);
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    transition: color .15s;
  }
  thead th:hover { color: var(--c-text); }
  thead th.sorted { color: var(--c-accent); }
  thead th .sort-arrow { margin-left: 4px; opacity: .5; }
  thead th.sorted .sort-arrow { opacity: 1; }

  tbody tr {
    border-bottom: 1px solid var(--c-border);
    transition: background .12s;
    cursor: pointer;
  }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: #FAFAF8; }
  tbody tr.highlighted { background: var(--c-accent-bg); }

  td {
    padding: 12px 14px;
    color: var(--c-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  td.pin-cell {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: var(--c-muted);
  }
  td.name-cell { font-weight: 500; }

  /* ── Badges ── */
  .badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    letter-spacing: .02em;
  }
  .badge-extension { background: var(--c-accent-bg);  color: #185FA5; }
  .badge-revision  { background: var(--c-amber-bg);   color: #854F0B; }
  .badge-renewal   { background: var(--c-success-bg); color: #3B6D11; }
  .badge-active    { background: var(--c-success-bg); color: #3B6D11; }
  .badge-expired   { background: var(--c-danger-bg);  color: #A32D2D; }
  .badge-expiring  { background: var(--c-amber-bg);   color: #854F0B; }

  /* ── Action buttons ── */
  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 11px;
    border-radius: var(--radius-sm);
    font-size: 12px;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    cursor: pointer;
    border: 1px solid transparent;
    text-decoration: none;
    transition: all .15s;
  }
  .btn-pdf {
    background: var(--c-success-bg);
    color: var(--c-success);
    border-color: rgba(22,163,74,.2);
  }
  .btn-pdf:hover {
    background: var(--c-success);
    color: #fff;
    border-color: var(--c-success);
  }
  .btn-email {
    background: #EFF6FF;
    color: #2563EB;
    border-color: rgba(37,99,235,.2);
  }
  .btn-email:hover {
    background: #2563EB;
    color: #fff;
    border-color: #2563EB;
  }
  .btn-delete {
    background: var(--c-danger-bg);
    color: var(--c-danger);
    border-color: rgba(220,38,38,.2);
  }
  .btn-delete:hover {
    background: var(--c-danger);
    color: #fff;
    border-color: var(--c-danger);
  }

  /* ── Delete confirm modal ── */
  .modal-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 200;
    align-items: center;
    justify-content: center;
  }
  .modal-backdrop.open { display: flex; }
  .modal-box {
    background: var(--c-surface);
    border-radius: var(--radius);
    border: 1px solid var(--c-border);
    width: 100%;
    max-width: 400px;
    margin: 1rem;
    animation: modalPop .2s cubic-bezier(.175,.885,.32,1.275);
  }
  @keyframes modalPop {
    from { transform: scale(.93); opacity: 0; }
    to   { transform: scale(1);   opacity: 1; }
  }
  .modal-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 1.25rem 1.5rem 1rem;
    border-bottom: 1px solid var(--c-border);
  }
  .modal-icon {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: var(--c-danger-bg);
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .modal-title { font-size: 15px; font-weight: 600; }
  .modal-body  { padding: 1rem 1.5rem 1.25rem; font-size: 13px; color: var(--c-muted); line-height: 1.6; }
  .modal-body strong { color: var(--c-text); font-weight: 600; }
  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: .75rem 1.5rem 1.25rem;
  }
  .modal-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 18px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all .15s;
  }
  .modal-btn-cancel {
    background: transparent;
    border-color: var(--c-border-strong);
    color: var(--c-muted);
  }
  .modal-btn-cancel:hover { background: var(--c-bg); color: var(--c-text); }
  .modal-btn-confirm {
    background: var(--c-danger);
    color: #fff;
    border-color: var(--c-danger);
  }
  .modal-btn-confirm:hover { background: #B91C1C; }
  .modal-btn-confirm:disabled { opacity: .6; cursor: not-allowed; }

  /* ── Empty state ── */
  .empty-state {
    padding: 3.5rem 1rem;
    text-align: center;
  }
  .empty-icon {
    width: 48px; height: 48px;
    border-radius: 50%;
    background: var(--c-bg);
    border: 1px solid var(--c-border);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 1rem;
  }
  .empty-state h3 { font-size: 15px; font-weight: 500; margin-bottom: 4px; }
  .empty-state p  { font-size: 13px; color: var(--c-muted); }

  /* ── Detail drawer (slide-in from right) ── */
  .drawer-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 100;
  }
  .drawer-overlay.open { display: block; }
  .drawer {
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: 380px;
    max-width: 100vw;
    background: var(--c-surface);
    border-left: 1px solid var(--c-border);
    z-index: 101;
    transform: translateX(100%);
    transition: transform .28s cubic-bezier(.4,0,.2,1);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }
  .drawer.open { transform: translateX(0); }
  .drawer-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 1.5rem;
    border-bottom: 1px solid var(--c-border);
    position: sticky;
    top: 0;
    background: var(--c-surface);
    z-index: 1;
  }
  .drawer-close {
    width: 30px; height: 30px;
    border-radius: 50%;
    border: 1px solid var(--c-border-strong);
    background: none;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    color: var(--c-muted);
    font-size: 16px;
    flex-shrink: 0;
    transition: background .15s;
  }
  .drawer-close:hover { background: var(--c-bg); }
  .drawer-body { padding: 1.5rem; flex: 1; }
  .drawer-section { margin-bottom: 1.5rem; }
  .drawer-section-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: var(--c-hint);
    margin-bottom: 10px;
  }
  .drawer-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--c-border);
    font-size: 13px;
  }
  .drawer-row:last-child { border-bottom: none; }
  .drawer-row-label { color: var(--c-muted); }
  .drawer-row-val { font-weight: 500; text-align: right; }
  .drawer-avatar {
    width: 44px; height: 44px;
    border-radius: 50%;
    background: var(--c-accent-bg);
    color: #185FA5;
    font-weight: 600;
    font-size: 14px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }

  /* ── Pagination ── */
  .pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-top: 1px solid var(--c-border);
    background: var(--c-bg);
    font-size: 12px;
    color: var(--c-muted);
    flex-wrap: wrap;
    gap: 8px;
  }
  .page-btns { display: flex; gap: 4px; }
  .page-btn {
    width: 30px; height: 30px;
    border: 1px solid var(--c-border-strong);
    border-radius: var(--radius-sm);
    background: var(--c-surface);
    font-size: 12px;
    font-family: 'DM Mono', monospace;
    color: var(--c-muted);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all .15s;
  }
  .page-btn:hover { border-color: var(--c-accent); color: var(--c-accent); }
  .page-btn.active { background: var(--c-accent); border-color: var(--c-accent); color: #fff; }
  .page-btn:disabled { opacity: .35; cursor: default; }

  @media (max-width: 700px) {
    .stat-grid { grid-template-columns: repeat(2, 1fr); }
    .toolbar { flex-direction: column; align-items: stretch; }
    .results-count { margin-left: 0; }
    .drawer { width: 100vw; }
    
    /* Mobile table: horizontal scroll */
    .table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { min-width: 800px; }
    
    /* Mobile drawer adjustments */
    .drawer { padding: 15px; }
    .drawer-header { flex-direction: column; gap: 10px; }
    .drawer-body { padding: 15px; }
    
    /* Mobile buttons */
    .action-btn { padding: 8px 12px; font-size: 12px; }
    .btn-email, .btn-pdf, .btn-delete { 
      display: block; width: 100%; margin: 5px 0; text-align: center; 
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  @keyframes pulse {
    0%, 100% { stroke-opacity: 1; }
    50% { stroke-opacity: 0.5; }
  }
`

type SortKey = 'pin' | 'name' | 'salary' | 'date'

// Replica of contracts/templates/contracts/list.html
export function ContractsList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [q, setQ] = useState('')
  const [serverQ, setServerQ] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [startDateFilter, setStartDateFilter] = useState('')
  const [endDateFilter, setEndDateFilter] = useState('')
  const [statFilter, setStatFilter] = useState('all')
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<1 | -1>(1)
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<number[]>([])
  const [drawer, setDrawer] = useState<Row | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Contract | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)
  const ownsFlash = useRef(false)

  // HrLayout only drains the flash slot on a navigation, and several outcomes
  // here (a deleted row, an unavailable PDF) deliberately stay on this page --
  // so the message is rendered inline and the pending slot is dropped again.
  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  // The template filters as you type; the server pass trails a beat behind so
  // every keystroke does not become its own request.
  useEffect(() => {
    const timer = setTimeout(() => setServerQ(q.trim()), 300)
    return () => clearTimeout(timer)
  }, [q])

  useEffect(() => {
    setPage(1)
  }, [q, typeFilter, statusFilter, startDateFilter, endDateFilter, statFilter, sortKey, sortDir])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setDrawer(null)
        setDeleteTarget(null)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const sortParam = sortKey
    ? `${sortDir === -1 ? '-' : ''}${sortKey === 'date' ? 'start_date' : sortKey}`
    : '-id'

  // list.html's table: server-side q/type/status/sort (contract_list's own
  // filter set) plus the client-side pass applyFilters() runs over the rows.
  const listQuery = useQuery({
    queryKey: ['contracts', 'list', serverQ, typeFilter, statusFilter, sortParam],
    queryFn: async () =>
      getAllResults<Contract>('/contracts/', {
        q: serverQ || undefined,
        type: typeFilter || undefined,
        status: statusFilter || undefined,
        sort: sortParam,
      }),
    placeholderData: keepPreviousData,
  })

  // buildStats() reads every contract rather than the filtered page, so the
  // six stat cards keep their totals while the toolbar narrows the table.
  const statsQuery = useQuery({
    queryKey: ['contracts', 'stats'],
    queryFn: async () => getAllResults<Contract>('/contracts/'),
  })

  useEffect(() => {
    if (listQuery.isError) {
      setNotice({ level: 'error', text: flashFromError(listQuery.error).text })
    }
  }, [listQuery.isError, listQuery.error])

  const rows = useMemo<Row[]>(
    () =>
      (listQuery.data?.results ?? []).map((r) => ({
        ...r,
        _status: computeStatus(r.end_date),
      })),
    [listQuery.data],
  )

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const out = rows.filter((r) => {
      const matchQ =
        !needle ||
        r.pin.toLowerCase().includes(needle) ||
        r.name.toLowerCase().includes(needle) ||
        (r.designation || '').toLowerCase().includes(needle) ||
        (r.new_designation || '').toLowerCase().includes(needle)
      const matchType = !typeFilter || r.contract_type === typeFilter
      const matchStatus = !statusFilter || r._status === statusFilter
      const matchStat =
        statFilter === 'all'
          ? true
          : statFilter === 'expiring'
            ? r._status === 'Expiring'
            : r.contract_type === statFilter
      let matchDate = true
      if (startDateFilter && r.start_date) {
        matchDate = matchDate && r.start_date >= startDateFilter
      }
      if (endDateFilter && r.end_date) {
        matchDate = matchDate && r.end_date <= endDateFilter
      }
      return matchQ && matchType && matchStatus && matchStat && matchDate
    })

    if (sortKey) {
      out.sort((a, b) => {
        let av: number | string
        let bv: number | string
        if (sortKey === 'salary') {
          av = Number(a.salary) || 0
          bv = Number(b.salary) || 0
        } else if (sortKey === 'date') {
          av = a.start_date || ''
          bv = b.start_date || ''
        } else if (sortKey === 'pin') {
          av = a.pin
          bv = b.pin
        } else {
          av = a.name
          bv = b.name
        }
        if (av < bv) return -sortDir
        if (av > bv) return sortDir
        return 0
      })
    }
    return out
  }, [rows, q, typeFilter, statusFilter, statFilter, startDateFilter, endDateFilter, sortKey, sortDir])

  const stats = useMemo(() => {
    const all = (statsQuery.data?.results ?? []).map((r) => ({
      ...r,
      _status: computeStatus(r.end_date),
    }))
    return {
      total: all.length,
      newC: all.filter((r) => r.contract_type === 'New').length,
      ext: all.filter((r) => r.contract_type === 'Extension').length,
      rev: all.filter((r) => r.contract_type === 'Revision').length,
      renew: all.filter((r) => r.contract_type === 'Renewal').length,
      expiring: all.filter((r) => r._status === 'Expiring').length,
    }
  }, [statsQuery.data])

  const total = filtered.length
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.min(page, pages)
  const start = (currentPage - 1) * PAGE_SIZE
  const slice = filtered.slice(start, start + PAGE_SIZE)
  const shown = Math.min(start + PAGE_SIZE, total)
  const pageInfo = total === 0 ? '' : `${start + 1}–${shown} of ${total}`
  const resultsCount = listQuery.isLoading
    ? '— results'
    : `${total} ${total === 1 ? 'result' : 'results'}`

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === 1 ? -1 : 1))
    else {
      setSortKey(key)
      setSortDir(1)
    }
  }

  function goPage(p: number) {
    setPage(Math.max(1, Math.min(p, pages)))
    document.querySelector('.dash-wrap')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function filterByStat(val: string) {
    setStatFilter(val)
    setTypeFilter('')
    setStatusFilter('')
    setQ('')
    setServerQ('')
    setStartDateFilter('')
    setEndDateFilter('')
  }

  function arrow(key: SortKey) {
    if (sortKey !== key) return ''
    return sortDir === 1 ? ' ↑' : ' ↓'
  }

  function headerClass(key: SortKey) {
    return sortKey === key ? 'sorted' : ''
  }

  const pageSliceAllChecked = slice.length > 0 && slice.every((r) => selected.includes(r.id))

  function toggleSelectAll() {
    if (pageSliceAllChecked) {
      const ids = slice.map((r) => r.id)
      setSelected((prev) => prev.filter((id) => !ids.includes(id)))
    } else {
      setSelected((prev) => Array.from(new Set([...prev, ...slice.map((r) => r.id)])))
    }
  }

  function toggleRow(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  function openBulkEmail() {
    if (selected.length === 0) {
      window.alert('Please select at least one contract to email.')
      return
    }
    navigate('/hr/contracts/bulk-email', { state: { contractIds: selected } })
  }

  async function handlePdf(c: Contract) {
    try {
      await downloadContractPdf(c.id, c.pin)
    } catch (err) {
      const text = await pdfErrorText(err)
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await api.delete(`/contracts/${deleteTarget.id}/`)
      const text = 'Contract deleted successfully.'
      setFlash('success', text)
      ownsFlash.current = true
      setNotice({ level: 'success', text })
      setDeleteTarget(null)
      setDrawer(null)
      setSelected((prev) => prev.filter((id) => id !== deleteTarget.id))
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
    } catch (err) {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    } finally {
      setDeleting(false)
    }
  }

  const pageNumbers: Array<number | 'gap'> = []
  if (pages > 1) {
    for (let i = 1; i <= pages; i++) {
      if (pages > 7 && i > 2 && i < pages - 1 && Math.abs(i - currentPage) > 1) {
        if (i === 3 || i === pages - 2) pageNumbers.push('gap')
        continue
      }
      pageNumbers.push(i)
    }
  }

  const statCards: Array<{ filter: string; label: string; value: number; sub: string }> = [
    { filter: 'all', label: 'Total', value: stats.total, sub: 'All contracts' },
    { filter: 'New', label: 'New Contracts', value: stats.newC, sub: 'Click to filter' },
    { filter: 'Extension', label: 'Extensions', value: stats.ext, sub: 'Click to filter' },
    { filter: 'Revision', label: 'Revisions', value: stats.rev, sub: 'Click to filter' },
    { filter: 'Renewal', label: 'Renewals', value: stats.renew, sub: 'Click to filter' },
    { filter: 'expiring', label: 'Expiring soon', value: stats.expiring, sub: 'Within 30 days' },
  ]

  return (
    <>
      <PageStyle css={css} />
      <link
        href={
          'https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap'
        }
        rel="stylesheet"
      />

      {notice && (
        <div className={`app-message ${notice.level}`}>
          <span className="msg-close" onClick={() => setNotice(null)}>
            &times;
          </span>
          {notice.text}
        </div>
      )}

      <div className="dash-wrap">
        {/* Header */}
        <div className="dash-header">
          <div>
            <h1>Contracts dashboard</h1>
            <p>Manage and review all employee contracts</p>
          </div>
          <Link
            to="/hr/contracts/create"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '9px 18px',
              background: '#2563EB',
              color: '#fff',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: '500',
              fontFamily: "'DM Sans',sans-serif",
              textDecoration: 'none',
              transition: 'background .15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#1D4ED8')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#2563EB')}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            New contract
          </Link>
          <Link
            to="/hr/contracts/bulk-create"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '9px 18px',
              background: '#7C3AED',
              color: '#fff',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: '500',
              textDecoration: 'none',
            }}
          >
            📤 Bulk Upload
          </Link>
          <button
            type="button"
            onClick={openBulkEmail}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '9px 18px',
              background: '#059669',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'background .15s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#047857')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#059669')}
          >
            {selected.length > 0 ? `📧 Bulk Email (${selected.length})` : '📧 Bulk Email'}
          </button>
        </div>

        {/* Stat cards */}
        <div className="stat-grid">
          {statCards.map((card) => (
            <div
              key={card.filter}
              className={`stat-card ${statFilter === card.filter ? 'active' : ''}`}
              onClick={() => filterByStat(card.filter)}
            >
              <div className="stat-label">{card.label}</div>
              <div className="stat-value">{card.value}</div>
              <div className="stat-sub">{card.sub}</div>
            </div>
          ))}
        </div>

        {/* Toolbar */}
        <div className="toolbar">
          <div className="search-wrap">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="6.5" cy="6.5" r="4.5" />
              <path d="M10 10l3 3" strokeLinecap="round" />
            </svg>
            <input
              type="text"
              placeholder="Search PIN, name, designation…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <select
            className="filter-select"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">All types</option>
            <option value="New">New Contract</option>
            <option value="Extension">Extension</option>
            <option value="Revision">Revision</option>
            <option value="Renewal">Renewal</option>
          </select>
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="Active">Active</option>
            <option value="Expiring">Expiring soon</option>
            <option value="Expired">Expired</option>
          </select>
          <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
            <input
              type="date"
              className="filter-select"
              style={{ width: '130px', padding: '0 10px' }}
              title="Contract start date from"
              value={startDateFilter}
              onChange={(e) => setStartDateFilter(e.target.value)}
            />
            <span style={{ color: 'var(--c-muted)', fontSize: '12px' }}>to</span>
            <input
              type="date"
              className="filter-select"
              style={{ width: '130px', padding: '0 10px' }}
              title="Contract end date to"
              value={endDateFilter}
              onChange={(e) => setEndDateFilter(e.target.value)}
            />
          </div>
          <button
            className={`sort-btn ${sortKey === 'salary' ? 'active' : ''}`}
            onClick={() => toggleSort('salary')}
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                d="M4 12V4M4 4L2 6M4 4l2 2M12 4v8M12 12l-2-2M12 12l2-2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Salary
          </button>
          <button
            className={`sort-btn ${sortKey === 'date' ? 'active' : ''}`}
            onClick={() => toggleSort('date')}
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <rect x="2" y="3" width="12" height="11" rx="2" />
              <path d="M2 7h12M5 1v4M11 1v4" strokeLinecap="round" />
            </svg>
            Date
          </button>
          <span className="results-count">{resultsCount}</span>
        </div>

        {/* Table */}
        <div className="table-card">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input type="checkbox" checked={pageSliceAllChecked} onChange={toggleSelectAll} />
                  </th>
                  <th style={{ width: '90px' }} className={headerClass('pin')} onClick={() => toggleSort('pin')}>
                    PIN <span className="sort-arrow">{arrow('pin')}</span>
                  </th>
                  <th style={{ width: '140px' }} className={headerClass('name')} onClick={() => toggleSort('name')}>
                    Name <span className="sort-arrow">{arrow('name')}</span>
                  </th>
                  <th style={{ width: '130px' }}>Designation</th>
                  <th style={{ width: '130px' }}>New designation</th>
                  <th
                    style={{ width: '100px' }}
                    className={headerClass('salary')}
                    onClick={() => toggleSort('salary')}
                  >
                    Salary <span className="sort-arrow">{arrow('salary')}</span>
                  </th>
                  <th style={{ width: '100px' }}>Type</th>
                  <th
                    style={{ width: '100px' }}
                    className={headerClass('date')}
                    onClick={() => toggleSort('date')}
                  >
                    Start date <span className="sort-arrow">{arrow('date')}</span>
                  </th>
                  <th style={{ width: '100px' }}>End date</th>
                  <th style={{ width: '90px' }}>Status</th>
                  <th style={{ width: '120px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {listQuery.isLoading ? (
                  <tr>
                    <td colSpan={11} className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : slice.length === 0 ? (
                  <tr>
                    <td colSpan={10}>
                      <div className="empty-state">
                        <div className="empty-icon">
                          <svg
                            width="20"
                            height="20"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="#A8A79F"
                            strokeWidth="1.5"
                          >
                            <path
                              d="M2 4h12M4 4V2h8v2M4 4v10h8V4"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </div>
                        <h3>No contracts found</h3>
                        <p>Try adjusting your search or filters.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  slice.map((r) => (
                    <tr key={r.id} onClick={() => setDrawer(r)} title="Click to view details">
                      <td onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selected.includes(r.id)}
                          onChange={() => toggleRow(r.id)}
                        />
                      </td>
                      <td className="pin-cell">{r.pin}</td>
                      <td className="name-cell">{r.name}</td>
                      <td style={{ color: 'var(--c-muted)' }}>{r.designation || '—'}</td>
                      <td style={{ color: 'var(--c-muted)' }}>{r.new_designation || '—'}</td>
                      <td style={{ fontFamily: "'DM Mono',monospace", fontSize: '12px' }}>
                        {fmtMoney(r.salary)}
                      </td>
                      <td>
                        <span className={`badge ${badgeClass(r.contract_type)}`}>{r.contract_type}</span>
                      </td>
                      <td style={{ color: 'var(--c-muted)' }}>{fmtDate(r.start_date)}</td>
                      <td style={{ color: 'var(--c-muted)' }}>{fmtDate(r.end_date)}</td>
                      <td>
                        <span className={`badge ${statusClass(r._status)}`}>{r._status}</span>
                      </td>
                      <td onClick={(e) => e.stopPropagation()} style={{ whiteSpace: 'nowrap' }}>
                        <button
                          className="action-btn btn-pdf"
                          title="Download PDF"
                          onClick={() => handlePdf(r)}
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                          >
                            <path
                              d="M3 12h10M8 2v8M5 7l3 3 3-3"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                          PDF
                        </button>
                        <Link
                          to={`/hr/contracts/email/${r.id}`}
                          className="action-btn btn-email"
                          title="Send via Email"
                          style={{ marginLeft: '4px' }}
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                          >
                            <path
                              d="M2 4h12M2 4l-1 8h14l-1-8M2 4l5 4 5-4"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                          Email
                        </Link>
                        <button
                          className="action-btn btn-delete"
                          title="Delete contract"
                          style={{ marginLeft: '4px' }}
                          onClick={() => setDeleteTarget(r)}
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                          >
                            <path
                              d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M4 4l1 9h6l1-9"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span style={{ fontFamily: "'DM Mono',monospace" }}>{pageInfo}</span>
            <div className="page-btns">
              {pages > 1 && (
                <button
                  className="page-btn"
                  disabled={currentPage === 1}
                  onClick={() => goPage(currentPage - 1)}
                >
                  ‹
                </button>
              )}
              {pageNumbers.map((n, i) =>
                n === 'gap' ? (
                  <span
                    key={`gap-${i}`}
                    style={{ alignSelf: 'center', color: 'var(--c-hint)', padding: '0 4px' }}
                  >
                    …
                  </span>
                ) : (
                  <button
                    key={n}
                    className={`page-btn ${n === currentPage ? 'active' : ''}`}
                    onClick={() => goPage(n)}
                  >
                    {n}
                  </button>
                ),
              )}
              {pages > 1 && (
                <button
                  className="page-btn"
                  disabled={currentPage === pages}
                  onClick={() => goPage(currentPage + 1)}
                >
                  ›
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Detail Drawer ── */}
      <div className={`drawer-overlay ${drawer ? 'open' : ''}`} onClick={() => setDrawer(null)} />
      <div className={`drawer ${drawer ? 'open' : ''}`}>
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="drawer-avatar">{drawer ? initials(drawer.name) : '–'}</div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 600 }}>{drawer ? drawer.name : '–'}</div>
              <div style={{ fontSize: '13px', color: 'var(--c-muted)', marginTop: '2px' }}>
                {drawer ? `PIN: ${drawer.pin}` : '–'}
              </div>
            </div>
          </div>
          <button className="drawer-close" onClick={() => setDrawer(null)}>
            ✕
          </button>
        </div>
        <div className="drawer-body">
          <div className="drawer-section">
            <div className="drawer-section-title">Contract details</div>
            {drawer && (
              <div>
                <div className="drawer-row">
                  <span className="drawer-row-label">Contract type</span>
                  <span className="drawer-row-val">
                    <span className={`badge ${badgeClass(drawer.contract_type)}`}>
                      {drawer.contract_type}
                    </span>
                  </span>
                </div>
                <div className="drawer-row">
                  <span className="drawer-row-label">Status</span>
                  <span className="drawer-row-val">
                    <span className={`badge ${statusClass(drawer._status)}`}>{drawer._status}</span>
                  </span>
                </div>
                <div className="drawer-row">
                  <span className="drawer-row-label">Designation</span>
                  <span className="drawer-row-val">{drawer.designation || '—'}</span>
                </div>
                <div className="drawer-row">
                  <span className="drawer-row-label">New designation</span>
                  <span className="drawer-row-val">{drawer.new_designation || '—'}</span>
                </div>
                <div className="drawer-row">
                  <span className="drawer-row-label">Salary</span>
                  <span className="drawer-row-val">{fmtMoney(drawer.salary)}</span>
                </div>
                <div className="drawer-row">
                  <span className="drawer-row-label">Start date</span>
                  <span className="drawer-row-val">{fmtDate(drawer.start_date)}</span>
                </div>
                <div className="drawer-row">
                  <span className="drawer-row-label">End date</span>
                  <span className="drawer-row-val">{fmtDate(drawer.end_date)}</span>
                </div>
              </div>
            )}
          </div>
          <div style={{ marginTop: '1.5rem' }}>
            <button
              onClick={() => drawer && handlePdf(drawer)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                width: '100%',
                padding: '10px',
                background: 'var(--c-success-bg)',
                color: 'var(--c-success)',
                border: '1px solid rgba(22,163,74,.2)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
                fontWeight: '500',
                fontFamily: "'DM Sans',sans-serif",
                cursor: 'pointer',
                transition: 'all .15s',
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  d="M3 12h10M8 2v8M5 7l3 3 3-3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Download PDF
            </button>
            <Link
              to={drawer ? `/hr/contracts/email/${drawer.id}` : '#'}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '10px',
                background: '#EFF6FF',
                color: '#2563EB',
                border: '1px solid rgba(37,99,235,.2)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
                fontWeight: '500',
                fontFamily: "'DM Sans',sans-serif",
                textDecoration: 'none',
                transition: 'all .15s',
                marginTop: '8px',
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  d="M2 4h12M2 4l-1 8h14l-1-8M2 4l5 4 5-4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Send via Email
            </Link>
            <button
              onClick={() => {
                if (!drawer) return
                setDrawer(null)
                setDeleteTarget(drawer)
              }}
              style={{
                marginTop: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                width: '100%',
                padding: '10px',
                background: 'var(--c-danger-bg)',
                color: 'var(--c-danger)',
                border: '1px solid rgba(220,38,38,.2)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
                fontWeight: '500',
                fontFamily: "'DM Sans',sans-serif",
                cursor: 'pointer',
                transition: 'all .15s',
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M4 4l1 9h6l1-9"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Delete contract
            </button>
          </div>
        </div>
      </div>

      {/* ── Delete confirm modal ── */}
      <div className={`modal-backdrop ${deleteTarget ? 'open' : ''}`}>
        <div className="modal-box">
          <div className="modal-header">
            <div className="modal-icon">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="#DC2626"
                strokeWidth="1.5"
              >
                <path
                  d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M4 4l1 9h6l1-9"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div className="modal-title">Delete contract</div>
          </div>
          <div className="modal-body">
            Are you sure you want to delete the contract for{' '}
            <strong>{deleteTarget?.name ?? '—'}</strong>
            (
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: '12px' }}>
              {deleteTarget?.pin ?? '—'}
            </span>
            )?
            <br />
            <br />
            This action <strong>cannot be undone</strong>. The contract record and its PDF will be
            permanently removed.
          </div>
          <div className="modal-footer">
            <button className="modal-btn modal-btn-cancel" onClick={() => setDeleteTarget(null)}>
              Cancel
            </button>
            <button
              className="modal-btn modal-btn-confirm"
              onClick={confirmDelete}
              disabled={deleting}
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M4 4l1 9h6l1-9"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Yes, delete
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
