import test from 'node:test'
import assert from 'node:assert/strict'
import { api, setAccessToken, unlockDemo } from '../src/api.ts'

test('hung fetch is aborted at its deadline', async (t) => {
  t.mock.method(globalThis, 'fetch', (_, options) => new Promise((_, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  }))
  await assert.rejects(api('/test', {}, { timeoutMs: 10 }), /timed out/)
})

test('explicit cancellation interrupts the request', async (t) => {
  t.mock.method(globalThis, 'fetch', (_, options) => new Promise((_, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  }))
  const controller = new AbortController()
  const pending = api('/test', {}, { signal: controller.signal })
  controller.abort()
  await assert.rejects(pending, /cancelled/)
})

test('backend errors remain actionable', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ detail: 'Click Done signing in.' }), { status: 409 }))
  await assert.rejects(api('/test'), /Done signing in/)
})

test('successful responses are returned normally', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json({ post_count: 20 }))
  assert.equal((await api('/test')).post_count, 20)
})

test('demo token is sent in headers and can be cleared',async t=>{
  let expected='Bearer test-demo'
  t.mock.method(globalThis,'fetch',async(_,options)=>{
    assert.equal(options.headers.Authorization,expected)
    return Response.json({ok:true})
  })
  try {
    setAccessToken('test-demo');await api('/api/access')
    setAccessToken('');expected=undefined;await api('/api/access')
  } finally {setAccessToken('')}
})

test('unlock wakes a sleeping backend then authenticates exactly once',async t=>{
  let healthCalls=0, accessCalls=0
  t.mock.method(globalThis,'fetch',async(url,options)=>{
    if(url.endsWith('/api/health')) {
      assert.equal(options.headers.Authorization,undefined)
      healthCalls++
      return healthCalls===1?new Response('Starting Render',{status:503}):Response.json({ok:true})
    }
    accessCalls++;assert.equal(options.headers.Authorization,'Bearer test-demo')
    return Response.json({ok:true})
  })
  try {await unlockDemo('test-demo',{retryDelayMs:0});assert.equal(healthCalls,2);assert.equal(accessCalls,1)}
  finally {setAccessToken('')}
})

test('invalid demo code is not retried and is cleared after failure',async t=>{
  let accessCalls=0
  t.mock.method(globalThis,'fetch',async(url,options)=>{
    if(url.endsWith('/api/health'))return Response.json({ok:true})
    if(url.endsWith('/api/access')) {accessCalls++;return Response.json({detail:'Incorrect code'},{status:401})}
    assert.equal(options.headers.Authorization,undefined);return Response.json({ok:true})
  })
  await assert.rejects(unlockDemo('wrong',{retryDelayMs:0}),/Incorrect code/)
  assert.equal(accessCalls,1);await api('/check-cleared')
})

test('network failures explain backend and CORS configuration',async t=>{
  t.mock.method(globalThis,'fetch',async()=>{throw new TypeError('Failed to fetch')})
  await assert.rejects(unlockDemo('test-demo',{attempts:1}),/FRONTEND_URL or CORS_ORIGINS/)
})

test('HTML success cannot unlock the workspace',async t=>{
  t.mock.method(globalThis,'fetch',async()=>new Response('<html>Not an API</html>'))
  await assert.rejects(unlockDemo('test-demo',{attempts:1}),/unexpected response/)
})
