# Deployment

Phase 1 has no user login, so deploy **only on a trusted network** (VPN / office LAN).

1. Run the API and web containers with the same `TASKIFY_API_TOKEN`; keep the API port private.
2. Set `TASKIFY_ENV=production` and a random `DJANGO_SECRET_KEY` on the web service.
3. Put [Caddyfile](./Caddyfile) in front for automatic HTTPS; replace the hostname.
4. Exposing the app to the internet requires the follow-up `002-user-authentication` feature first.
