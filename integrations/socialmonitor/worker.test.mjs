import test from 'node:test'
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { EventEmitter } from 'node:events'
import { execute, validateProfile, collectorError } from './worker.mjs'
import { timelinePosts, navigateProfile } from './instagram-data.mjs'
import { facebookStories } from './facebook-data.mjs'

test('browser crashes preserve the real cause instead of claiming missing installation',()=>{
  const result=collectorError('browserType.launchPersistentContext: Target closed\nBrowser logs:\n<launching> chromium --long-launch-arguments\n[pid=42][err] chrome_crashpad_handler: --database is required\n[pid=42][err] Permission denied')
  assert.match(result,/Browser failed to start/)
  assert.match(result,/crashpad_handler/)
  assert.match(result,/Permission denied/)
  assert.doesNotMatch(result,/setup is incomplete|long-launch-arguments/)
})

test('missing browser executables still get installation guidance',()=>{
  assert.match(collectorError("browserType.launch: Executable doesn't exist at /ms-playwright/chrome"),/Rebuild the hosted backend image/)
})

test('Facebook reads initial Relay stories and excludes other profile posts', () => {
  const story = { __typename: 'Story', post_id: '100', url: 'https://www.facebook.com/joanquizonmakeup/posts/100', comet_sections: {} }
  const unrelated = { ...story, post_id: '200', url: 'https://www.facebook.com/anotherpage/posts/200' }
  const richer = { ...story, creation_time: 1700000000 }
  const found = facebookStories([{ require: [{ data: [story, unrelated, richer] }] }], { handle: 'joanquizonmakeup' })
  assert.equal(found.length, 1)
  assert.equal(found[0].creation_time, 1700000000)
  assert.equal(facebookStories([{ ...story, url: 'https://facebook.com.attacker.test/joanquizonmakeup/posts/100' }], { handle: 'joanquizonmakeup' }).length, 0)
})

test('TikTok preserves supplied save counts and does not fabricate missing counts', async () => {
  await import('./vendor/collect/index.ts')
  const { toPost } = await import('./vendor/collect/tiktok.ts')
  const profile = { handle: 'example' }
  const post = toPost(profile, { id: '123', createTime: 1700000000, statsV2: { collectCount: '42', playCount: '1000' } }, [])
  assert.equal(post.saves, 42)
  assert.equal(post.views, 1000)
  assert.equal(toPost(profile, { id: '123', createTime: 1700000000 }, []).saves, null)
})

test('profile normalization supports the three collectors', () => {
  assert.deepEqual(validateProfile('instagram.com/mrbeast/?x=1'), { network: 'instagram', handle: 'mrbeast', url: 'https://www.instagram.com/mrbeast/' })
  assert.equal(validateProfile('https://www.tiktok.com/@example').handle, 'example')
  assert.equal(validateProfile('facebook.com/profile.php?id=123').url, 'https://www.facebook.com/profile.php?id=123')
})

test('Instagram navigation retries one transient reset and stops after the second failure', async () => {
  let calls = 0
  await navigateProfile({ goto: async () => { if (++calls === 1) throw new Error('net::ERR_CONNECTION_RESET') } }, 'https://www.instagram.com/brand/', async () => {})
  assert.equal(calls, 2)
  calls = 0
  await assert.rejects(navigateProfile({ goto: async () => { calls++; throw new Error('net::ERR_CONNECTION_RESET') } }, 'https://www.instagram.com/brand/', async () => {}), /CONNECTION_RESET/)
  assert.equal(calls, 2)
})

test('Instagram navigation does not retry a closed or cancelled browser', async () => {
  let calls = 0
  await assert.rejects(navigateProfile({ goto: async () => { calls++; throw new Error('Target closed') } }, 'https://www.instagram.com/brand/', async () => {}), /Target closed/)
  assert.equal(calls, 1)
})

test('Instagram current Relay timeline maps real fields and preserves missing metrics', () => {
  const input = { require: [['RelayPrefetchedStreamCache', 'next', [{ __bbox: { result: { data: {
    xdt_api__v1__feed__user_timeline_graphql_connection: { edges: [
      { node: { pk: '123', code: 'ABC', taken_at: 1790000000, media_type: 8, like_count: 9, comment_count: 3, caption: { text: 'Observed caption' } } },
      { node: { pk: '123', code: 'ABC', taken_at: 1790000000, media_type: 8, like_count: 9, comment_count: 3, caption: { text: 'Observed caption' } } },
    ] },
  } } } }]]] }
  const result = timelinePosts(input, 'brand')
  assert.equal(result.length, 1)
  assert.equal(result[0].edge_liked_by.count, 9)
  assert.equal(result[0].edge_media_to_comment.count, 3)
  assert.equal(result[0].edge_media_to_caption.edges[0].node.text, 'Observed caption')
  assert.equal(result[0].video_view_count, undefined)
  assert.equal(result[0].media_type, 8)
})

test('Instagram legacy timeline is supported and unrelated account data is excluded', () => {
  const post = { id: '1', shortcode: 'CODE', taken_at_timestamp: 1790000000, edge_liked_by: { count: 4 } }
  const user = { username: 'brand', edge_owner_to_timeline_media: { edges: [{ node: post }] } }
  assert.equal(timelinePosts({ data: { user } }, 'brand')[0].id, '1')
  assert.deepEqual(timelinePosts({ data: { user } }, 'other'), [])
  assert.deepEqual(timelinePosts({ unrelated: { items: [post] } }, 'brand'), [])
})

test('Instagram preserves supplied play/share/save counts across sparse payloads',()=>{
 const raw={pk:'1',code:'A',ig_play_count:0,share_count:5,saved_count:4}
 const wrap=node=>({data:{user:{username:'brand',edge_owner_to_timeline_media:{edges:[{node}]}}}})
 const result=timelinePosts([wrap(raw),wrap({pk:'1',code:'A'})],'brand')
 assert.equal(result[0].video_view_count,0)
 assert.equal(result[0].share_count,5)
 assert.equal(result[0].save_count,4)
})

test('arbitrary hosts, credentials, ports, post URLs and malformed handles are rejected', () => {
  for (const url of ['http://localhost/test', 'https://instagram.com.evil.test/brand', 'https://user:pass@instagram.com/brand', 'https://instagram.com:8080/brand', 'instagram.com/p/postid', 'instagram.com/accounts/login', 'tiktok.com/@a/video/123']) assert.throws(() => validateProfile(url))
})

function mocks(fail = false) {
  const state = { closed: 0, visible: null, options: null }
  const page = {}
  const deps = {
    dataDir: fileURLToPath(new URL('../../.tmp-collector-test', import.meta.url)),
    openBrowser: async (options) => { state.visible = options; return { newPage: async () => page } },
    closeBrowser: async () => { state.closed++ },
    signedIn: async () => false,
    collectors: { instagram: { collect: async (actual, profile, options) => {
      state.options = options; assert.equal(actual, page); assert.equal(profile.handle, 'brand')
      if (fail) throw new Error('login required')
      return [{ ext_id: '1', likes: 7 }]
    } } },
  }
  return { state, deps }
}

test('collection returns upstream records with bounded options and closes the browser', async () => {
  const { state, deps } = mocks()
  const result = await execute({ action: 'collect', url: 'instagram.com/brand', limit: 999 }, deps)
  assert.equal(result.posts[0].likes, 7)
  assert.equal(state.options.limit, 50)
  assert.equal(state.options.maxComments, 8)
  assert.equal(state.closed, 1)
})

test('collector failures also close the browser', async () => {
  const { state, deps } = mocks(true)
  await assert.rejects(execute({ action: 'collect', url: 'instagram.com/brand' }, deps), /login required/)
  assert.equal(state.closed, 1)
})

test('Facebook requires login and TikTok does not support session login', async () => {
  const { state, deps } = mocks()
  await assert.rejects(execute({ action: 'collect', url: 'facebook.com/brand' }, deps), /requires sign-in/)
  assert.equal(state.closed, 1)
  await assert.rejects(execute({ action: 'login', network: 'tiktok' }, deps), /TikTok is collected while signed out/)
})

test('closing the login page releases a still-running browser context', async () => {
  const { state, deps } = mocks()
  const page = new EventEmitter()
  page.goto = async () => {}
  const ctx = new EventEmitter()
  ctx.pages = () => [page]
  deps.openBrowser = async () => ctx
  const result = await execute({ action: 'login', network: 'instagram' }, deps, (event) => {
    if (event.event === 'login_ready') page.emit('close')
  })
  assert.equal(result.closed, true)
  assert.equal(state.closed, 1)
})

test('Done signing in closes the context without requiring Chrome to exit first', async () => {
  const { state, deps } = mocks()
  const page = new EventEmitter()
  page.goto = async () => {}
  const ctx = new EventEmitter()
  ctx.pages = () => [page]
  deps.openBrowser = async () => ctx
  let finish
  deps.finishLogin = new Promise((resolve) => { finish = resolve })
  await execute({ action: 'login', network: 'instagram' }, deps, (event) => {
    if (event.event === 'login_ready') finish()
  })
  assert.equal(state.closed, 1)
})

test('cancelling an in-flight collector closes its browser', async () => {
  const { state, deps } = mocks()
  deps.collectors.instagram.collect = () => new Promise(() => {})
  deps.cancelled = Promise.resolve()
  await assert.rejects(execute({ action: 'collect', url: 'instagram.com/brand' }, deps), /cancelled/)
  assert.equal(state.closed, 1)
})
