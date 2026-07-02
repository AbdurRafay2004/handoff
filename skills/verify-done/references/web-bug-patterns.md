# Recurring web bug patterns

Check these before declaring web work done. They recur across stacks and
account for most "worked locally, broke in production" incidents.

## Build & deploy

- Confirm every env var the change reads exists in the production environment,
  not just locally — "works on my machine" env bugs are the top deploy breaker.
- Check for hardcoded preview/staging URLs when a deploy works in preview but
  breaks on the production domain.
- Mark routes that fetch data at build time as runtime-rendered if the data
  must be fresh; build-time database fetches time out at scale.

## URLs & domains

- Verify the canonical URL points at the production domain. Derive it from a
  server-only env var — client-exposed vars pick up the wrong domain.
- Keep APIs on dedicated subdomains; after a DNS cutover the main domain may
  serve a different app and requests loop back.
- Load every resource over HTTPS; mixed content breaks the browser security
  model.

## Caching

- Invalidate the cache after deploy — or confirm the automatic invalidation
  actually ran before concluding the code is at fault.
- Use a new filename or cache-bust query string when replacing an asset; CDNs
  keep serving old bytes under the same name.
- Keep `max-age` short on resources that change often; aggressive cache
  headers mean users see stale content for days.

## Database & data

- Replace loops-with-queries (N+1) with a join or batch fetch.
- Put a `LIMIT` on any query that can hit a large table; paginate large result
  sets instead of loading them whole.
- Watch for connection-pool exhaustion from parallel build-time fetches.
- Backfill existing rows before adding a `NOT NULL` column.

## Images

- Use a new filename when replacing an uploaded image — the CDN cached the
  old one, so "image not loading after upload" is usually cache, not code.
- Set explicit `width` and `height` on every image to prevent layout shift.
- Optimize hero images for size and format; they dominate LCP.

## Third-party integrations

- Whitelist server IPs, or disable bot challenges on API endpoints, so bot
  mitigation doesn't block legitimate server-to-server calls.
- Add backoff and rate-limit handling to external API calls; production
  traffic hits limits local testing never reached.
- Set explicit timeouts and retries on every network call — no infinite waits,
  and make retried mutations idempotent.

## Security

- Protect revalidation and admin endpoints with a secret token; validate the
  caller on every mutation endpoint.
- Keep PII out of URLs — they land in server logs, browser history, and
  referrer headers.
- Treat anything shipped in the client bundle as public; never give server
  secrets a client-exposing env-var prefix.
- Sanitize user input before it reaches queries, file paths, or HTML.
- Set `Secure`, `HttpOnly`, and `SameSite` on session cookies.

*Adapted from rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
