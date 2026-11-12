import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { api } from './api'
import { PredictPanel, RecommendPanel, ChartsPanel, CorrelationPanel } from './components/InsightPanels'
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

const live = new Map<string, any>()
const liveFor = (seed: string) => live.get(seed)
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

function Predict() { return <PredictPanel analysis={liveFor(useContext(Seed))} /> }
function Recommend() { return <RecommendPanel analysis={liveFor(useContext(Seed))} /> }
function Charts() { return <ChartsPanel analysis={liveFor(useContext(Seed))} /> }
function Correlation() { return <CorrelationPanel analysis={liveFor(useContext(Seed))} /> }

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
          <div className="flex items-center justify-between px-4 py-3"><div><p className="font-display font-bold text-ink">Ask Speculara</p><p className="mt-1 text-[11px] text-slate-600">{analysis ? `Reading ${analysis.post_count ?? 0} posts · ${analysis.evidence?.comments?.length ?? 0} comment samples` : 'Connect an analysis to get started'}{picked ? ` · ${META[picked].title}` : ''}</p></div>
            <button onClick={() => setOpen(false)} aria-label="Close chat" className="neu-sm grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink">&times;</button></div>
          <div className="neu-in neu-scroll mx-3 flex-1 space-y-3 overflow-y-auto rounded-2xl p-3 text-sm" aria-live="polite">
            {msgs.map((message, index) => <div key={index} className={`max-w-[95%] rounded-2xl px-3 py-3 ${message.me ? 'ml-auto bg-ink text-white' : 'neu-sm text-slate-800'}`}>
              <p className="whitespace-pre-wrap break-words leading-relaxed">{message.t}</p>
              {!!message.sources?.length && <div className="mt-3 flex flex-wrap gap-2">{message.sources.map((source) => <SourceButton key={source.id} url={source.url} kind={source.kind} label={`Source ${source.id}`} />)}</div>}
              {message.engine && <p className="mt-2 text-[10px] text-slate-500">{message.engine === 'gemma' ? 'Gemma · using this analysis' : message.engine === 'fallback' ? 'Local data summary · Gemma unavailable' : 'Could not reach the analysis service'}</p>}
            </div>)}
            {sending && <p role="status" className="neu-sm rounded-2xl p-3 text-xs text-ink">Reading your analysis and collected evidence…</p>}
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
    setErr('')
    try { live.set('sample', await api('/api/sample')); connect('sample', 'sample data') }
    catch (ex) { setErr(`Could not load sample data: ${(ex as Error).message}`) }
    finally { setBusyAction('') }
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
                <Primary key={source?.seed} />
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
                  <Secondary key={source?.seed} />
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
            <p className="mt-1">Forecasts use past posts with a confidence band; accuracy depends on the amount of data and date range. Trend longevity compares observed four-week patterns within the collected profile; its evidence dialog lists the matching dates and posts. No account-wide or global dataset is implied. Correlation shows association, not proof of cause. Sample mode uses demo data. Live results depend on the posts collected; data notes identify unavailable metrics.</p>
          </footer>
        </main>
        <Chat key={source?.seed} picked={picked} />
      </div>
    </Seed.Provider>
  )
}
