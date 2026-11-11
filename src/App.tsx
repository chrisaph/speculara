import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from './api'
import { SentimentPanel, DemandPanel, EvidenceSources, SourceButton } from './components/AnalysisPanels'

type Key = 'predict' | 'recommend' | 'charts' | 'correlation' | 'sentiment' | 'demand'

const INK = '#29348f', SKY = '#38bdf8', CREAM = '#f9f5f1', WINE = '#8f2934'

const META: Record<Key, { q: string; title: string; tab: string }> = {
  predict: { q: 'What do you want to Predict?', title: 'Prediction', tab: 'Predict' },
  recommend: { q: 'What do you want to find recommendation of?', title: 'Recommendation', tab: 'Recommend' },
  charts: { q: 'What do you want to get charts of?', title: 'Charts', tab: 'Charts' },
  correlation: { q: 'What do you want to get correlation of?', title: 'Correlation', tab: 'Correlation' },
  sentiment: { q: 'What do you want to get sentiment of?', title: 'Sentiment', tab: 'Sentiment' },
  demand: { q: 'What do you want to get demand of?', title: 'Demand', tab: 'Demand' },
}
const ORDER = Object.keys(META) as Key[]

function hash(s: string) {
  let h = 2166136261
  for (const c of s) h = Math.imul(h ^ c.charCodeAt(0), 16777619)
  return () => ((h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0) / 4294967296)
}

/* Shared facts so every panel and the chatbot agree with each other */
const live = new Map<string, any>() // real backend results, keyed by seed

/* Panels pass seed + a suffix (metric, topic...), so match the longest live key that prefixes it */
function liveFor(seed: string) {
  let best: string | undefined
  for (const k of live.keys()) if (seed.startsWith(k) && (!best || k.length > best.length)) best = k
  return best ? live.get(best) : undefined
}

function facts(seed: string): ReturnType<typeof mockFacts> {
  return liveFor(seed)?.facts ?? mockFacts(seed)
}

function mockFacts(seed: string) {
  const r = hash(seed + 'facts')
  const pos = 52 + Math.round(r() * 28), neg = 4 + Math.round(r() * 12)
  const kw: [string, number, 'pos' | 'neg' | 'neu'][] = [
    ['love it', 0, 'pos'], ['quality', 0, 'pos'], ['where to buy', 0, 'neu'], ['price', 0, 'neg'], ['shipping', 0, 'neg'],
    ['restock', 0, 'neu'], ['amazing', 0, 'pos'], ['worth it', 0, 'pos'], ['scam', 0, 'neg'], ['tutorial', 0, 'neu'],
  ]
  const keywords = kw.map(([w, , s]) => ({ w, s, n: 30 + Math.round(r() * 220) })).sort((a, b) => b.n - a.n)
  const posts = ['Behind-the-scenes reel', 'Product drop carousel', 'Founder story video', 'Live Q&A replay', 'Giveaway photo post']
    .map((p) => ({ p, q: 20 + Math.round(r() * 160), ask: 15 + Math.round(r() * 120) })).sort((a, b) => b.q + b.ask - a.q - a.ask)
  const pairs = ([
    ['Recommended', 'Comments'], ['Comments', 'Views'], ['Likes', 'Saves'], ['Views', 'Sales'], ['Comments', 'Sales'], ['Saves', 'Sales'],
  ] as [string, string][]).map(([a, b]) => ({ a, b, v: +(0.25 + r() * 0.7).toFixed(2) })).sort((x, y) => y.v - x.v)
  return {
    weeks: 3 + Math.floor(r() * 9), phase: (['Rising', 'Peaking', 'Declining'] as const)[Math.floor(r() * 3)],
    acc: seed.startsWith('sample') ? 88 : 84 + Math.floor(r() * 8), pos, neg, neu: 100 - pos - neg,
    keywords, posts, pairs, growth: Math.round(4 + r() * 30), similar: 12 + Math.floor(r() * 30),
    counts: { Likes: 8000 + Math.round(r() * 20000), Dislikes: 100 + Math.round(r() * 700), Comments: 600 + Math.round(r() * 3000), Saves: 1000 + Math.round(r() * 6000), Sales: 80 + Math.round(r() * 900), Views: 90000 + Math.round(r() * 300000) },
  }
}

const Seed = createContext('sample')

/* ---------- primitives ---------- */
function Logo({ size = 36 }: { size?: number }) {
  const fills = [INK, SKY, INK, SKY, INK, SKY]
  return (
    <svg width={size} height={size} viewBox="-50 -50 100 100" aria-label="Speculara logo">
      <circle r="48" fill={CREAM} stroke={INK} strokeWidth="3" />
      {fills.map((f, i) => (
        <path key={i} transform={`rotate(${i * 60})`} d="M0 -44 L26 -38 L8 -2 Z" fill={f} stroke={CREAM} strokeWidth="1.5" />
      ))}
      <circle r="9" fill={CREAM} stroke={INK} strokeWidth="2" />
      <circle cx="-14" cy="-26" r="3" fill="#fff" opacity=".7" />
    </svg>
  )
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`neu rounded-3xl p-4 sm:p-6 ${className}`}>{children}</div>
}
const Well = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <div className={`neu-in rounded-2xl p-3 sm:p-4 ${className}`}>{children}</div>
)
const H = ({ children, sub }: { children: ReactNode; sub?: string }) => (
  <div className="mb-3">
    <h3 className="font-display text-lg font-bold text-ink">{children}</h3>
    {sub && <p className="text-xs text-slate-600">{sub}</p>}
  </div>
)

function Pills<T extends string>({ items, value, onChange }: { items: T[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="no-bar -mx-1 flex gap-3 overflow-x-auto p-2" role="tablist">
      {items.map((i) => (
        <button key={i} role="tab" aria-selected={i === value} onClick={() => onChange(i)}
          className={`min-h-10 whitespace-nowrap rounded-full px-4 py-2 text-sm transition focus-visible:outline-2 focus-visible:outline-sky ${i === value ? 'neu-in font-semibold text-ink' : 'neu-sm text-slate-600 hover:text-ink'}`}>
          {i}
        </button>
      ))}
    </div>
  )
}

function Query({ label, value, onChange, cta }: { label: string; value: string; onChange: (v: string) => void; cta: string }) {
  const [draft, setDraft] = useState(value)
  return (
    <form className="neu-in flex flex-col gap-2 rounded-2xl p-2 sm:flex-row sm:items-center sm:pl-4"
      onSubmit={(e) => { e.preventDefault(); onChange(draft.trim() || value) }}>
      <label className="shrink-0 px-2 pt-1 text-sm text-slate-600 sm:p-0">{label}</label>
      <input value={draft} onChange={(e) => setDraft(e.target.value)} className="min-h-10 min-w-0 flex-1 bg-transparent px-2 text-sm outline-none" />
      <button className="neu-btn min-h-11 rounded-xl px-5 py-2.5 text-sm font-medium text-white">{cta}</button>
    </form>
  )
}

const Explain = ({ children }: { children: ReactNode }) => (
  <div className="pt-5 text-sm">
    <p className="font-semibold text-ink">What this shows</p>
    <p className="mt-1 text-slate-600">{children}</p>
  </div>
)

const Stat = ({ l, v, c = INK }: { l: string; v: string | number; c?: string }) => (
  <div className="neu-in rounded-2xl p-3 text-center">
    <p className="font-display text-lg font-bold sm:text-xl" style={{ color: c }}>{v}</p>
    <p className="text-xs text-slate-600">{l}</p>
  </div>
)

/* diverging bar: left vs right share */
const Split = ({ l, r, lv, ll, rl }: { l: string; r?: string; lv: number; ll: string; rl: string }) => (
  <div className="mb-3">
    <div className="mb-1 flex justify-between text-xs text-slate-600"><span>{ll} {lv}%</span><span>{rl} {100 - lv}%</span></div>
    <div className="neu-in flex h-3 overflow-hidden rounded-full"><i style={{ width: `${lv}%`, background: l }} /><i style={{ width: `${100 - lv}%`, background: r ?? WINE }} /></div>
  </div>
)

/* Bar chart with axis, gridlines, value labels and optional average line */
function BarChart({ values, labels, max, fmt, avg, label }: { values: number[]; labels: string[]; max: number; fmt: (v: number) => string; avg?: boolean; label: string }) {
  const top = Math.max(...values), mean = values.reduce((a, b) => a + b, 0) / values.length
  const many = values.length > 8
  return (
    <div role="img" aria-label={`${label}. Highest ${labels[values.indexOf(top)]}: ${fmt(top)}`}>
      <div className="flex gap-2">
        <div className="flex h-44 flex-col justify-between pb-0 text-right text-[10px] leading-none text-slate-600">
          {[1, 0.75, 0.5, 0.25, 0].map((t) => <span key={t}>{fmt(max * t)}</span>)}
        </div>
        <div className="relative h-44 flex-1">
          {[0, 25, 50, 75, 100].map((t) => <div key={t} className="absolute inset-x-0 border-t border-slate-300/70" style={{ bottom: `${t}%` }} />)}
          <div className="absolute inset-0 flex items-end gap-1.5 sm:gap-2.5">
            {values.map((v, i) => (
              <div key={i} title={`${labels[i]}: ${fmt(v)}`} className="flex h-full flex-1 flex-col items-center justify-end">
                {(!many || v === top) && <span className="mb-1 text-[10px] font-semibold text-ink">{fmt(v)}</span>}
                <div className="w-full rounded-t-lg transition-all duration-500" style={{ height: `${(v / max) * 100}%`, background: v === top ? `linear-gradient(180deg,#3544ad,${INK})` : `linear-gradient(180deg,${SKY},#2a9fd8)`, boxShadow: '2px 2px 5px rgba(41,52,143,.25)' }} />
              </div>
            ))}
          </div>
          {avg && <div className="pointer-events-none absolute inset-x-0 border-t-2 border-dashed" style={{ bottom: `${(mean / max) * 100}%`, borderColor: WINE }}><span className="absolute -top-5 right-0 rounded bg-mist px-1 text-[10px] font-semibold text-wine">avg {fmt(mean)}</span></div>}
        </div>
      </div>
      <div className="mt-1.5 flex gap-2"><span className="w-8 shrink-0" /><div className="flex flex-1 gap-1.5 sm:gap-2.5">{labels.map((l, i) => <span key={i} className="flex-1 truncate text-center text-[10px] text-slate-600">{l}</span>)}</div></div>
    </div>
  )
}

/* ---------- Predict ---------- */
function Predict() {
  const seed = useContext(Seed)
  const [metric, setMetric] = useState('Views')
  const [notify, setNotify] = useState(false)
  const f = facts(seed + metric)
  const months = ['Jan 25', 'Mar 25', 'May 25', 'Jul 25', 'Sep 25', 'Nov 25', 'Jan 26', 'Mar 26']
  const data = useMemo(() => { const r = hash(seed + metric); let v = 5; return Array.from({ length: 16 }, () => (v += (r() - 0.45) * 0.6)) }, [metric, seed])
  const W = 640, H2 = 240, n = 22, sx = (i: number) => 40 + (i * (W - 60)) / (n - 1)
  const lo = 2, hi = 9, sy = (v: number) => 20 + (1 - (v - lo) / (hi - lo)) * (H2 - 50)
  const last = data[15]
  const fc = Array.from({ length: 6 }, (_, k) => last + (k + 1) * 0.04)
  // lifecycle curve for trend longevity
  const lf = facts(seed)
  const nowX = lf.phase === 'Rising' ? 30 : lf.phase === 'Peaking' ? 50 : 70
  const curve = (x: number) => 100 - 80 * Math.exp(-Math.pow((x - 50) / 22, 2))
  const cp = Array.from({ length: 41 }, (_, i) => `${i * 2.5},${curve(i * 2.5)}`).join(' ')
  const advice = lf.phase === 'Rising' ? 'Early. Publish soon to ride the climb.' : lf.phase === 'Peaking' ? 'At its peak. Post now, then prepare a follow-up.' : 'Past its peak. Move to a fresher trend soon.'
  return (
    <div className="space-y-5">
      <Card>
        <H sub="Forecast of your next posts with a confidence band.">Prediction</H>
        <Pills items={['Views', 'Saves', 'Likes', 'Comments', 'Sales']} value={metric} onChange={setMetric} />
        <Well className="mt-2">
          <svg viewBox={`0 0 ${W} ${H2}`} className="w-full" role="img" aria-label={`${metric} forecast chart`}>
            {[2, 4, 6, 8].map((t) => (<g key={t}><line x1="40" x2={W - 20} y1={sy(t)} y2={sy(t)} stroke="#d5dce6" /><text x="30" y={sy(t) + 4} fontSize="11" textAnchor="end" fill="#475569">{t}k</text></g>))}
            <polygon fill={SKY} opacity=".25" points={[...fc.map((v, k) => `${sx(15 + k)},${sy(v + 0.3 + k * 0.18)}`), ...fc.map((_, k) => `${sx(20 - k)},${sy(fc[5 - k] - 0.3 - (5 - k) * 0.18)}`)].join(' ')} />
            <polyline fill="none" stroke={SKY} strokeWidth="3" points={data.map((v, i) => `${sx(i)},${sy(v)}`).join(' ')} />
            <polyline fill="none" stroke={INK} strokeWidth="3" strokeDasharray="6 4" points={[last, ...fc].map((v, k) => `${sx(15 + k)},${sy(v)}`).join(' ')} />
            {data.map((v, i) => (<circle key={i} cx={sx(i)} cy={sy(v)} r="3.5" fill="#f1f5f9" stroke={SKY} strokeWidth="2" />))}
            <text x={sx(18)} y="14" fontSize="11" fill={INK} textAnchor="middle">Forecast</text>
            {months.map((m, i) => (<text key={m} x={sx(i * 3)} y={H2 - 8} fontSize="10" textAnchor="middle" fill="#475569">{m}</text>))}
          </svg>
        </Well>
        <p className="mt-4 text-center font-display text-3xl font-bold text-ink">Accuracy: {f.acc}%</p>
        <p className="text-center text-xs text-slate-600">Accuracy depends on amount of data and range of date</p>
        <div className="mt-4 flex justify-center">
          <button onClick={() => setNotify(!notify)} aria-pressed={notify}
            className={`min-h-11 rounded-full px-5 py-2.5 text-center text-sm transition ${notify ? 'neu-in font-medium text-wine' : 'neu-sm text-ink'}`}>
            {notify ? 'Reminder set for the forecast date' : 'Be notified when date reaches forecast to see if accurate?'}
          </button>
        </div>
        <p className="mt-5 text-sm text-slate-600">Want to know how we did this?</p>
        <a href="#docs" className="text-sm font-semibold text-ink underline decoration-sky underline-offset-4">Documentation</a>
      </Card>

      <Card>
        <H sub="How long a trend will last, from similar past trends plus current traffic and sentiment.">Trend longevity prediction</H>
        <div className="grid gap-4 md:grid-cols-2">
          <Well>
            <p className="text-xs font-semibold text-ink">Trend lifecycle</p>
            <svg viewBox="0 0 100 110" className="mt-2 w-full" role="img" aria-label={`Trend is ${lf.phase.toLowerCase()}`}>
              <polyline points={cp} fill="none" stroke={SKY} strokeWidth="2.5" />
              <line x1={nowX} x2={nowX} y1="10" y2="100" stroke={WINE} strokeDasharray="3 2" />
              <circle cx={nowX} cy={curve(nowX)} r="3.5" fill={WINE} />
              <text x={nowX} y="8" fontSize="6" textAnchor="middle" fill={WINE}>Now</text>
              <text x="5" y="108" fontSize="5" fill="#475569">Emerging</text><text x="50" y="108" fontSize="5" textAnchor="middle" fill="#475569">Peak</text><text x="95" y="108" fontSize="5" textAnchor="end" fill="#475569">Fading</text>
            </svg>
          </Well>
          <div className="space-y-3">
            <div className="neu-in rounded-2xl p-4 text-center">
              <p className="text-xs text-slate-600">Estimated time left</p>
              <p className="font-display text-4xl font-bold text-ink">~{lf.weeks} weeks</p>
              <p className="text-xs text-slate-600">Range {Math.max(1, lf.weeks - 2)} to {lf.weeks + 3} weeks, phase: <b style={{ color: lf.phase === 'Declining' ? WINE : INK }}>{lf.phase}</b></p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Stat l="Similar trends" v={lf.similar} />
              <Stat l="Traffic / wk" v={`${lf.phase === 'Declining' ? '-' : '+'}${lf.growth}%`} c={lf.phase === 'Declining' ? WINE : INK} />
              <Stat l="Sentiment" v={`${lf.pos}%`} />
            </div>
            <p className="text-sm text-ink">{advice}</p>
          </div>
        </div>
        <Explain>We match the trend to similar past ones, then adjust by today's traffic and audience sentiment, both drawn from historical scraping of social media as a whole.</Explain>
      </Card>
    </div>
  )
}

/* ---------- Recommend ---------- */
function Recommend() {
  const seed = useContext(Seed)
  const [item, setItem] = useState('Item A')
  const [mode, setMode] = useState('Similar items')
  const rows = useMemo(() => {
    const r = hash(seed + item + mode)
    const notes: Record<string, string> = { 'Similar items': 'Often chosen together', 'Bought together': 'Same basket', Trending: 'Rising this week' }
    return ['Item B', 'Item C', 'Item D', 'Item E'].map((n, i) => ({ n, note: notes[mode], s: Math.round(96 - i * 8 - r() * 6) }))
  }, [item, mode, seed])
  const plays = [
    { t: 'Open with a 3-second hook', why: 'Short-form feeds reward posts people watch past the first seconds.', tag: 'High impact', lift: '+18%' },
    { t: 'Reply to comments in the first hour', why: 'Early conversation signals a post is worth showing to more people.', tag: 'Quick win', lift: '+11%' },
    { t: 'Turn top questions into a follow-up post', why: 'Content that answers real demand earns saves and shares.', tag: 'High impact', lift: '+14%' },
    { t: 'Partner with a mid-size creator', why: 'Borrowed audiences push brands into new recommendation circles.', tag: 'Longer term', lift: '+9%' },
  ]
  return (
    <div className="space-y-5">
      <Card>
        <H sub="Ranks next ideas by how close they sit to past winners.">Find recommendation of</H>
        <Query label="Find recommendations of" value={item} onChange={setItem} cta="Find" />
        <Pills items={['Similar items', 'Bought together', 'Trending']} value={mode} onChange={setMode} />
        <ul className="mt-2 space-y-1">
          {rows.map((r, i) => (
            <li key={r.n} className="flex flex-wrap items-center gap-3 py-2">
              <span className="neu-sm grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-semibold text-ink">{i + 1}</span>
              <div className="w-28 sm:w-40"><p className="text-sm font-medium">{r.n}</p><p className="text-xs text-slate-600">{r.note}</p></div>
              <div className="neu-in h-3 min-w-24 flex-1 rounded-full"><div className="h-3 rounded-full bg-ink" style={{ width: `${r.s}%`, opacity: 1 - i * 0.18 }} /></div>
              <span className="w-10 text-right text-sm text-slate-700">{r.s}%</span>
            </li>
          ))}
        </ul>
      </Card>
      <Card>
        <H sub="What to do next, drawn from how brands earn reach on each platform.">Next action and brand strategy</H>
        <ol className="space-y-3">
          {plays.map((p, i) => (
            <li key={p.t} className="neu-in flex gap-3 rounded-2xl p-3 sm:p-4">
              <span className="neu-sm grid h-9 w-9 shrink-0 place-items-center rounded-full font-display text-sm font-bold text-ink">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold text-ink">{p.t}</p>
                  <span className="text-xs font-semibold" style={{ color: p.tag === 'Quick win' ? WINE : INK }}>{p.tag} / {p.lift} reach</span></div>
                <p className="mt-1 text-sm text-slate-600">{p.why}</p>
              </div>
            </li>
          ))}
        </ol>
        <Explain>An AI model trained on how people grow brands and work with platform algorithms turns your results into a ranked to-do list. Lift figures are estimates.</Explain>
      </Card>
    </div>
  )
}

/* ---------- Charts ---------- */
function Charts() {
  const seed = useContext(Seed)
  const [item, setItem] = useState('Item A')
  const [metric, setMetric] = useState('Views')
  const [by, setBy] = useState('By month')
  const f = facts(seed + metric)
  const lc = liveFor(seed)?.charts?.[metric.toLowerCase()]
  const liveSeries: { label: string; value: number }[] | undefined = lc?.[by === 'By week' ? 'week' : 'month']?.slice(-12)
  const liveShare: { type: string; pct: number }[] | undefined = liveFor(seed)?.charts?.post_type_share
  const { bars, labels, parts, line } = useMemo(() => {
    if (liveSeries?.length) {
      const vals = liveSeries.map((x) => x.value), mx = Math.max(...vals, 1)
      const shares = (liveShare ?? []).slice(0, 3).map((x) => x.pct / 100)
      return { bars: vals.map((v) => (v / mx) * 100), labels: liveSeries.map((x) => x.label.slice(by === 'By week' ? 5 : 2)), parts: shares.length ? shares : [1], line: vals.map((v) => 15 + (v / mx) * 80) }
    }
    const r = hash(seed + item + by + metric)
    const labels = by === 'By month' ? ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'] : by === 'By category' ? ['Cat A', 'Cat B', 'Cat C', 'Cat D'] : ['North', 'South', 'East', 'West', 'Central']
    const bars = labels.map(() => 40 + r() * 60)
    const p = [0.3 + r() * 0.3, 0.2 + r() * 0.2]; p.push(1 - p[0] - p[1])
    let v = 40; const line = Array.from({ length: 12 }, () => (v = Math.min(95, Math.max(15, v + (r() - 0.4) * 22))))
    return { bars, labels, parts: p, line }
  }, [item, by, metric, seed, liveSeries, liveShare])
  const cols = [INK, SKY, '#a5b4d8']; let acc = 0
  const c = f.counts
  const total = (c as Record<string, number>)[metric]
  const unit = liveSeries?.length ? Math.max(10, Math.ceil(Math.max(...liveSeries.map((x) => x.value), 1) * 1.1)) : Math.ceil((total / (by === 'By month' ? 8 : 3)) / 100) * 100
  const nf = (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : `${Math.round(v)}`)
  return (
    <Card>
      <H sub="Trends, stats, views, likes and more, auto-charted.">Get charts of</H>
      <Query label="Get charts of" value={item} onChange={setItem} cta="Get charts" />
      <Pills items={['Views', 'Likes', 'Saves', 'Comments', 'Sales']} value={metric} onChange={setMetric} />
      <Pills items={liveSeries ? ['By month', 'By week'] : ['By month', 'By category', 'By region']} value={liveSeries && by !== 'By month' && by !== 'By week' ? 'By month' : by} onChange={setBy} />
      <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat l="Views" v={c.Views.toLocaleString()} /><Stat l="Likes" v={c.Likes.toLocaleString()} /><Stat l="Saves" v={c.Saves.toLocaleString()} /><Stat l="Sales" v={c.Sales.toLocaleString()} c={WINE} />
      </div>
      <Well className="mt-4">
        <p className="text-xs font-semibold text-ink">{metric} trend, last 12 periods</p>
        <svg viewBox="0 0 120 50" className="mt-2 w-full" role="img" aria-label={`${metric} trend line`}>
          <polyline fill="none" stroke={SKY} strokeWidth="1.5" points={line.map((v, i) => `${5 + i * 10},${48 - v / 2.2}`).join(' ')} />
          {line.map((v, i) => <circle key={i} cx={5 + i * 10} cy={48 - v / 2.2} r="1.4" fill={INK} />)}
        </svg>
      </Well>
      <div className="mt-4 grid gap-4 md:grid-cols-[1.6fr_1fr]">
        <Well>
          <p className="text-xs font-semibold text-ink">{metric} {by.toLowerCase()}</p>
          <div className="mt-4"><BarChart values={bars.map((b) => (b / 100) * unit)} labels={labels} max={unit} fmt={nf} label={`${metric} ${by.toLowerCase()}`} /></div>
        </Well>
        <Well>
          <p className="text-xs font-semibold text-ink">Share by category</p>
          <div className="mt-3 flex items-center gap-4">
            <svg viewBox="0 0 36 36" className="h-28 w-28 shrink-0 -rotate-90" role="img" aria-label="Share by category">
              {parts.map((p, i) => { const d = p * 100; const el = <circle key={i} cx="18" cy="18" r="14" fill="none" stroke={cols[i]} strokeWidth="6" strokeDasharray={`${d * 0.88} 88`} strokeDashoffset={-acc * 0.88} />; acc += d; return el })}
            </svg>
            <ul className="space-y-1 text-xs text-slate-700">{parts.map((p, i) => (<li key={i} className="flex items-center gap-2"><i className="h-2.5 w-2.5 rounded-full" style={{ background: cols[i] }} />{liveShare?.[i]?.type ?? `Category ${'ABC'[i]}`}: {Math.round(p * 100)}%</li>))}</ul>
          </div>
        </Well>
      </div>
      <Explain>Turns your data into charts: a trend line over time, a comparison of periods or groups, and how the total splits.</Explain>
    </Card>
  )
}

/* ---------- Correlation ---------- */
function Correlation() {
  const seed = useContext(Seed)
  const [v, setV] = useState('Your page')
  const [mode, setMode] = useState('All pairs')
  const vars = ['Views', 'Likes', 'Saves', 'Comments', 'Sales', 'Recommended']
  const f = facts(seed + v)
  const m = useMemo(() => {
    const r = hash(seed + v)
    const g = vars.map(() => vars.map(() => 0))
    vars.forEach((_, i) => vars.forEach((_, j) => { if (i === j) g[i][j] = 1; else if (i < j) { g[i][j] = +(r() * 1.6 - 0.35).toFixed(2); g[j][i] = g[i][j] } }))
    return g
  }, [v, seed])
  const show = (x: number) => mode === 'All pairs' || (mode === 'Strong only' ? Math.abs(x) >= 0.5 : x < 0)
  const pts = useMemo(() => { const r = hash(seed + v + 'p'); return Array.from({ length: 10 }, (_, i) => [i * 9 + 5, 85 - i * 7 + (r() - 0.5) * 18]) }, [v, seed])
  const label = (r: number) => (r > 0.7 ? 'Strong' : r > 0.45 ? 'Moderate' : 'Weak')
  return (
    <Card>
      <H sub="See how strongly each measure moves with the others (-1 to +1).">Get correlation of</H>
      <Query label="Get correlation of" value={v} onChange={setV} cta="Get correlation" />
      <Pills items={['All pairs', 'Strong only', 'Negative only']} value={mode} onChange={setMode} />
      <Well className="mt-2">
        <p className="mb-3 text-xs font-semibold text-ink">Key relationships</p>
        <ul className="space-y-3">
          {f.pairs.map((p) => (
            <li key={p.a + p.b}>
              <div className="mb-1 flex justify-between gap-2 text-sm"><span>{p.a} <span className="text-slate-500">to</span> {p.b}</span><span className="font-semibold text-ink">{p.v} <span className="text-xs font-normal text-slate-600">{label(p.v)}</span></span></div>
              <div className="neu-in h-2.5 rounded-full"><div className="h-2.5 rounded-full" style={{ width: `${p.v * 100}%`, background: `linear-gradient(90deg,${SKY},${INK})` }} /></div>
            </li>
          ))}
        </ul>
      </Well>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Well>
          <p className="mb-2 text-xs font-semibold text-ink">Correlation matrix</p>
          <div className="grid grid-cols-[auto_repeat(6,1fr)] gap-1 text-[9px] sm:text-[10px]">
            <span />{vars.map((x) => <span key={x} className="truncate text-center text-slate-600" title={x}>{x.slice(0, 4)}</span>)}
            {m.map((row, i) => [<span key={'l' + i} className="self-center pr-1 text-slate-600">{vars[i].slice(0, 4)}</span>, ...row.map((x, j) => (
              <div key={`${i}${j}`} title={`${vars[i]} / ${vars[j]}: ${x}`} className="grid aspect-square place-items-center rounded"
                style={{ background: show(x) ? (x >= 0 ? `rgba(41,52,143,${0.12 + x * 0.85})` : `rgba(143,41,52,${0.12 - x * 0.85})`) : 'transparent', color: show(x) && Math.abs(x) > 0.5 ? '#fff' : '#334155' }}>{show(x) ? x.toFixed(1) : ''}</div>))])}
          </div>
          <div className="mt-2 h-2 rounded-full" style={{ background: `linear-gradient(90deg, ${WINE}, ${CREAM}, ${INK})` }} />
        </Well>
        <Well>
          <p className="mb-2 text-xs font-semibold text-ink">Comments vs views, per trend</p>
          <svg viewBox="0 0 100 100" className="w-full" role="img" aria-label="Scatter plot"><line x1="5" y1="95" x2="95" y2="95" stroke="#94a3b8" /><line x1="5" y1="5" x2="5" y2="95" stroke="#94a3b8" />
            {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="2.5" fill="#f1f5f9" stroke={SKY} strokeWidth="1.5" />)}
            <line x1="5" y1="88" x2="95" y2="22" stroke={INK} strokeDasharray="3 2" /></svg>
        </Well>
      </div>
      <Explain>Shows which measures rise and fall together, such as being recommended and getting comments, or comments and views within one trend. It shows association, not proof of cause.</Explain>
    </Card>
  )
}

/* ---------- Sentiment ---------- */
function Sentiment() {
  const seed = useContext(Seed)
  return <SentimentPanel analysis={liveFor(seed)} />
}

function Demand() {
  const seed = useContext(Seed)
  return <DemandPanel analysis={liveFor(seed)} />
}

const VIEWS: Record<Key, () => ReactNode> = { predict: Predict, recommend: Recommend, charts: Charts, correlation: Correlation, sentiment: Sentiment, demand: Demand }

/* ---------- Chatbot ---------- */
function Chat({ picked }: { picked: Key | null }) {
  const seed = useContext(Seed)
  const analysis = liveFor(seed)
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  type Message = { me: boolean; t: string; sources?: { id: string; title: string; url: string; kind: string }[]; engine?: string }
  const greeting: Message = { me: false, t: 'Ask me about the posts, collected comments, demand, sentiment, or other analysis outputs. I can cite their sources.' }
  const [msgs, setMsgs] = useState<Message[]>([greeting])
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { setMsgs([greeting]) }, [seed])
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [msgs, open, sending])
  const send = async (question: string) => {
    const message = question.trim()
    if (!message || sending) return
    setMsgs((messages) => [...messages, { me: true, t: message }]); setText(''); setSending(true)
    try {
      if (!analysis) {
        setMsgs((messages) => [...messages, { me: false, t: 'Analyze a profile or choose Try with sample data first, so I can read its results.' }])
        return
      }
      const response = await api<{ answer: string; sources?: Message['sources']; engine?: string }>('/api/chat', {
        message, analysis_id: analysis.analysis_id, analysis, facts: analysis.facts,
      }, { timeoutMs: 60000 })
      setMsgs((messages) => [...messages, { me: false, t: response.answer, sources: response.sources, engine: response.engine }])
    } catch (error) {
      setMsgs((messages) => [...messages, { me: false, t: `I couldn't finish reading the analysis: ${(error as Error).message}`, engine: 'unavailable' }])
    } finally { setSending(false) }
  }
  return (
    <div className="fixed bottom-4 right-4 z-30 flex flex-col items-end gap-3">
      {open && (
        <div role="dialog" aria-label="Ask about your analysis" className="neu flex h-[min(34rem,80vh)] w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-3xl sm:w-96">
          <div className="flex items-center justify-between px-4 py-3"><div><p className="font-display font-bold text-ink">Ask Speculara</p><p className="mt-1 text-[11px] text-slate-600">{analysis ? `Reading ${analysis.post_count ?? 0} posts ? ${analysis.evidence?.comments?.length ?? 0} comment samples` : 'Connect an analysis to get started'}{picked ? ` ? ${META[picked].title}` : ''}</p></div>
            <button onClick={() => setOpen(false)} aria-label="Close chat" className="neu-sm grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink">&times;</button></div>
          <div className="neu-in neu-scroll mx-3 flex-1 space-y-3 overflow-y-auto rounded-2xl p-3 text-sm" aria-live="polite">
            {msgs.map((message, index) => <div key={index} className={`max-w-[95%] rounded-2xl px-3 py-3 ${message.me ? 'ml-auto bg-ink text-white' : 'neu-sm text-slate-800'}`}>
              <p className="whitespace-pre-wrap break-words leading-relaxed">{message.t}</p>
              {!!message.sources?.length && <div className="mt-3 flex flex-wrap gap-2">{message.sources.map((source) => <SourceButton key={source.id} url={source.url} kind={source.kind} label={`Source ${source.id}`} />)}</div>}
              {message.engine && <p className="mt-2 text-[10px] text-slate-500">{message.engine === 'gemma' ? 'Gemma ? using this analysis' : message.engine === 'fallback' ? 'Local data summary ? Gemma unavailable' : 'Could not reach the analysis service'}</p>}
            </div>)}
            {sending && <p role="status" className="neu-sm rounded-2xl p-3 text-xs text-ink">Reading your analysis and collected evidence?</p>}
            <div ref={end} />
          </div>
          <div className="no-bar flex gap-2 overflow-x-auto px-3 pt-3">
            {['What does demand show?', 'Explain the sentiment', 'Which reel has the most questions?'].map((question) => <button key={question} disabled={sending} onClick={() => void send(question)} className="neu-sm min-h-9 shrink-0 rounded-full px-3 py-1.5 text-xs text-ink disabled:opacity-50">{question}</button>)}
          </div>
          <form onSubmit={(event) => { event.preventDefault(); void send(text) }} className="flex gap-2 p-3">
            <input value={text} onChange={(event) => setText(event.target.value)} placeholder="Ask about your results" aria-label="Your question" className="neu-in min-h-11 min-w-0 flex-1 rounded-xl bg-transparent px-3 text-sm outline-none" />
            <button disabled={sending || !text.trim()} className="neu-btn min-h-11 rounded-xl px-4 text-sm text-white disabled:opacity-50">Send</button>
          </form>
        </div>
      )}
      <button onClick={() => setOpen(!open)} aria-label={open ? 'Close chat' : 'Open chat'} aria-expanded={open} className="neu-btn grid h-14 w-14 place-items-center rounded-full text-white">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a8 8 0 0 1-11.5 7.2L4 20l1-4.5A8 8 0 1 1 21 12z" /></svg>
      </button>
    </div>
  )
}

const MARKETS = ['Marketing Teams', 'Advertisement Agencies', 'Public Relations (PR) Agencies', 'Brand Strategists', 'Market Research Analysts']

/* ---------- App ---------- */
export default function App() {
  const [picked, setPicked] = useState<Key | null>(null)
  const [tab, setTab] = useState<Key | null>(null)
  const [url, setUrl] = useState('')
  const [err, setErr] = useState('')
  const [source, setSource] = useState<{ seed: string; label: string } | null>(null)
  const [nudge, setNudge] = useState(false)
  const [busyAction, setBusyAction] = useState<'' | 'analyze' | 'sample' | 'login' | 'finish' | 'cancel'>('')
  const busy = busyAction !== ''
  const [elapsed, setElapsed] = useState(0)
  const [progress, setProgress] = useState('Checking saved results…')
  const [loginOpen, setLoginOpen] = useState(false)
  const [collectorBusy, setCollectorBusy] = useState(false)
  const analysisController = useRef<AbortController | null>(null)
  const [loginNetwork, setLoginNetwork] = useState('instagram')
  const [loginMessage, setLoginMessage] = useState('')
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let alive = true
    const check = async () => {
      try {
        const status = await api('/api/collector/status', undefined, { timeoutMs: 5000 })
        if (!alive) return
        setLoginOpen(status.login_open); setCollectorBusy(status.busy)
        if (busyAction === 'analyze') setProgress(status.login_open ? 'Finish signing in using the button below.' : status.busy ? status.progress : 'Preparing results…')
      } catch { /* The main request reports connection failures. */ }
    }
    void check()
    const timer = busy || loginOpen || collectorBusy ? setInterval(() => { void check() }, 2000) : undefined
    return () => { alive = false; clearInterval(timer) }
  }, [busyAction, loginOpen, collectorBusy])

  useEffect(() => {
    if (!busy) return
    setElapsed(0)
    const timer = setInterval(() => setElapsed((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [busyAction])

  const connect = (seed: string, label: string) => {
    setSource({ seed, label }); setPicked(null); setTab(null); setErr(''); setNudge(true)
    listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTimeout(() => setNudge(false), 3500)
  }
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const raw = url.trim()
    if (!raw) return setErr('Paste the link to your social media page first.')
    let u: URL
    try {
      u = new URL(/^https?:\/\//i.test(raw) ? raw : `https://${raw}`)
      if (!u.hostname.includes('.')) throw new Error()
    } catch { return setErr('That does not look like a valid link. Try something like instagram.com/yourbrand') }
    const seed = u.hostname + u.pathname
    const controller = new AbortController()
    analysisController.current = controller
    setBusyAction('analyze'); setErr(''); setProgress('Checking collector…')
    try {
      const status = await api('/api/collector/status', undefined, { timeoutMs: 5000, signal: controller.signal })
      if (status.login_open) {
        setLoginOpen(true)
        throw new Error('Sign-in is still open. Click Done signing in below, then Analyze.')
      }
      live.set(seed, await api('/api/analyze', { url: raw }, { timeoutMs: 240000, signal: controller.signal }))
      connect(seed, u.hostname.replace(/^www\./, '') + (u.pathname.length > 1 ? u.pathname : ''))
    } catch (ex) {
      setErr(ex instanceof TypeError ? 'Cannot reach the analysis service. Check your connection and try again.' : (ex as Error).message)
    } finally { analysisController.current = null; setBusyAction((action) => action === 'analyze' ? '' : action) }
  }
  const trySample = async () => {
    setBusyAction('sample')
    try { live.set('sample', await api('/api/sample')) } catch { live.delete('sample') } // falls back to built-in demo numbers
    setBusyAction(''); connect('sample', 'sample data')
  }
  const signIn = async () => {
    setBusyAction('login'); setErr(''); setLoginMessage('')
    try {
      const response = await api('/api/collector/login', { network: loginNetwork })
      setLoginMessage(response.message)
      setLoginOpen(true)
    } catch (ex) {
      setErr(ex instanceof TypeError ? 'Cannot reach the local collector. Start the backend and try again.' : (ex as Error).message)
    } finally { setBusyAction((action) => action === 'login' ? '' : action) }
  }
  const finishSignIn = async () => {
    analysisController.current?.abort()
    setBusyAction('finish'); setErr('')
    try {
      const response = await api('/api/collector/login/finish', {}, { timeoutMs: 25000 })
      setLoginOpen(false); setCollectorBusy(false); setLoginMessage(response.message)
    } catch (ex) { setErr((ex as Error).message) }
    finally { setBusyAction('') }
  }
  const cancelAnalysis = async () => {
    setBusyAction('cancel')
    try {
      await api('/api/collector/cancel', {}, { timeoutMs: 25000 })
      setCollectorBusy(false); setErr('Analysis cancelled.')
    } catch (ex) { setErr((ex as Error).message) }
    finally { analysisController.current?.abort(); setBusyAction('') }
  }

  const others = ORDER.filter((k) => k !== picked)
  const active = tab && tab !== picked ? tab : others[0]
  const Primary = picked ? VIEWS[picked] : null
  const Secondary = VIEWS[active]
  const colors = [INK, WINE, INK, WINE, INK, WINE]
  const locked = !source
  const researchSources: { title: string; url: string }[] = source ? (live.get(source.seed)?.profile?.sources ?? []) : []
  const dataNotes: string = source ? (live.get(source.seed)?.profile?.notes ?? '') : ''

  return (
    <Seed.Provider value={source?.seed ?? 'sample'}>
      <div className="min-h-screen pb-24">
        <header className="sticky top-0 z-20 bg-mist/90 px-3 pt-3 backdrop-blur">
          <div className="neu mx-auto flex max-w-5xl items-center gap-3 rounded-2xl px-4 py-2.5 sm:px-5">
            <span className="neu-sm grid h-11 w-11 shrink-0 place-items-center rounded-full"><Logo size={32} /></span>
            <span className="font-display text-xl font-bold tracking-tight text-ink">Speculara</span>
            <span className="ml-auto hidden text-xs text-slate-600 md:block">Social media analysis for marketing teams</span>
          </div>
        </header>

        <main className="mx-auto max-w-5xl px-4 sm:px-5">
          <section className="grid items-center gap-8 py-8 md:grid-cols-[1fr_1.1fr] md:py-10">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-wine">Ad performance, in focus</p>
              <h1 className="mt-2 font-display text-3xl font-bold leading-tight text-ink md:text-4xl">Turn scattered numbers into your next ad decision.</h1>
              <p className="mt-3 max-w-md text-slate-700">Paste your page link, then pick a question. Speculara predicts, recommends, charts, correlates and reads sentiment and demand across your posts.</p>
            </div>

            <div ref={listRef} className={`neu rounded-[2rem] p-4 transition ${nudge ? 'ring-2 ring-sky' : ''}`}>
              <p className="px-2 pt-1 text-xs font-semibold uppercase tracking-widest text-slate-600">Scroll and choose</p>
              {nudge && <p role="status" className="mx-2 mt-2 rounded-xl bg-sky/20 px-3 py-2 text-sm font-medium text-ink">Connected to {source?.label}. Now scroll and choose a question.</p>}
              <div className="relative">
                <ul className={`neu-scroll mt-2 h-64 snap-y snap-mandatory overflow-y-scroll px-2 py-1 sm:h-72 ${locked ? 'opacity-50' : ''}`} aria-label="Questions">
                  {ORDER.map((k, i) => (
                    <li key={k} className="snap-center">
                      <button disabled={locked} onClick={() => { setPicked(k); setTab(null); setTimeout(() => document.getElementById('result')?.scrollIntoView({ behavior: 'smooth' }), 50) }}
                        className={`my-2 block min-h-14 w-full rounded-2xl px-4 py-4 text-center font-display text-base font-semibold leading-snug transition focus-visible:outline-2 focus-visible:outline-sky sm:text-lg ${picked === k ? 'neu-in' : 'neu-sm enabled:hover:-translate-y-0.5'}`} style={{ color: colors[i] }}>
                        {META[k].q}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <form onSubmit={submit} className="mt-3 px-1" noValidate>
                <label htmlFor="url" className="mb-1 block px-1 text-xs font-medium text-slate-700">Your social media page link</label>
                <div className="neu-in flex flex-col gap-2 rounded-2xl p-2 sm:flex-row">
                  <input id="url" value={url} onChange={(e) => { setUrl(e.target.value); setErr('') }} inputMode="url" autoComplete="url" placeholder="instagram.com/yourbrand"
                    aria-invalid={!!err} aria-describedby="url-msg" className="min-h-11 min-w-0 flex-1 bg-transparent px-3 text-sm outline-none" />
                  <button disabled={busy} className="neu-btn min-h-11 rounded-xl px-5 text-sm font-medium text-white disabled:opacity-60">{busyAction === 'analyze' ? 'Collecting…' : busy ? 'Please wait…' : 'Analyze'}</button>
                </div>
                <p id="url-msg" className="min-h-5 px-1 pt-1 text-xs text-wine" role="alert">{err}</p>
                {busyAction === 'analyze' && <p role="status" className="px-1 pb-2 text-sm text-ink">{progress} · {elapsed}s elapsed. Reading comments can take up to 3 minutes.</p>}
                {(busyAction === 'analyze' || (collectorBusy && !loginOpen)) && <button type="button" onClick={cancelAnalysis} disabled={busyAction === 'cancel'} className="mb-2 min-h-10 px-2 text-sm font-semibold text-wine underline">Cancel collection</button>}
                <div className="flex items-center gap-3 px-1">
                  <span className="h-px flex-1 bg-slate-300" /><span className="text-xs text-slate-600">or</span><span className="h-px flex-1 bg-slate-300" />
                </div>
                <button type="button" disabled={busy} onClick={trySample} className="neu-sm mt-3 min-h-11 w-full rounded-xl text-sm font-semibold text-ink transition hover:text-wine">Try with sample data</button>
              </form>
              <div className="mt-4 border-t border-slate-300 px-2 pt-3 text-xs text-slate-700">
                <p>SocialMonitor collects Instagram, Facebook and TikTok posts. Collection may take a few minutes.</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <select aria-label="Network to sign in to" value={loginNetwork} onChange={(e) => setLoginNetwork(e.target.value)} className="neu-in min-h-10 rounded-lg px-2">
                    <option value="instagram">Instagram</option><option value="facebook">Facebook</option>
                  </select>
                  <button type="button" disabled={busy} onClick={signIn} className="neu-sm min-h-10 rounded-lg px-3 font-semibold text-ink disabled:opacity-50">Sign in for comments</button>
                  {loginOpen && <button type="button" onClick={finishSignIn} disabled={busyAction === 'finish'} className="neu-btn min-h-10 rounded-lg px-3 font-semibold text-white">{busyAction === 'finish' ? 'Closing…' : 'Done signing in'}</button>}
                </div>
                <p className="mt-2">Instagram comment text and Facebook collection require sign-in. Sign in in the separate browser window, then click Done signing in here. TikTok uses public pages.</p>
                {loginMessage && <p role="status" className="mt-2 font-semibold text-ink">{loginMessage}</p>}
              </div>
              {locked && <p className="mt-2 px-2 text-center text-xs text-slate-600">Add your page link or try sample data to unlock the questions.</p>}
            </div>
          </section>

          <div id="result" className="scroll-mt-24">
            {dataNotes && <p className="mb-4 rounded-xl bg-sky/10 p-3 text-sm text-slate-700">{dataNotes}</p>}
            {source && live.get(source.seed)?.evidence ? <EvidenceSources analysis={live.get(source.seed)} /> : researchSources.length > 0 && (
              <p className="mb-4 flex flex-wrap gap-x-3 gap-y-1 text-sm text-slate-700">
                <span className="font-semibold">Research sources:</span>
                {researchSources.map((item) => (
                  <a key={item.url} href={item.url} target="_blank" rel="noopener noreferrer" className="text-ink underline hover:text-wine">{item.title}</a>
                ))}
              </p>
            )}
            {Primary ? (
              <>
                <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2"><h2 className="font-display text-2xl font-bold text-ink sm:text-3xl">{META[picked!].title}</h2><span className="text-xs text-slate-600">Source: {source?.label}</span></div>
                <Primary />
                <div className="mt-10">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-600">Explore the others</p>
                  <div className="no-bar mb-3 flex gap-3 overflow-x-auto p-2" role="tablist">
                    {others.map((k) => (
                      <button key={k} role="tab" aria-selected={k === active} onClick={() => setTab(k)}
                        className={`min-h-11 whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-sky ${k === active ? 'neu-in font-semibold text-ink' : 'neu-sm text-slate-600 hover:text-ink'}`}>
                        {META[k].tab}
                      </button>
                    ))}
                  </div>
                  <Secondary />
                </div>
              </>
            ) : (
              <div className="neu-in rounded-3xl p-8 text-center text-slate-600">{locked ? 'Your results will appear here once you add a page link or try the sample data.' : 'Choose a question above to see your first result here.'}</div>
            )}
          </div>

          <section className="mt-14">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-600">Built for</p>
            <ul className="flex flex-wrap gap-3">{MARKETS.map((m) => <li key={m} className="neu-sm rounded-full px-4 py-2 text-sm font-medium text-ink">{m}</li>)}</ul>
          </section>

          <footer id="docs" className="neu mt-10 scroll-mt-24 rounded-3xl p-5 text-sm text-slate-700 sm:p-6">
            <p className="font-semibold text-ink">Documentation</p>
            <p className="mt-1">Forecasts use past posts with a confidence band; accuracy depends on the amount of data and date range. Trend longevity compares your trend with similar past trends using traffic and sentiment gathered from social media as a whole. Correlation shows association, not proof of cause. Sample mode uses demo data. Live results depend on the posts collected; data notes identify unavailable metrics.</p>
          </footer>
        </main>
        <Chat picked={picked} />
      </div>
    </Seed.Provider>
  )
}
