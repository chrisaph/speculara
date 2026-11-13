import test, { before, after } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { chartView, correlationView, resolvePost } from '../src/insights.ts'

let server, render
before(async () => {
  server = await createServer({ configFile:false,cacheDir:`.tmp-test-cache/insights-${process.pid}`,plugins:[react()],optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom' })
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

test('metric coverage distinguishes missing, zero and imported counts',()=>{
 const data={...analysis,metric_availability:{views:{known_posts:0,total:null},likes:{known_posts:5,total:100,imported_posts:2},sales:{known_posts:5,total:0,imported_posts:5}}}
 const html=render.renderCoverage(data)
 assert.match(html,/Not supplied/);assert.match(html,/text-ink-dark/);assert.match(html,/2 user-imported/)
 assert.match(html,/Import metrics CSV \/ Excel/);assert.match(html,/measured zero/)
 assert.doesNotMatch(html,/NaN|undefined/)
 const csv=render.metricsCSV(data)
 assert.match(csv,/id,url,views,likes,comments,shares,saves,sales/)
 assert.match(csv, /"","https:\/\/www.instagram.com\/reel\/qa0\/",,,,,,/)
})
test('zero backtest score explains excessive error and shows actual-versus-predicted evidence',()=>{
 const html=render.renderValidation({accuracy:0,model:'Last observed week',validation:{weighted_error_pct:150,test_weeks:2,observations:[{date:'2026-11-01',actual:10,predicted:25}]}})
 assert.match(html,/Accuracy: 0%/);assert.match(html,/Backtest error: 150%/);assert.match(html,/Low reliability/)
 assert.match(html,/does not mean the posts had no activity/);assert.match(html,/Actual/);assert.match(html,/Predicted/)
})

test('post forecasts use post units and disclose the matching holdout baseline',()=>{
 const data={basis:'post',history:[{date:'2026-01-01',value:100}],forecast:[{date:'Next post 1',value:100,low:90,high:110}],accuracy:90,validation:{test_posts:3,weighted_error_pct:10,baseline_weighted_error_pct:20,baseline_model:'Recent four-post average',observations:[{date:'2026-01-02',actual:100,predicted:90}]}}
 const html=render.renderPredict({...analysis,predict:{basis:'post',trend_metric:'likes',metrics:{likes:data},weekly_metrics:{likes:{basis:'week',history:[]}},similar_windows:[]}})
 assert.match(html,/likes per post/);assert.match(html,/Next post 1/);assert.match(html,/Weekly totals/)
 assert.match(html,/Accuracy: 90%/);assert.match(html,/Backtest error: 10%/);assert.match(html,/3 latest posts/);assert.match(html,/Post date/)
 assert.match(html,/20% error on the same holdout/);assert.doesNotMatch(html,/3 completed weeks/)
})

test('a poor backtest keeps exploratory projection and discloses its actual error',()=>{
 const data={basis:'post',history:[{date:'2026-01-01',value:100}],forecast:[{date:'Next post 8',value:100,low:0,high:900}],accuracy:0,validation:{weighted_error_pct:129.9,test_posts:4}}
 const html=render.renderPredict({...analysis,predict:{basis:'post',trend_metric:'likes',metrics:{likes:data},similar_windows:[]}})
 assert.match(html,/Accuracy: 0%/);assert.match(html,/129.9%/)
 assert.match(html,/Next post 8/);assert.match(html,/Download forecast periods and values/)
})
test('chat suggestions expose horizontal scrolling and both navigation controls',()=>{
 const html=render.renderSuggestions(['First question','Second question','Third question'])
 assert.match(html,/Previous chat suggestions/);assert.match(html,/Next chat suggestions/)
 assert.match(html,/Scrollable chat suggestions/);assert.match(html,/Swipe, drag/)
 assert.match(html,/Third question/);assert.match(html,/overflow-x-auto/)
})

test('accuracy uses the Python score, including zero, while raw errors stay in collapsed details',()=>{
 for(const score of [0,57,100]) {
   const html=render.renderValidation({accuracy:score,validation:{weighted_error_pct:465.3}})
   assert.match(html,new RegExp(`Accuracy: ${score}%`))
   assert.match(html,/<details[^>]*aria-label="Prediction backtest details"/)
   assert.doesNotMatch(html,/<details[^>]*\sopen(?:\s|>)/)
 }
 const missing=render.renderValidation({accuracy:null,validation:{}})
 assert.match(missing,/Accuracy unavailable/)
 assert.doesNotMatch(missing,/Accuracy: 0%/)
})

test('stale withheld forecasts prompt reanalysis instead of contradicting current forecast messaging',()=>{
 const html=render.renderPredict({...analysis,predict:{basis:'post',trend_metric:'likes',metrics:{likes:{history:[],forecast:[],accuracy:0,reason:'Forecast withheld: old behavior',validation:{weighted_error_pct:465.3}}}}})
 assert.match(html,/Analyze the profile again/)
 assert.doesNotMatch(html,/Forecast withheld:/)
})
