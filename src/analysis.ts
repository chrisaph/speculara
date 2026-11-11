export type TextSample = {
  id: string; text: string; tone: 'pos' | 'neg' | 'neu'; score?: number; kind?: string;
  author?: string; post_id: string; post_type: string; post_caption?: string; posted_at?: string;
  source_url?: string; post_url?: string; source_kind?: string;
}

export function sourceHref(value: unknown): string | undefined {
  if (typeof value !== 'string' || !value) return undefined
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !u.username ? u.href : undefined } catch { return undefined }
}

export function sentimentView(analysis: any, options: { query?: string; range?: string; postType?: string; tone?: string; now?: number } = {}) {
  const all: TextSample[] = Array.isArray(analysis?.sentiment?.samples) ? analysis.sentiment.samples : []
  const query = options.query?.trim().toLowerCase() || ''
  const days = options.range === 'Last 30 days' ? 30 : options.range === 'Last 3 months' ? 90 : null
  const samples = all.filter((s) => (!query || `${s.text} ${s.post_caption || ''}`.toLowerCase().includes(query))
    && (!days || Date.parse(s.posted_at || '') >= (options.now ?? Date.now()) - days * 86400000)
    && (!options.postType || options.postType === 'All types' || s.post_type === options.postType)
    && (!options.tone || options.tone === 'All' || s.tone === options.tone))
  const positive = samples.filter((s) => s.tone === 'pos').length
  const negative = samples.filter((s) => s.tone === 'neg').length
  const pos = samples.length ? Math.round(100 * positive / samples.length) : 0
  const neg = samples.length ? Math.round(100 * negative / samples.length) : 0
  const keywords = (analysis?.sentiment?.keywords || []).flatMap((k: any) => {
    const matching = samples.filter((s) => k.sample_ids?.includes(s.id) || (!k.sample_ids && s.text.toLowerCase().includes(k.w.toLowerCase())))
    return matching.length ? [{ ...k, n: matching.length }] : []
  })
  return { samples, keywords, pos, neg, neu: samples.length ? 100 - pos - neg : 0,
    types: ['All types', ...new Set(all.map((s) => s.post_type))], basis: analysis?.sentiment?.basis || 'none' }
}

export function demandPeriods(weekly: any[] = [], period = 'Weekly') {
  const grouped = new Map<string, number>()
  for (const row of weekly) {
    const label = period === 'Monthly' ? row.date.slice(0, 7) : row.date
    grouped.set(label, (grouped.get(label) || 0) + Number(row.questions || 0) + Number(row.requests || 0))
  }
  return [...grouped].map(([label, value]) => ({ label, value }))
}
