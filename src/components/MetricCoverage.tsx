import { useRef, useState } from 'react'
import { importMetrics } from '../api'

const metrics=['views','likes','comments','shares','saves','sales']
const quote=(value:unknown) => `"${String(value??'').replace(/"/g,'""')}"`
export function metricsTemplate(analysis:any) {
  // Blank metric cells never overwrite existing measured values on import.
  return ['id,url,'+metrics.join(','),...(analysis?.evidence?.posts||[]).map((p:any)=>[quote(p.url?'':p.id),quote(p.url),...metrics.map(()=> '')].join(','))].join('\r\n')
}

export function MetricCoverage({ analysis, onUpdated }: { analysis:any; onUpdated:(analysis:any)=>void }) {
  const input=useRef<HTMLInputElement>(null), [busy,setBusy]=useState(false), [error,setError]=useState('')
  const coverage=analysis?.metric_availability || {}, count=analysis?.evidence?.posts?.length||0
  async function upload(file?:File) {
    if(!file) return
    setBusy(true);setError('')
    try { if(file.size>10_000_000) throw new Error('Use a metrics file smaller than 10 MB.'); onUpdated(await importMetrics(analysis,file)) }
    catch(e) { setError((e as Error).message) }
    finally { setBusy(false); if(input.current) input.current.value='' }
  }
  if(!count) return null
  return <section aria-label="Metric availability and import" className="neu mb-5 rounded-3xl p-4 sm:p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-display font-bold text-ink">Your available metrics</h3><p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-600">Public profiles may not provide saves, shares or sales. Add your own post-level Insights or sales counts below to unlock those metrics. Sales means a count, not revenue.</p></div></div>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">{metrics.map(metric=>{ const c=coverage[metric],known=c?.known_posts??0;return <div key={metric} className="neu-in rounded-xl p-3"><p className="text-xs font-semibold capitalize text-ink">{metric}</p><p className="mt-1 font-display text-lg font-bold text-ink">{known?c.total.toLocaleString():'Not supplied'}</p><p className="mt-1 text-[11px] text-slate-600">{known}/{count} posts · {c?.imported_posts||0} user-imported{known<count?' · partial coverage':''}</p></div> })}</div>
    <div className="mt-4 flex flex-wrap items-center gap-3"><a href={`data:text/csv;charset=utf-8,${encodeURIComponent(metricsTemplate(analysis))}`} download="speculara-post-metrics.csv" className="neu-sm inline-flex min-h-11 items-center rounded-full px-4 text-xs font-semibold text-ink">Download metrics template</a><button disabled={busy} onClick={()=>input.current?.click()} className="neu-btn min-h-11 rounded-full px-4 text-xs font-semibold text-white disabled:opacity-50">{busy?'Updating all results…':'Import metrics CSV / Excel'}</button><input ref={input} type="file" accept=".csv,.xlsx" aria-label="Import post metrics" onChange={e=>void upload(e.target.files?.[0])} className="sr-only" /></div>
    <p className="mt-3 text-xs text-slate-600">Match each row by post ID or URL. Fill only known counts; leave unknown values blank. A supplied 0 is treated as a measured zero. Import updates every panel and the chat without collecting posts again.</p>{error&&<p role="alert" className="mt-3 text-sm text-wine">{error}</p>}
  </section>
}
