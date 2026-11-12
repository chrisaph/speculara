import { sourceHref } from './analysis.ts'

export function resolvePost(posts: any[], input: string): string | undefined {
  const value = input.trim()
  if (!value || value === 'all') return 'all'
  const canonical = (url: string) => { try { const u = new URL(url); return u.hostname.toLowerCase().replace(/^www\./, '') + u.pathname.replace(/\/$/, '') } catch { return '' } }
  return posts.find(p => p.id === value || (canonical(value) && canonical(p.url) === canonical(value)))?.id
}

export function chartView(analysis: any, metric: string, period = 'month', selected = 'all') {
  const posts = (analysis?.evidence?.posts || []).filter((p: any) => !(p.unavailable_metrics || []).includes(metric) && Number.isFinite(p[metric]))
  const filtered = posts.filter((p: any) => selected === 'all' || p.id === selected)
  const groups = new Map<string, number>()
  for (const p of filtered) {
    const date = new Date(p.posted_at)
    if (!Number.isFinite(date.getTime())) continue
    if (period === 'week') date.setUTCDate(date.getUTCDate() - (date.getUTCDay() + 6) % 7)
    const label = date.toISOString().slice(0, period === 'month' ? 7 : 10)
    groups.set(label, (groups.get(label) || 0) + p[metric])
  }
  const series = [...groups].sort(([a], [b]) => a.localeCompare(b)).map(([label, value]) => ({ label, value }))
  const total = posts.reduce((sum: number, p: any) => sum + p[metric], 0)
  return { series, posts, total, known: posts.length, shares: posts.map((p: any) => ({ ...p, pct: total ? 100 * p[metric] / total : 0 })),
    selectedTotal: filtered.length ? filtered.reduce((sum: number, p: any) => sum + p[metric], 0) : null }
}

export function correlationView(analysis: any, mode = 'All pairs') {
  const c = analysis?.correlation || {}
  const matches = (v: number | null) => v != null && (mode === 'All pairs' || (mode === 'Negative only' ? v < 0 : Math.abs(v) >= .5))
  return { matrix: c.matrix || {}, pairs: (c.pairs || []).filter((p: any) => matches(p.v)), matches, scatter: c.scatter || {} }
}

export function postTitle(post: any) { return post?.title || post?.caption || `${post?.type || 'Post'} ${post?.id || ''}` }
export const safePostLink = (post: any) => sourceHref(post?.url)
