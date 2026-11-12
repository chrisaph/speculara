// Normalize Story records from both initial Relay data and subsequent GraphQL.
export function facebookStories(payloads, profile) {
  const stories=new Map(),seen=new Set()
  const handle=profile.handle.toLowerCase()
  const belongs=url=>{
    try { const u=new URL(url);return /(^|\.)facebook\.com$/.test(u.hostname)&&!u.username&&
      (u.pathname.toLowerCase().startsWith(`/${handle}/`) || (profile.handle.match(/^\d+$/)&&u.searchParams.get('id')===profile.handle)) }
    catch{return false}
  }
  const walk=(v,depth=0)=>{
    if(!v||typeof v!=='object'||seen.has(v)||depth>60)return
    seen.add(v)
    if(Array.isArray(v)){for(const x of v)walk(x,depth+1);return}
    const url=v.url||v.permalink_url
    const id=v.post_id||v.legacy_fbid||(v.__typename==='Story'?v.id:null)
    if(id&&typeof url==='string'&&belongs(url)&&('comet_sections' in v||v.__typename==='Story')) {
      const key=String(id)
      if(!stories.has(key)||Object.keys(v).length>Object.keys(stories.get(key)).length) stories.set(key,{...v,post_id:key,url})
    }
    for(const child of Object.values(v))walk(child,depth+1)
  }
  walk(payloads)
  return [...stories.values()]
}
