// Speculara adapter: collectors need only the browser data path, not upstream SQLite.
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
export const DATA_DIR = resolve(process.env.SPECULARA_COLLECTOR_DATA_DIR || fileURLToPath(new URL('../../../backend/.socialmonitor', import.meta.url)))
