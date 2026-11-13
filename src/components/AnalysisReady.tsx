export type ReadyInfo={label:string;postCount:number|null}

function readyText(info:ReadyInfo) {
  return `${info.postCount==null?'Analysis':`${info.postCount} ${info.postCount===1?'post':'posts'}`} ready from ${info.label}.`
}

export function AnalysisReadyNotice({info}:{info:ReadyInfo}) {
  return <aside role="note" aria-label="Analysis ready" className="neu-in mx-2 mb-3 rounded-2xl px-4 py-3 text-sm text-ink"><p className="font-semibold">{readyText(info)}</p><p className="mt-1 text-xs text-slate-600">Choose a question below to view your results. You can switch options at any time.</p></aside>
}

export function AnalysisReadyToast({info,onChoose,onDismiss}:{info:ReadyInfo;onChoose:()=>void;onDismiss:()=>void}) {
  return <div role="status" aria-label="Analysis completion" className="neu fixed bottom-5 left-4 right-4 z-50 rounded-2xl bg-mist p-4 text-sm text-ink sm:left-6 sm:right-auto sm:w-96"><div className="flex items-start gap-3"><p className="flex-1 font-semibold">{readyText(info)}</p><button type="button" aria-label="Dismiss completion notification" onClick={onDismiss} className="neu-sm grid h-8 w-8 shrink-0 place-items-center rounded-full">×</button></div><p className="mt-2 text-xs text-slate-600">Scroll up and choose a question to explore your results.</p><button type="button" onClick={onChoose} className="neu-sm mt-3 min-h-10 rounded-xl px-4 text-xs font-semibold text-ink">Choose a question</button></div>
}
