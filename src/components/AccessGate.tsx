import { useState,type ReactNode,type FormEvent } from 'react'
import { unlockDemo,setAccessToken } from '../api'

export function AccessGate({children}:{children:ReactNode}) {
  const [allowed,setAllowed]=useState(false),[code,setCode]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  if(import.meta.env?.VITE_REQUIRE_ACCESS_CODE!=='true')return <>{children}</>
  async function unlock(event:FormEvent) {
    event.preventDefault();if(busy)return;setBusy(true);setError('')
    try {await unlockDemo(code);setCode('');setAllowed(true)}
    catch(e) {setAccessToken('');setError((e as Error).message)}
    finally {setBusy(false)}
  }
  if(allowed)return <><div className="mx-auto max-w-6xl px-6 pt-3 text-right"><button className="neu-sm min-h-10 rounded-full px-4 text-sm font-semibold text-ink" onClick={()=>{setAccessToken('');setAllowed(false)}}>Lock demo</button></div>{children}</>
  return <main className="grid min-h-screen place-items-center bg-mist p-6"><form onSubmit={unlock} className="neu w-full max-w-md space-y-5 rounded-3xl p-7"><div className="flex items-center gap-3"><img src="/speculara-logo.svg" alt="Speculara" width="48" height="48"/><h1 className="font-display text-2xl font-bold text-ink">Speculara demo</h1></div><p className="text-sm text-slate-700">Enter the access code shared by the demo operator.</p><label className="block text-sm font-semibold text-ink">Demo access code<input type="password" autoComplete="off" required value={code} onChange={e=>setCode(e.target.value)} className="neu-in mt-2 min-h-12 w-full rounded-xl p-3 font-normal" /></label><button disabled={busy} className="neu-btn min-h-12 w-full rounded-xl text-white disabled:opacity-60">{busy?'Checking access…':'Open demo'}</button>{busy&&<p role="status" className="text-sm text-slate-600">Render Free may take up to two minutes to wake. Keep this tab open.</p>}{error&&<p role="alert" className="text-sm text-wine">{error}</p>}<p className="text-xs text-slate-600">The code stays in memory for this tab. Refreshing asks for it again.</p></form></main>
}
