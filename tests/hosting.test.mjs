import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'

async function renderer(mode) {
  const server=await createServer({configFile:false,cacheDir:`.tmp-test-cache/hosting-${mode}-${process.pid}`,plugins:[react()],
    define:{'import.meta.env':JSON.stringify({VITE_COLLECTOR_MODE:mode,VITE_API_URL:''})},
    optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true,hmr:false,ws:false,watch:null},appType:'custom'})
  try{return {server,render:await server.ssrLoadModule('/tests/render-panels.tsx')}}
  catch(e){await server.close();throw e}
}

test('hosted demo exposes analysis and explains operator-managed sign-in',async t=>{
  const {server,render}=await renderer('operator')
  try {
    const html=render.renderApp()
    assert.match(html,/demo operator/);assert.match(html,/Analyze CSV \/ Excel data/)
    assert.doesNotMatch(html,/Sign in for comments|Network to sign in to|Done signing in/)
    t.mock.method(globalThis,'fetch',async (url,options)=>{
      assert.equal(url,'/api/upload');assert.equal(options.method,'POST');assert.ok(options.body instanceof FormData)
      return Response.json({post_count:5})
    })
    assert.equal((await render.uploadDataset(new File(['date,likes'],'test.csv'))).post_count,5)
  } finally {await server.close()}
})

test('local demo retains the existing desktop sign-in control',async()=>{
  const {server,render}=await renderer('local')
  try {assert.match(render.renderApp(),/Sign in for comments/)} finally {await server.close()}
})
