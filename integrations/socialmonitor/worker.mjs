import { mkdir } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import { createInterface } from 'node:readline'

export const NETWORKS = ['instagram', 'facebook', 'tiktok']

export function validateProfile(raw) {
  const u = new URL(/^https?:\/\//i.test(raw) ? raw : `https://${raw}`)
  if (!['http:', 'https:'].includes(u.protocol) || u.username || u.password || u.port) throw new Error('Use a public profile URL.')
  const host = u.hostname.toLowerCase().replace(/^(www\.|m\.)/, '')
  const network = { 'instagram.com': 'instagram', 'facebook.com': 'facebook', 'tiktok.com': 'tiktok' }[host]
  if (!network) throw new Error('SocialMonitor supports Instagram, Facebook and TikTok profile links.')
  let handle = u.pathname.replace(/^\/|\/$/g, '')
  if (network === 'tiktok') handle = handle.replace(/^@/, '')
  if (network === 'facebook' && handle === 'profile.php') handle = u.searchParams.get('id') || ''
  if (!/^[\w.-]{1,100}$/.test(handle) || (network === 'instagram' && ['p', 'reel', 'reels', 'explore', 'accounts'].includes(handle))) throw new Error('Paste the profile link, rather than an individual post or login page.')
  const url = network === 'tiktok' ? `https://www.tiktok.com/@${handle}` : network === 'facebook' && /^\d+$/.test(handle) ? `https://www.facebook.com/profile.php?id=${handle}` : `https://www.${host}/${handle}/`
  return { network, handle, url }
}

export async function execute(input, deps, emit = () => {}) {
  const { collectors, openBrowser, closeBrowser, signedIn, dataDir } = deps
  if (input.action === 'status') return { installed: true, networks: NETWORKS }
  if (input.action === 'login') {
    if (!['instagram', 'facebook'].includes(input.network)) throw new Error('Sign-in is supported for Instagram and Facebook. TikTok is collected while signed out.')
    await mkdir(dataDir, { recursive: true })
    const ctx = await openBrowser({ visible: true })
    let timer
    try {
      const page = ctx.pages()[0] || await ctx.newPage()
      const closed = new Promise((resolve) => ctx.once('close', resolve))
      // Chrome can keep its process/context alive after its last window closes.
      const pageClosed = new Promise((resolve) => page.once('close', resolve))
      await page.goto(input.network === 'instagram' ? 'https://www.instagram.com/accounts/login/' : 'https://www.facebook.com/login/', { waitUntil: 'domcontentloaded', timeout: 45000 })
      await page.bringToFront?.()
      emit({ event: 'login_ready' })
      timer = setTimeout(() => closeBrowser(), 10 * 60 * 1000)
      await Promise.race([closed, pageClosed, deps.finishLogin || new Promise(() => {})])
      return { closed: true }
    } finally { clearTimeout(timer); await closeBrowser() }
  }
  if (input.action !== 'collect' && input.action !== 'smoke') throw new Error('Unknown collector action.')
  const profile = input.action === 'collect' ? validateProfile(input.url) : null
  await mkdir(dataDir, { recursive: true })
  let timer
  try {
    emit({ event: 'progress', message: 'Opening the saved browser session…' })
    const context = await openBrowser()
    const page = await context.newPage()
    if (input.action === 'smoke') {
      await page.goto('data:text/html,<title>Speculara collector ready</title>')
      return { browser: await page.title() }
    }
    const notes = []
    let read = 0
    const options = {
      range: 'all', limit: Math.min(50, Math.max(5, Number(input.limit) || 20)),
      known: new Set(), due: new Map(), comments: true,
      maxComments: 8, usedSession: false,
      log: (line) => {
        notes.push(line); console.error(line)
        emit({ event: 'progress', message: /comments read/.test(line) ? `Reading post ${++read} of up to ${Math.min(50, Math.max(5, Number(input.limit) || 20))}…` : line })
      },
    }
    const session = await signedIn(context, profile.network)
    if (profile.network === 'facebook' && !session) throw new Error('Facebook requires sign-in. Use Sign in for comments, then close the sign-in window and retry.')
    const timeout = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Collection timed out. Try a profile with fewer posts or sign in and retry.')), Math.max(180000,options.limit*10000+15000)) })
    emit({ event: 'progress', message: 'Loading posts and comment samples…' })
    const cancelled = (deps.cancelled || new Promise(() => {})).then(() => { throw new Error('Collection cancelled.') })
    const posts = await Promise.race([collectors[profile.network].collect(page, profile, options), timeout, cancelled])
    return { ...profile, posts, signed_in: session, notes: notes.slice(-10) }
  } finally { clearTimeout(timer); await closeBrowser() }
}

async function main() {
  let browser
  let lines
  const emit = (value) => console.log(JSON.stringify(value))
  try {
    let finishLogin, cancel
    const finishRequested = new Promise((resolve) => { finishLogin = resolve })
    const cancelRequested = new Promise((resolve) => { cancel = resolve })
    const input = process.argv[2] === 'login' ? { action: 'login', network: process.argv[3] || 'instagram' } : await new Promise((resolve, reject) => {
      lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
      let started = false
      lines.on('line', (line) => {
        try {
          const message = JSON.parse(line)
          if (!started) { started = true; resolve(message) }
          else if (message.action === 'finish_login') finishLogin()
          else if (message.action === 'cancel') cancel()
        } catch (e) { if (!started) reject(e) }
      })
      lines.on('close', () => { if (!started) reject(new Error('Missing collector request.')) })
    })
    browser = await import('./vendor/collect/browser.ts')
    const { collectors } = await import('./vendor/collect/index.ts')
    const { DATA_DIR } = await import('./vendor/db.ts')
    const deps = { ...browser, collectors, dataDir: DATA_DIR, finishLogin: finishRequested, cancelled: cancelRequested,
      signedIn: async (context, network) => {
        if (network === 'tiktok') return false
        const key = network === 'instagram' ? 'sessionid' : 'c_user'
        return (await context.cookies(`https://www.${network}.com`)).some((c) => c.name === key && !!c.value)
      },
    }
    emit({ ok: true, data: await execute(input, deps, emit) })
  } catch (e) {
    const message = e instanceof Error ? e.message : 'SocialMonitor collection failed.'
    const error = /net::ERR_(CONNECTION_RESET|CONNECTION_CLOSED|NETWORK_CHANGED|TIMED_OUT)/.test(message)
      ? 'The connection to the social network was interrupted. Please try again shortly.'
      : /executable doesn't exist|browserType\.launch|cannot find package/i.test(message) ? 'Browser setup is incomplete. Run npm run collector:setup, then npm run collector:browser from speculara.' : message.replace(/Open "Sign in to networks"/g, 'Use "Sign in for comments" in Speculara')
    emit({ ok: false, error })
    process.exitCode = 1
  } finally { lines?.close(); process.stdin.pause(); await browser?.closeBrowser().catch(() => {}) }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) await main()
