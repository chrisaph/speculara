import test from 'node:test'
import assert from 'node:assert/strict'
import { postTarget, extractMetrics } from './public-metrics.mjs'

test('public enrichment matches the exact post and preserves missing and zero counts',()=>{
 const target=postTarget({id:'123',url:'https://www.instagram.com/reel/fixture/'})
 const result=extractMetrics({posts:[{id:'999',shortcode:'unrelated',view_count:900000},{id:'123',shortcode:'fixture',play_count:321,share_count:0,save_count:null,sales:500,like_count:14}]},target)
 assert.deepEqual(result,{views:321,shares:0,likes:14})
 assert.equal(result.sales,undefined)
})

test('background post targets reject arbitrary hosts and credentials',()=>{
 for(const url of ['http://www.instagram.com/p/test/','https://127.0.0.1/','https://www.instagram.com.evil.test/p/test/','https://user:pass@www.instagram.com/p/test/','https://www.instagram.com/accounts/login/'])assert.throws(()=>postTarget({id:'1',url}))
 assert.throws(()=>postTarget({id:'',url:'https://www.instagram.com/p/test/'}))
})
import { execute } from './worker.mjs'

test('background worker reads exact public post JSON and closes the browser',async()=>{
 let closed=false
 const page={on(){},off(){},async goto(){},url(){return 'https://www.instagram.com/reel/fixture/'},async waitForLoadState(){},locator(){return {async evaluateAll(){return [{shortcode:'fixture',view_count:1200,share_count:4}]}}}}
 const result=await execute({action:'enrich',posts:[{id:'123',url:'https://www.instagram.com/reel/fixture/'}]}, {async openBrowser(){return {async newPage(){return page}}},async closeBrowser(){closed=true}},()=>{})
 assert.equal(result.checked,1)
 assert.equal(result.posts[0].metrics.views,1200)
 assert.equal(result.posts[0].metrics.shares,4)
 assert.equal(result.posts[0].metrics.sales,undefined)
 assert.equal(closed,true)
})
