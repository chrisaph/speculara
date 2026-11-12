import { build } from 'vite'
import { pathToFileURL } from 'node:url'
export function backendOrigin(value) {
  let url
  try {url=new URL(value)}catch{throw new Error('Set VITE_API_URL to your HTTPS Render backend origin in Netlify environment variables.')}
  if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||url.pathname!=='/'||['localhost','127.0.0.1','::1','[::1]'].includes(url.hostname))throw new Error('VITE_API_URL must be a public HTTPS backend origin without credentials, query, fragment or path.')
  return url.origin
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  process.env.VITE_API_URL=backendOrigin(process.env.VITE_API_URL)
  process.env.VITE_COLLECTOR_MODE='operator'
  process.env.VITE_REQUIRE_ACCESS_CODE='true'
  await build()
}
