import { api } from '@/api/axios'
import { PaginatedResponse } from '@/types'

/**
 * Every list endpoint is page-sized (DRF ``PAGE_SIZE = 20``), and no view in
 * the app passed a page parameter -- so any collection longer than 20 quietly
 * showed only its first 20 rows. 27 configured form fields rendered as 20; a
 * requisition log, an audit trail or an email log would lose everything past
 * the first screen as soon as it grew.
 *
 * Follow DRF's ``next`` and hand back the whole collection. Only the page
 * number is lifted off ``next`` (never the URL itself) so it works whether
 * Django reports the proxied host on :5173 or its own on :8000.
 */
export async function getAllResults<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<PaginatedResponse<T>> {
  const results: T[] = []
  let count = 0
  let page = 1

  for (;;) {
    const { data } = await api.get<PaginatedResponse<T>>(path, {
      params: { ...params, page },
    })
    results.push(...data.results)
    count = data.count

    if (!data.next) break

    const nextPage = Number(new URL(data.next, window.location.origin).searchParams.get('page'))
    // Stop rather than loop if Django ever hands back a next without a usable
    // page number (an unpaged response, or a URL we cannot make sense of).
    if (!Number.isFinite(nextPage) || nextPage === page) break
    page = nextPage
  }

  return { count, next: null, previous: null, results }
}
