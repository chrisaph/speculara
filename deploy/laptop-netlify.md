# Laptop backend + existing Netlify frontend

The laptop runs collection, Gemma API calls and its original saved browser profile. Netlify stays at `https://speculara.netlify.app`. A temporary Cloudflare HTTPS tunnel exposes only the protected backend. Keep the laptop awake and online. This is a private demo setup, not permanent hosting.

1. Install Python/backend and collector dependencies as in `backend/README.md`. Keep Gemma/Supabase keys in ignored `backend/.env`.
2. Install the official Cloudflare `cloudflared` client, either on PATH or at `.tmp-laptop-demo/bin/cloudflared.exe`. On this laptop the official Windows client has already been downloaded and checksum-verified.
3. In PowerShell at the repository root, run:

   ```powershell
   .\backend\.venv\Scripts\python.exe deploy/laptop-demo.py start
   ```

   Leave it running. The API binds only to `127.0.0.1:8010`. Before opening a tunnel, the launcher checks that authentication is required, the demo key works, visitor sign-in/cancel is forbidden, and Netlify's exact origin passes CORS. It prints a temporary `https://....trycloudflare.com` URL. No secret is printed. Credentials and logs are in the ignored `.tmp-laptop-demo` folder, restricted to your Windows account.
4. Set Netlify's `VITE_API_URL` to that tunnel URL and trigger a production deploy. Keep `VITE_COLLECTOR_MODE=operator` and the existing access-code screen. Do not add any secret to Netlify. You can get the current URL with:

   ```powershell
   .\backend\.venv\Scripts\python.exe deploy/laptop-demo.py status
   ```

5. Copy the **new laptop demo code** privately, then paste it into Speculara's access-code field:

   ```powershell
   .\backend\.venv\Scripts\python.exe deploy/laptop-demo.py code
   ```

   The old Render demo token does not unlock this backend. The laptop operator token is separate and is loaded automatically by the commands below; no copy/paste or remote desktop is needed.
6. In a second local terminal, open a real Chrome sign-in window on the laptop:

   ```powershell
   .\backend\.venv\Scripts\python.exe deploy/laptop-demo.py login instagram
   ```

   Use `facebook` instead for Facebook. Complete sign-in manually in the local window, then run:

   ```powershell
   .\backend\.venv\Scripts\python.exe deploy/laptop-demo.py finish
   ```

   Never sign in to the operator desktop on Render for this route. TikTok collection uses public pages. Local sign-in reduces the cloud-network problem but does not guarantee platform access.
7. Test sample/CSV data, chat and strategy, then request five actual posts from Netlify. Only one collection or sign-in runs at a time. Private Insights/sales still need your own exported metrics.
8. To stop, run `laptop-demo.py stop` or press Ctrl+C in the launcher terminal. It stops the public tunnel first, closes its own collector session and stops its own backend. It does not stop unrelated local servers.

Quick Tunnel hostnames change on restart. Each new URL requires updating `VITE_API_URL` and redeploying Netlify. Local credentials and browser profile remain on your laptop. Do not commit `.tmp-laptop-demo`, `.env`, browser cookies or keys. The Cloudflare client must stay running; Quick Tunnels have no uptime guarantee and are intended for development/testing. No email-login layer is used because cross-origin API requests must pass through; the backend enforces its own demo/operator credentials.

If the client reports DNS lookup timeouts for `argotunnel.com`, the tunnel has not connected. The launcher shuts down rather than leaving a misleading URL running. Try another permitted network or ask the network administrator about Cloudflare Tunnel access. No system DNS/firewall changes are made by this launcher. Do not change Netlify's URL until `status` says `ready` and its public health endpoint works. A Quick Tunnel allocation message alone is not proof of connectivity.

The old Render service is no longer used once Netlify points here. You may suspend it in Render and disable its operator desktop; this launcher does not delete or alter that service.

Sources: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) and [official client downloads](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/).
