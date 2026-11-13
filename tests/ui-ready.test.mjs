import test from 'node:test'
import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {mkdir} from 'node:fs/promises'
import path from 'node:path'
import {createServer} from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import {chromium} from '../integrations/socialmonitor/node_modules/playwright/index.mjs'

const root=fileURLToPath(new URL('../',import.meta.url))

test('completed analysis shows a temporary popup and a persistent choice notice; forecast details start closed',async()=>{
  const previousEnv={VITE_API_URL:process.env.VITE_API_URL,VITE_COLLECTOR_MODE:process.env.VITE_COLLECTOR_MODE,VITE_REQUIRE_ACCESS_CODE:process.env.VITE_REQUIRE_ACCESS_CODE}
  Object.assign(process.env,{VITE_API_URL:'',VITE_COLLECTOR_MODE:'operator',VITE_REQUIRE_ACCESS_CODE:'false'})
  const python=path.join(root,'backend',process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python')
  const data=JSON.parse(execFileSync(python,['-c',"import json; from app.analytics import analyze; from app.sample import sample_posts; print(json.dumps({'profile':{'platform':'Instagram','handle':'qa','notes':'Synthetic browser-test fixture'},**analyze(sample_posts(20))}))"],{cwd:path.join(root,'backend'),encoding:'utf8'}))
  const server=await createServer({configFile:false,root,cacheDir:'.tmp-test-cache/ui-ready',plugins:[react(),tailwindcss()],
    define:{'import.meta.env':JSON.stringify({VITE_API_URL:'',VITE_COLLECTOR_MODE:'operator',VITE_REQUIRE_ACCESS_CODE:'false'})},
    server:{host:'127.0.0.1',port:0,hmr:false,ws:false,watch:null,fs:{deny:['.env','.env.*','**/.socialmonitor/**','**/.venv/**','**/.tmp-*/**']}}})
  let browser
  try {
    await server.listen()
    browser=await chromium.launch({headless:true,channel:'chrome'})
    const page=await browser.newPage({viewport:{width:1280,height:960}})
    await page.clock.install()
    let fail=false
    await page.route('**/api/**',async route=>{
      const pathname=new URL(route.request().url()).pathname
      if(pathname==='/api/collector/status')return route.fulfill({json:{installed:true,busy:false,login_open:false}})
      if(pathname==='/api/analyze'&&fail)return route.fulfill({status:503,json:{detail:'Synthetic collection failed'}})
      return route.fulfill({json:data})
    })
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}`)
    const notice=page.getByRole('note',{name:'Analysis ready'})
    const toast=page.getByRole('status',{name:'Analysis completion'})
    assert.equal(await notice.count(),0)
    await page.locator('#url').fill('https://www.instagram.com/qa/')
    await page.getByRole('button',{name:'Analyze',exact:true}).click()
    await toast.waitFor({state:'visible'})
    assert.match(await notice.innerText(),/20 posts ready from instagram.com\/qa/)
    const before=await page.locator('#analysis-options').evaluate(el=>[...el.children].map(child=>child.textContent))
    assert.match(before[0],/20 posts ready/);assert.equal(before[1],'Scroll and choose')
    await page.getByRole('button',{name:'Choose a question',exact:true}).click()
    await page.clock.runFor(500)
    const bannerBox=await notice.boundingBox(),headerBox=await page.locator('header').boundingBox()
    assert.ok(bannerBox.y>=headerBox.y+headerBox.height,'Completion notice must not be hidden behind the sticky header')
    await page.getByRole('button',{name:'What do you want to Predict?',exact:true}).click()
    assert.equal(await notice.isVisible(),true)
    const score=data.predict.metrics[data.predict.trend_metric].accuracy
    assert.equal(await page.getByLabel('Prediction accuracy').innerText(),score==null?'Accuracy unavailable':`Accuracy: ${score}%`)
    const details=page.locator('details[aria-label="Prediction backtest details"]')
    assert.equal(await details.getAttribute('open'),null)
    assert.equal(await details.locator('strong').isVisible(),false)
    await mkdir(path.join(root,'.tmp-ui-ready'),{recursive:true})
    await page.getByLabel('Prediction accuracy').locator('../../..').screenshot({path:path.join(root,'.tmp-ui-ready','forecast-summary.png')})
    await details.locator('summary').click()
    assert.equal(await details.locator('strong').isVisible(),true)
    await page.clock.fastForward(6200)
    assert.equal(await toast.count(),0)
    assert.equal(await notice.isVisible(),true)
    await page.getByRole('button',{name:'What do you want to get charts of?',exact:true}).click()
    assert.equal(await notice.isVisible(),true)
    fail=true
    await page.locator('#url').fill('https://www.instagram.com/qa-failure/')
    await page.getByRole('button',{name:'Analyze',exact:true}).click()
    await page.getByText('Synthetic collection failed',{exact:true}).waitFor()
    assert.equal(await toast.count(),0)
    assert.match(await notice.innerText(),/instagram.com\/qa\//)
    fail=false
    await page.locator('#url').fill('https://www.instagram.com/qa-second/')
    await page.getByRole('button',{name:'Analyze',exact:true}).click()
    await toast.waitFor({state:'visible'})
    await page.setViewportSize({width:390,height:844})
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Mobile layout must not overflow horizontally')
    await page.getByRole('button',{name:'Dismiss completion notification'}).click()
    assert.equal(await toast.count(),0)
    assert.match(await notice.innerText(),/qa-second/)
    await page.locator('#analysis-options').evaluate(el=>el.scrollIntoView({block:'start'}))
    await page.clock.runFor(500)
    await mkdir(path.join(root,'.tmp-ui-ready'),{recursive:true})
    await page.screenshot({path:path.join(root,'.tmp-ui-ready','persistent-notice.png')})
  } finally {
    await browser?.close();await server.close()
    for(const [key,value] of Object.entries(previousEnv)) {if(value===undefined)delete process.env[key];else process.env[key]=value}
  }
})
