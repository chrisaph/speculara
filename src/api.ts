const API = (import.meta.env?.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
let accessToken=''
export function setAccessToken(value:string) { accessToken=value.trim() }
export function accessHeaders(base=API):Record<string,string> {
  const headers:Record<string,string>=accessToken?{Authorization:`Bearer ${accessToken}`} : {}
  try {
    const host=new URL(base).hostname
    if(['ngrok-free.app','ngrok-free.dev','ngrok.app','ngrok.dev','ngrok.io'].some(domain=>host.endsWith('.'+domain)))headers['ngrok-skip-browser-warning']='1'
  } catch { /* Same-origin/local API does not need provider headers. */ }
  return headers
}

export async function uploadDataset(file:File) {
  const body=new FormData();body.append('file',file)
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000)
  try { const res=await fetch(`${API}/api/upload`,{method:'POST',body,headers:accessHeaders(),signal:controller.signal});const data=await res.json();if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not analyze this file.');return data }
  finally {clearTimeout(timer)}
}

export async function importMetrics(analysis:unknown,file:File) {
  const body=new FormData();body.append('analysis',JSON.stringify(analysis));body.append('file',file)
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000)
  try { const res=await fetch(`${API}/api/metrics`,{method:'POST',body,headers:accessHeaders(),signal:controller.signal});const data=await res.json();if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not import these metrics.');return data }
  catch(e) { if(controller.signal.aborted)throw new Error('The metric import timed out. Try a smaller file.');throw e }
  finally { clearTimeout(timer) }
}

export async function api<T = any>(path: string, body?: unknown, options: { timeoutMs?: number; signal?: AbortSignal } = {}): Promise<T> {
  const controller = new AbortController()
  const forwardAbort = () => controller.abort()
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, options.timeoutMs ?? 30000)
  options.signal?.addEventListener('abort', forwardAbort, { once: true })
  if (options.signal?.aborted) controller.abort()
  try {
    const res = await fetch(`${API}${path}`, {
      headers: {...accessHeaders(),...(body===undefined?{}:{'Content-Type':'application/json'})},
      ...(body === undefined ? {} : { method: 'POST', body: JSON.stringify(body) }),
      signal: controller.signal,
    })
    const data = await res.json().catch(() => null)
    if (controller.signal.aborted) throw new Error('Request aborted.')
    if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'The analysis service had a problem. Please try again.')
    if (data===null) throw new Error('The backend is starting or returned an unexpected response. Wait a moment and retry.')
    return data as T
  } catch (error) {
    if (timedOut) throw new Error('The request timed out. The collector may need sign-in or a retry; check its status below.')
    if (options.signal?.aborted) throw new Error('Analysis cancelled.')
    if (error instanceof TypeError) throw new Error('Cannot reach the backend. It may be waking up. Check the Render URL and that Render allows this Netlify site in FRONTEND_URL or CORS_ORIGINS.')
    throw error
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', forwardAbort)
  }
}

export async function unlockDemo(code:string,options:{attempts?:number;retryDelayMs?:number}={}) {
  setAccessToken('')
  const attempts=options.attempts??6
  for(let attempt=0;attempt<attempts;attempt++) {
    try {
      const health=await api('/api/health',undefined,{timeoutMs:20000})
      if(health?.ok!==true)throw new Error('The backend is not ready yet.')
      break
    } catch(error) {
      if(attempt===attempts-1)throw error
      await new Promise(resolve=>setTimeout(resolve,options.retryDelayMs??2000))
    }
  }
  setAccessToken(code)
  try {
    const result=await api('/api/access')
    if(result?.ok!==true)throw new Error('The backend did not confirm demo access. Check VITE_API_URL and redeploy Netlify.')
  } catch(error) {setAccessToken('');throw error}
}
