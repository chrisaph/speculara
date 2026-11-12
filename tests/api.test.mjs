import test from 'node:test'
import assert from 'node:assert/strict'
import { api, setAccessToken } from '../src/api.ts'

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
