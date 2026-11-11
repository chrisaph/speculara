import test from 'node:test'
import assert from 'node:assert/strict'
import { api } from '../src/api.ts'

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
