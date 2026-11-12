const API = (import.meta.env?.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export async function uploadDataset(file:File) {
  const body=new FormData();body.append('file',file)
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000)
  try { const res=await fetch(`${API}/api/upload`,{method:'POST',body,signal:controller.signal});const data=await res.json();if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not analyze this file.');return data }
  finally {clearTimeout(timer)}
}

export async function importMetrics(analysis:unknown,file:File) {
  const body=new FormData();body.append('analysis',JSON.stringify(analysis));body.append('file',file)
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000)
  try { const res=await fetch(`${API}/api/metrics`,{method:'POST',body,signal:controller.signal});const data=await res.json();if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not import these metrics.');return data }
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
      ...(body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
      signal: controller.signal,
    })
    const data = await res.json().catch(() => ({}))
    if (controller.signal.aborted) throw new Error('Request aborted.')
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The analysis service had a problem. Please try again.')
    return data as T
  } catch (error) {
    if (timedOut) throw new Error('The request timed out. The collector may need sign-in or a retry; check its status below.')
    if (options.signal?.aborted) throw new Error('Analysis cancelled.')
    throw error
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', forwardAbort)
  }
}
