import test, { before, after } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { chartView, correlationView, resolvePost } from '../src/insights.ts'

let server, render
before(async () => {
  server = await createServer({ configFile:false,plugins:[react()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom' })
  render = await server.ssrLoadModule('/tests/render-panels.tsx')
})
after(async () => { await server?.close() })
const posts=Array.from({length:5},(_,i)=>({id:`p${i}`,type:'Reel',caption:`QA banana post ${i}`,url:`https://www.instagram.com/reel/qa${i}/`,posted_at:`2026-01-${String(i+1).padStart(2,'0')}T00:00:00Z`,likes:i*10,views:0,unavailable_metrics:['views']}))
const analysis={evidence:{posts},predict:{trend_metric:'likes',metrics:{likes:{history:[{date:'2026-01-01',value:23}],forecast:[],accuracy:null,reason:'Six weeks needed'}},similar_windows:[]},recommend:{comparisons:{p0:[{id:'p1',title:'QA banana post 1',url:posts[1].url,type:'Reel',score:72,caption_similarity:.8,comment_similarity:.6,metric_similarity:.7}]},actions:[]},correlation:{matrix:{likes:{likes:1,comments:-1},comments:{likes:-1,comments:1}},pairs:[{a:'Likes',b:'Comments',v:-1,n:5}],scatter:{'likes|comments':[{id:'p1',x:20,y:50,title:'Actual post'}]}}}

test('actual chart totals and all-post shares reconcile without rounding to an axis maximum',()=>{
 const view=chartView(analysis,'likes')
 assert.equal(view.total,100); assert.equal(view.series[0].value,100)
 assert.equal(view.shares.length,5); assert.equal(view.shares.reduce((s,p)=>s+p.pct,0),100)
 assert.equal(chartView(analysis,'likes','month','p3').selectedTotal,30)
 assert.equal(chartView(analysis,'views').selectedTotal,null)
})
test('URL selector resolves only collected posts and ignores tracking query',()=>{
 assert.equal(resolvePost(posts,'https://instagram.com/reel/qa3/?utm_source=test'),'p3')
 assert.equal(resolvePost(posts,'https://instagram.com/reel/not-collected/'),undefined)
})
test('negative and strong filters update real relationship list',()=>{
 assert.equal(correlationView(analysis,'Negative only').pairs[0].v,-1)
 assert.equal(correlationView(analysis,'Strong only').pairs.length,1)
 assert.equal(correlationView({correlation:{pairs:[{v:.2}]}},'Strong only').pairs.length,0)
})
test('prediction renders actual observed values and no fabricated accuracy or reminder',()=>{
 const html=render.renderPredict(analysis)
 assert.match(html,/23/); assert.match(html,/Accuracy unavailable/); assert.match(html,/View evidence/)
 assert.doesNotMatch(html,/88%|Reminder set|Jan 25|NaN|undefined/)
})
test('recommendations render post titles, dropdown and source with no item placeholders or lifts',()=>{
 const html=render.renderRecommend(analysis)
 assert.match(html,/Choose a collected post/); assert.match(html,/QA banana post 1/); assert.match(html,/qa1\//)
 assert.doesNotMatch(html,/Item A|Item B|Bought together|18% reach|NaN|undefined/)
})
test('chart render has values, all five posts, dates and sources',()=>{
 const html=render.renderCharts(analysis)
 assert.match(html,/100/); assert.match(html,/2026-01/); assert.match(html,/QA banana post 4/)
 assert.match(html,/Read numeric values/); assert.match(html,/5 posts compared/)
 assert.doesNotMatch(html,/Category A|NaN|undefined/)
})
test('correlation render uses signed matrix and actual pair labels',()=>{
 const html=render.renderCorrelation(analysis)
 assert.match(html,/-1.000/); assert.match(html,/Likes versus Comments/)
 assert.doesNotMatch(html,/Recommended|per trend|NaN|undefined/)
})
test('all four panels have explanatory empty states without synthetic data',()=>{
 for(const fn of ['renderPredict','renderRecommend','renderCharts','renderCorrelation']) {
  const html=render[fn]({}); assert.doesNotMatch(html,/NaN|undefined|Item B/)
 }
})
test('root never generates mock facts or silently connects failed sample requests',async()=>{
 const code=await readFile(new URL('../src/App.tsx',import.meta.url),'utf8')
 assert.doesNotMatch(code,/mockFacts|function hash|Item B|falls back to built-in/)
 assert.match(code,/Could not load sample data/)
 assert.match(code,/const liveFor = \(seed: string\) => live.get\(seed\)/)
})
