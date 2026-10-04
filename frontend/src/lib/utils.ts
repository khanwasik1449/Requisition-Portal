import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date, format = 'PPP'): string {
  const d = new Date(date)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    pending_first: 'bg-blue-100 text-blue-800',
    pending_grants: 'bg-purple-100 text-purple-800',
    pending_transport: 'bg-orange-100 text-orange-800',
    approved: 'bg-green-100 text-green-800',
    assigned: 'bg-indigo-100 text-indigo-800',
    rejected: 'bg-red-100 text-red-800',
    alternative_suggested: 'bg-teal-100 text-teal-800',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

export function getRoleColor(role: string): string {
  const colors: Record<string, string> = {
    admin: 'bg-red-100 text-red-800',
    supervisor: 'bg-blue-100 text-blue-800',
    grants: 'bg-purple-100 text-purple-800',
    transport_admin: 'bg-orange-100 text-orange-800',
    ict_admin: 'bg-green-100 text-green-800',
    internal_admin: 'bg-indigo-100 text-indigo-800',
    hr_admin: 'bg-pink-100 text-pink-800',
    requester: 'bg-gray-100 text-gray-800',
  }
  return colors[role] || 'bg-gray-100 text-gray-800'
}