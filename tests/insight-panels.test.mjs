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
 assert.match(html,/23/); assert.match(html,/Accuracy unavailable/); assert.match(html,/Illustrative trend lifecycle/)
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

test('simple prediction uses real post values with the future highlight and accuracy',()=>{
 const data={basis:'post',history:[{date:'2026-01-01',value:100}],forecast:[{date:'Next post 1',value:120,low:90,high:150}],accuracy:65}
 const html=render.renderPredict({predict:{trend_metric:'likes',metrics:{likes:data},weekly_metrics:{likes:{basis:'week',history:[],forecast:[]}}}})
 assert.match(html,/likes per post/);assert.match(html,/Next post 1/)
 assert.match(html,/Accuracy: 65%/);assert.match(html,/Measures fit to historical data/)
 assert.match(html,/data-forecast-band="true"/);assert.match(html,/stroke-dasharray="6 4"/)
 assert.match(html,/>Forecast</);assert.match(html,/Documentation/)
 assert.doesNotMatch(html,/Forecast check:|Explore the forecast|Forecast detail/)
})

test('simple prediction never raises a low score to meet a display target',()=>{
 const data={basis:'post',history:[{date:'2026-01-01',value:100}],forecast:[{date:'Next post 8',value:100,low:0,high:900}],accuracy:0}
 const html=render.renderPredict({predict:{trend_metric:'likes',metrics:{likes:data}}})
 assert.match(html,/Accuracy: 0%/);assert.match(html,/Next post 8/)
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


test('weekly chart and accuracy stay paired while automatic checks remain in backend data',()=>{
 const post={basis:'post',history:[{date:'2026-11-01',value:100}],forecast:[{date:'Next post 1',value:120,low:90,high:150}],accuracy:46,forecast_check:{score:10,checks:10}}
 const weekly={basis:'week',history:[{date:'2026-11-01',value:200}],forecast:[{date:'2026-11-08',value:250,low:100,high:400}],accuracy:53}
 const data={predict:{trend_metric:'likes',metrics:{likes:post},weekly_metrics:{likes:weekly}}}
 const html=render.renderPredict(data)
 assert.match(html,/Accuracy: 53%/);assert.match(html,/likes by week/)
 assert.doesNotMatch(html,/Accuracy: 46%|Forecast check:|Next post 1/)
 assert.equal(data.predict.metrics.likes.forecast_check.checks,10)
 const short=render.renderPredict({...data,predict:{...data.predict,weekly_metrics:{likes:{...weekly,forecast:[],accuracy:97}}}})
 assert.match(short,/Accuracy: 46%/);assert.match(short,/likes per post/)
 assert.doesNotMatch(short,/Accuracy: 97%/)
})

test('missing metric is explained without a blank model line',()=>{
 const html=render.renderValidation({score_basis:'fitted_history',accuracy:null,reason:'No observed views values were supplied.'})
 assert.match(html,/No observed views/)
 assert.doesNotMatch(html,/Measures how closely|undefined|NaN/)
})


test('simple prediction retains the lifecycle design and selects real daily data when eligible',()=>{
 const daily={basis:'day',history:[{date:'2026-01-14',value:14}],forecast:[{date:'2026-01-15',value:15,low:14,high:16}],accuracy:97,model:'Daily linear trend'}
 const html=render.renderPredict({predict:{trend_metric:'likes',metrics:{likes:{history:[],forecast:[]}},daily_metrics:{likes:daily},weekly_metrics:{likes:{phase:'Rising',growth:12,similar:0,weeks_left:null}}}})
 assert.match(html,/Accuracy: 97%/);assert.match(html,/likes by day/)
 assert.match(html,/data-forecast-band="true"/);assert.match(html,/Illustrative trend lifecycle/)
 assert.match(html,/Download forecast data/);assert.match(html,/Measures fit to historical data/)
 assert.doesNotMatch(html,/placeholder|Forecast check:|NaN|undefined/)
})

test('demo guidance recommends complete inputs and explains link limitations',()=>{
 const html=render.renderApp()
 assert.match(html,/For the demo:/);assert.match(html,/complete CSV/)
 assert.match(html,/Profile links also work/);assert.match(html,/Sample results are illustrative/)
 assert.match(html,/url-msg demo-guidance/)
})


test('large uncertainty cannot hide the chart line without an explicit scale explanation',()=>{
 const data={basis:'post',history:[{date:'2026-11-01',value:1000},{date:'2026-11-02',value:1800}],forecast:[{date:'Next post 1',value:1500,low:0,high:471400000}],accuracy:60}
 const html=render.renderPredict({predict:{trend_metric:'likes',metrics:{likes:data},weekly_metrics:{likes:{growth:null}},post_trends:{likes:{basis:'post',phase:'Rising',growth:15,similar:0,posts_left:null}}}})
 assert.match(html,/Log scale keeps the full forecast range visible/)
 assert.match(html,/471,400,000/)
 assert.match(html,/View exact values and ranges/)
 assert.match(html,/Activity \/ post/)
 assert.match(html,/Phase: Rising/)
 assert.doesNotMatch(html,/NaN|undefined/)
})
