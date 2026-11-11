import test, { before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'vite'
import react from '@vitejs/plugin-react'
import { sentimentView, sourceHref } from '../src/analysis.ts'

let server, panels
before(async () => {
  server = await createServer({ configFile: false, plugins: [react()], server: { middlewareMode: true }, appType: 'custom' })
  panels = await server.ssrLoadModule('/tests/render-panels.tsx')
})
after(async () => { await server?.close() })

const sample = { id: 'c1', text: 'This banana challenge is amazing!', tone: 'pos', kind: 'comment', post_id: 'p1', post_type: 'Reel', source_url: 'https://www.instagram.com/reel/real/', source_kind: 'post' }
const analysis = {
  sentiment: { basis: 'comments', samples: [sample], keywords: [{ w: 'banana', n: 1, s: 'pos', sample_ids: ['c1'] }] },
  demand: { summary: { questions: 2, requests: 1, sampled_comments: 3, request_rate_pct: 66.7 }, ranking: [{ post_id: 'p1', p: 'The real banana reel', q: 2, ask: 1, type: 'Reel', url: sample.source_url, sampled_comments: 3 }], weekly: [{ date: '2026-11-08', questions: 2, requests: 1 }] },
  evidence: { posts: [{ id: 'p1', type: 'Reel', caption: 'The real banana reel', url: sample.source_url }] },
}

test('sentiment renders real keywords with no hard-coded demo keyword assumptions', () => {
  const html = panels.renderSentiment(analysis)
  assert.match(html, /banana/)
  assert.match(html, /This banana challenge is amazing/)
  assert.match(html, /href="https:\/\/www.instagram.com\/reel\/real\/"/)
  assert.doesNotMatch(html, /where to buy|shipping|undefined|NaN/)
})

test('empty sentiment renders an explanation rather than a blank page', () => {
  const html = panels.renderSentiment({})
  assert.match(html, /No collected text matches/)
  assert.doesNotMatch(html, /NaN|undefined/)
})

test('demand uses observed values and gives each reel a source', () => {
  const html = panels.renderDemand(analysis)
  assert.match(html, /The real banana reel/)
  assert.match(html, /2 questions/)
  assert.match(html, /66.7%/)
  assert.match(html, /https:\/\/www.instagram.com\/reel\/real\//)
})

test('comment filters and unsafe sources are handled safely', () => {
  assert.equal(sentimentView(analysis, { query: 'banana' }).samples.length, 1)
  assert.equal(sentimentView(analysis, { query: 'absent' }).samples.length, 0)
  assert.equal(sentimentView(analysis, { tone: 'neg' }).samples.length, 0)
  assert.equal(sourceHref('javascript:alert(1)'), undefined)
  assert.equal(sourceHref('https://user:secret@example.com'), undefined)
})
