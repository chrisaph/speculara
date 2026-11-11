import { useState, type ReactNode } from 'react'
import { demandPeriods, sentimentView, sourceHref, type TextSample } from '../analysis'

const tones = { pos: { label: 'Positive', color: '#29348f' }, neg: { label: 'Negative', color: '#8f2934' }, neu: { label: 'Neutral', color: '#475569' } }
const Well = ({ children }: { children: ReactNode }) => <div className="neu-in mt-4 rounded-2xl p-4">{children}</div>
const Metric = ({ label, value }: { label: string; value: ReactNode }) => <div className="neu-sm rounded-2xl p-3"><p className="text-xs text-slate-600">{label}</p><p className="mt-1 font-display text-xl font-semibold text-ink">{value}</p></div>

function Tabs({ items, value, onChange }: { items: string[]; value: string; onChange: (value: string) => void }) {
  return <div className="no-bar -mx-1 flex gap-3 overflow-x-auto p-2">{items.map((item) => <button key={item} type="button" aria-pressed={value === item} onClick={() => onChange(item)} className={`${value === item ? 'neu-in text-ink' : 'neu-sm text-slate-600'} min-h-10 shrink-0 rounded-full px-4 text-xs font-semibold`}>{item}</button>)}</div>
}

export function SourceButton({ url, label = 'Source', kind = 'post', postType = '' }: { url?: string; label?: string; kind?: string; postType?: string }) {
  const href = sourceHref(url)
  const detail = kind === 'comment' ? 'Opens the original comment' : `Opens the parent ${postType === 'Reel' ? 'reel' : 'post'}`
  if (!href) return <span className="neu-in inline-flex min-h-9 items-center rounded-full px-3 text-[11px] text-slate-500" title="No original link was provided for this sample">Source unavailable</span>
  return <a href={href} target="_blank" rel="noopener noreferrer" title={detail} aria-label={`${label}: ${detail.toLowerCase()}`} className="neu-sm inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs font-semibold text-ink transition hover:text-wine focus-visible:outline-2 focus-visible:outline-sky">
    {label}<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M14 3h7v7M21 3l-9 9M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5" /></svg>
  </a>
}

function CommentCard({ sample }: { sample: TextSample }) {
  const tone = tones[sample.tone] || tones.neu
  return <li className="neu-sm rounded-2xl p-4">
    <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs"><span style={{ color: tone.color }} className="font-semibold">{tone.label} · {sample.post_type}{sample.kind === 'caption' ? ' caption' : ' comment'}</span><SourceButton url={sample.source_url || sample.post_url} kind={sample.source_kind} postType={sample.post_type} /></div>
    <blockquote className="whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700">“{sample.text}”</blockquote>
    {sample.author && <p className="mt-2 text-xs text-slate-500">@{sample.author}</p>}
    {sample.source_url && sample.source_kind !== 'comment' && <p className="mt-2 text-[11px] text-slate-500">Source opens the parent {sample.post_type === 'Reel' ? 'reel' : 'post'}; a direct comment link was not supplied.</p>}
  </li>
}

export function EvidenceSources({ analysis }: { analysis: any }) {
  const posts: any[] = analysis?.evidence?.posts || []
  if (!posts.length) return null
  return <details className="neu-in mb-5 rounded-2xl p-4">
    <summary className="cursor-pointer font-display text-sm font-semibold text-ink">Sources · {posts.length} collected posts</summary>
    <ul className="mt-4 grid gap-3 sm:grid-cols-2">{posts.map((post) => <li key={post.id} className="neu-sm flex items-center justify-between gap-3 rounded-xl p-3"><div className="min-w-0"><p className="text-[11px] font-semibold text-ink">{post.type}</p><p className="line-clamp-2 break-words text-xs text-slate-600">{post.caption || `Post ${post.id}`}</p></div><SourceButton url={post.url} postType={post.type} /></li>)}</ul>
  </details>
}

export function SentimentPanel({ analysis }: { analysis: any }) {
  const [query, setQuery] = useState('')
  const [range, setRange] = useState('All time')
  const [postType, setPostType] = useState('All types')
  const [tone, setTone] = useState('All')
  const [page, setPage] = useState(1)
  const view = sentimentView(analysis, { query, range, postType, tone })
  const max = Math.max(1, ...view.keywords.map((k: any) => k.n))
  const change = (set: (value: string) => void) => (value: string) => { set(value); setPage(1) }
  return <section className="neu rounded-3xl p-4 sm:p-6" aria-label="Sentiment analysis">
    <h3 className="font-display text-lg font-bold text-ink">Sentiment</h3>
    <p className="mt-1 text-xs text-slate-600">{view.basis === 'comments' ? 'Measured from collected comment samples, with links to their original posts.' : view.basis === 'captions' ? 'No comment text was returned. These scores describe post captions, not audience reactions.' : 'Analyze a profile to load the text that can be scored.'}</p>
    <label className="mt-4 block text-xs font-semibold text-slate-600" htmlFor="sentiment-query">Find text or a post</label>
    <input id="sentiment-query" value={query} onChange={(e) => change(setQuery)(e.target.value)} placeholder="Search collected text…" className="neu-in mt-2 min-h-11 w-full rounded-xl bg-transparent px-4 text-sm outline-none focus-visible:outline-2 focus-visible:outline-sky" />
    <Tabs items={['All time', 'Last 30 days', 'Last 3 months']} value={range} onChange={change(setRange)} />
    <Tabs items={view.types} value={postType} onChange={change(setPostType)} />
    <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Positive" value={view.samples.length ? `${view.pos}%` : '—'} /><Metric label="Neutral" value={view.samples.length ? `${view.neu}%` : '—'} /><Metric label="Negative" value={view.samples.length ? `${view.neg}%` : '—'} /><Metric label="Scored text samples" value={view.samples.length} /></div>
    <Well><h4 className="mb-2 text-sm font-semibold text-ink">Keywords in the collected text</h4>
      <Tabs items={['All', 'Positive', 'Neutral', 'Negative']} value={tone === 'pos' ? 'Positive' : tone === 'neg' ? 'Negative' : tone === 'neu' ? 'Neutral' : 'All'} onChange={(value) => change(setTone)(({ Positive: 'pos', Negative: 'neg', Neutral: 'neu' } as Record<string, string>)[value] || 'All')} />
      {view.keywords.length ? <ul className="grid gap-x-6 gap-y-3 sm:grid-cols-2">{view.keywords.map((k: any) => <li key={k.w} className="flex items-center gap-2 text-xs"><span className="w-24 truncate" style={{ color: (tones[k.s as keyof typeof tones] || tones.neu).color }}>{k.w}</span><span className="neu-in h-2.5 flex-1 overflow-hidden rounded-full"><span className="block h-full rounded-full" style={{ width: `${100 * k.n / max}%`, background: (tones[k.s as keyof typeof tones] || tones.neu).color }} /></span><span>{k.n}</span></li>)}</ul> : <p className="text-sm text-slate-600">No keywords match these filters.</p>}
    </Well>
    <Well><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h4 className="text-sm font-semibold text-ink">{view.basis === 'captions' ? 'Collected captions' : 'Collected comments'}</h4><span className="text-xs text-slate-500">{view.samples.length} matching samples</span></div>
      {view.samples.length ? <><ul className="space-y-4">{view.samples.slice(0, page * 12).map((sample) => <CommentCard key={sample.id} sample={sample} />)}</ul>{view.samples.length > page * 12 && <button type="button" onClick={() => setPage(page + 1)} className="neu-sm mt-4 min-h-10 rounded-full px-4 text-xs font-semibold text-ink">Show more comments</button>}</> : <p role="status" className="text-sm text-slate-600">No collected text matches these filters. Try All time and All types. If no text was returned, collect the profile again after signing in.</p>}
    </Well>
    <p className="mt-4 text-xs leading-relaxed text-slate-600">Scores use VADER on the collected text. They describe a sample, not every comment or a person's intent. Source buttons open an exact comment when available, otherwise its parent post or reel.</p>
  </section>
}

export function DemandPanel({ analysis }: { analysis: any }) {
  const [query, setQuery] = useState('')
  const [period, setPeriod] = useState('Weekly')
  const demand = analysis?.demand || {}
  const summary = demand.summary || {}
  const ranking: any[] = (demand.ranking || []).filter((post: any) => post.p.toLowerCase().includes(query.toLowerCase()))
  const periods = demandPeriods(demand.weekly, period)
  const top = Math.max(1, ...periods.map((p) => p.value))
  const maxRank = Math.max(1, ...ranking.map((p) => p.q + p.ask))
  const samples: TextSample[] = analysis?.sentiment?.samples || []
  return <section className="neu rounded-3xl p-4 sm:p-6" aria-label="Demand analysis">
    <h3 className="font-display text-lg font-bold text-ink">Audience demand</h3>
    <p className="mt-1 text-xs text-slate-600">Questions and requests found in sampled comments. These signals do not require private sales or view counts.</p>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Questions" value={summary.questions ?? '—'} /><Metric label="Requests" value={summary.requests ?? '—'} /><Metric label="Sampled comments" value={summary.sampled_comments ?? 0} /><Metric label="Comments asking for more" value={summary.request_rate_pct == null ? '—' : `${summary.request_rate_pct}%`} /></div>
    {!summary.sampled_comments && <p role="status" className="neu-in mt-4 rounded-xl p-3 text-sm text-slate-600">No comment text was collected, so audience demand cannot be measured yet. Sign in and collect comments; unavailable sales metrics are a separate limitation.</p>}
    <Well><h4 className="text-sm font-semibold text-ink">Observed questions and requests over time</h4><Tabs items={['Weekly', 'Monthly']} value={period} onChange={setPeriod} />
      {periods.length && summary.sampled_comments ? <div className="no-bar overflow-x-auto pb-2"><div className="flex min-w-full items-end gap-3" role="img" aria-label={`${period} observed questions and requests`}>
        {periods.map((p) => <div key={p.label} className="min-w-14 flex-1 text-center"><div className="flex h-36 flex-col justify-end"><span className="mb-1 text-xs font-semibold text-ink">{p.value}</span><div className="rounded-t-lg bg-ink" style={{ height: `${Math.max(2, 100 * p.value / top)}%`, background: 'linear-gradient(180deg,#38bdf8,#29348f)', boxShadow: '3px 3px 7px #cbd3dd' }} /></div><p className="mt-2 whitespace-nowrap text-[10px] text-slate-500">{p.label}</p></div>)}
      </div></div> : <p className="py-3 text-sm text-slate-600">No comment-based timeline is available.</p>}
    </Well>
    <Well><h4 className="text-sm font-semibold text-ink">Posts people ask about</h4><label htmlFor="demand-query" className="sr-only">Find a post in the demand ranking</label><input id="demand-query" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a post…" className="neu-in my-3 min-h-11 w-full rounded-xl bg-transparent px-3 text-sm outline-none" />
      <ul className="space-y-4">{ranking.map((post) => <li key={post.post_id} className="neu-sm rounded-2xl p-4">
        <div className="flex items-start justify-between gap-3"><div><p className="text-[11px] font-semibold text-ink">{post.type}</p><p className="mt-1 break-words text-sm text-slate-700">{post.p}</p></div><SourceButton url={post.url} postType={post.type} /></div>
        <p className="mt-3 text-xs text-slate-600">{post.q} questions · {post.ask} requests · {post.sampled_comments ?? 0} comments sampled</p>
        <div className="neu-in mt-2 flex h-2.5 overflow-hidden rounded-full"><span className="bg-ink" style={{ width: `${100 * post.q / maxRank}%` }} /><span className="bg-sky" style={{ width: `${100 * post.ask / maxRank}%` }} /></div>
        {!!samples.filter((c) => c.kind === 'comment' && c.post_id === post.post_id).length && <details className="mt-3"><summary className="cursor-pointer text-xs font-semibold text-ink">Read sampled comments</summary><ul className="mt-3 space-y-3">{samples.filter((c) => c.kind === 'comment' && c.post_id === post.post_id).map((c) => <CommentCard key={c.id} sample={c} />)}</ul></details>}
      </li>)}</ul>
      {!ranking.length && <p className="text-sm text-slate-600">No posts match this search.</p>}
    </Well>
    <p className="mt-4 text-xs leading-relaxed text-slate-600">A comment can contain both a question and a request. The percentage counts distinct matching comments within the collected sample. It is not a sales conversion rate.</p>
  </section>
}
