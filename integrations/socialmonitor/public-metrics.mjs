// Best-effort post-page reads. Never infer private metrics or sales.
export function postTarget(post) {
  if (!String(post.id ?? '').trim()) throw new Error('A collected post ID is required.')
  const url = new URL(post.url)
  if (url.protocol !== 'https:' || !['www.instagram.com', 'instagram.com'].includes(url.hostname) || url.port || url.username || url.password || !/^\/(p|reel)\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)) throw new Error('Only collected Instagram post URLs can be checked.')
  return { id: String(post.id), code: url.pathname.split('/')[2], url: `https://www.instagram.com${url.pathname.replace(/\/$/, '')}/` }
}

export function extractMetrics(payload, target) {
  const found = {}, seen = new Set()
  const fields = { views: ['video_view_count','view_count','ig_play_count','play_count','video_play_count'], likes: ['like_count'], comments: ['comment_count'], shares: ['share_count','shares_count'], saves: ['save_count','saved_count'] }
  const count = value => (typeof value === 'number' || typeof value === 'string' && /^\d+$/.test(value)) && Number.isSafeInteger(Number(value)) && Number(value) >= 0 && Number(value) <= 1e15 ? Number(value) : undefined
  function walk(value, depth=0) {
    if (!value || typeof value !== 'object' || depth > 35 || seen.has(value)) return
    seen.add(value)
    const matches = (value.shortcode || value.code) === target.code || String(value.pk || value.id || '').split('_')[0] === target.id
    if (matches) {
      for (const [metric, names] of Object.entries(fields)) {
        for (const name of names) { const n=count(value[name]); if (n !== undefined) { found[metric]=n; break } }
      }
      for (const [metric, key] of [['likes','edge_liked_by'],['comments','edge_media_to_comment']]) {
        const n=count(value[key]?.count); if (n !== undefined) found[metric]=n
      }
    }
    for (const child of Object.values(value)) walk(child,depth+1)
  }
  walk(payload)
  return found
}

export async function readPublicMetrics(input, deps, emit) {
  const targets = (input.posts || []).slice(0,20).map(postTarget)
  let checked=0, cancelled=false
  deps.cancelled?.then(()=>{ cancelled=true })
  const posts=[], notes=[]
  try {
    const context=await deps.openBrowser(), page=await context.newPage()
    for (const target of targets) {
      if (cancelled) throw new Error('Collection cancelled.')
      const payloads=[], pending=[]
      const listener = response => {
        const u=new URL(response.url())
        if ((u.hostname==='instagram.com' || u.hostname.endsWith('.instagram.com')) && /graphql|api\/v1\/media/.test(u.pathname) && payloads.length < 40) {
          pending.push(response.json().then(data=>payloads.push(data)).catch(()=>{}))
        }
      }
      page.on('response',listener)
      try {
        emit({event:'progress',message:`Checking public metrics ${checked+1} of ${targets.length}…`})
        await page.goto(target.url,{waitUntil:'domcontentloaded',timeout:7000})
        if (/\/accounts\/login|\/challenge|\/checkpoint/.test(page.url())) { notes.push('Instagram requires sign-in or a security check.'); break }
        await page.waitForLoadState('networkidle',{timeout:750}).catch(()=>{})
        const embedded=await page.locator('script[type="application/json"],script[type="application/ld+json"]').evaluateAll(scripts=>scripts.slice(0,100).flatMap(script=>{
          try { const text=script.textContent || ''; return text.length<=5000000 ? [JSON.parse(text)] : [] } catch { return [] }
        }))
        await Promise.allSettled(pending)
        posts.push({id:target.id,url:target.url,metrics:extractMetrics([...payloads,...embedded],target)})
      } catch { notes.push('Some post pages could not be read.') }
      finally { page.off('response',listener); checked++ }
    }
    return {posts,checked,notes:[...new Set(notes)]}
  } finally { await deps.closeBrowser() }
}
