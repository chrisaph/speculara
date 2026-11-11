// Speculara compatibility adapter for Instagram's legacy and current feed payloads.
export async function navigateProfile(page, url, wait = () => new Promise((resolve) => setTimeout(resolve, 1000))) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 })
      return
    } catch (error) {
      if (attempt || !/net::ERR_(CONNECTION_RESET|CONNECTION_CLOSED|NETWORK_CHANGED|TIMED_OUT)/.test(String(error))) throw error
      await wait()
    }
  }
}

export function timelinePosts(payload, handle) {
  const posts = new Map()
  const seen = new Set()
  const add = (raw) => {
    if (!raw || typeof raw !== 'object') return
    const code = raw.shortcode || raw.code
    const id = raw.pk || raw.id
    if (!code || !id) return
    const post = {
      id: String(id).split('_')[0], shortcode: code,
      taken_at_timestamp: raw.taken_at_timestamp ?? raw.taken_at,
      is_video: raw.is_video ?? raw.media_type === 2,
      product_type: raw.product_type,
      media_type: raw.media_type,
      display_url: raw.display_url || raw.image_versions2?.candidates?.[0]?.url,
      thumbnail_src: raw.thumbnail_src,
      video_view_count: raw.video_view_count ?? raw.view_count ?? raw.play_count,
      edge_liked_by: raw.edge_liked_by || { count: raw.like_count },
      edge_media_preview_like: raw.edge_media_preview_like,
      edge_media_to_comment: raw.edge_media_to_comment || { count: raw.comment_count },
      edge_media_to_caption: raw.edge_media_to_caption || { edges: [{ node: { text: raw.caption?.text || '' } }] },
    }
    posts.set(post.id, post)
  }
  const walk = (value, depth = 0) => {
    if (!value || typeof value !== 'object' || depth > 50 || seen.has(value)) return
    seen.add(value)
    if (Array.isArray(value)) { for (const item of value) walk(item, depth + 1); return }
    const belongsToProfile = !value.username || value.username.toLowerCase() === handle.toLowerCase()
    for (const [key, child] of Object.entries(value)) {
      if (belongsToProfile && ['edge_owner_to_timeline_media', 'polaris_ordered_timeline_connection', 'xdt_api__v1__feed__user_timeline_graphql_connection'].includes(key)) {
        for (const edge of child?.edges || []) add(edge.node)
      }
      walk(child, depth + 1)
    }
  }
  walk(payload)
  return [...posts.values()]
}
