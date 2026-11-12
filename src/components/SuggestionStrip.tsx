import { useRef } from 'react'

export function SuggestionStrip({ items, disabled, onSelect }: { items: string[]; disabled?: boolean; onSelect: (value: string) => void }) {
  const strip=useRef<HTMLDivElement>(null)
  const drag=useRef({ active:false, moved:false, x:0, left:0 })
  const move=(direction:number) => strip.current?.scrollBy({left:direction*Math.max(160,strip.current.clientWidth*.8),behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})
  return <div className="shrink-0 px-3 pt-3"><div className="flex min-w-0 items-center gap-2">
    <button type="button" onClick={() => move(-1)} aria-label="Previous chat suggestions" className="neu-sm grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink">‹</button>
    <div ref={strip} role="region" aria-label="Scrollable chat suggestions" tabIndex={0} className="neu-scroll flex min-w-0 flex-1 cursor-grab gap-2 overflow-x-auto overscroll-x-contain p-2 active:cursor-grabbing focus-visible:outline-2 focus-visible:outline-sky"
      onPointerDown={e => { drag.current.moved=false; if(e.pointerType==='mouse'&&e.button===0) drag.current={active:true,moved:false,x:e.clientX,left:e.currentTarget.scrollLeft} }}
      onPointerMove={e => { const d=drag.current; if(!d.active) return; const distance=e.clientX-d.x; if(Math.abs(distance)>5) { d.moved=true; e.currentTarget.setPointerCapture(e.pointerId); e.preventDefault(); e.currentTarget.scrollLeft=d.left-distance } }}
      onPointerUp={e => { drag.current.active=false; if(e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId) }}
      onPointerCancel={() => { drag.current.active=false; drag.current.moved=false }}
      onClickCapture={e => { if(drag.current.moved) { e.preventDefault(); e.stopPropagation(); drag.current.moved=false } }}>
      {items.map(question => <button type="button" key={question} disabled={disabled} onClick={() => onSelect(question)} className="neu-sm min-h-9 shrink-0 select-none rounded-full px-3 py-1.5 text-xs text-ink disabled:opacity-50">{question}</button>)}
    </div><button type="button" onClick={() => move(1)} aria-label="Next chat suggestions" className="neu-sm grid h-9 w-9 shrink-0 place-items-center rounded-full text-ink">›</button>
  </div><p className="mt-1 text-center text-[10px] text-slate-500">Swipe, drag, or use the arrows for more questions.</p></div>
}
