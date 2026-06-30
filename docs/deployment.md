# Deployment — Vercel + Railway

Frontend deploys to **Vercel**; backend deploys to **Railway**. Both use the same **Neon Postgres** database (configured via `DATABASE_URL`).

Deploy **backend first** — the Vercel build bakes `NEXT_PUBLIC_API_URL` at build time and needs a live Railway URL.

## Prerequisites

- GitHub repo connected to Vercel and Railway
- [Neon](https://console.neon.tech) project with a **pooled** connection string
- Data loaded into the `benchmarking` schema (run the pipeline locally against the same Neon DB):

```bash
cp .env.example .env   # set DATABASE_URL
poetry install
poetry run python scripts/reset_schema.py   # first time or after schema changes
poetry run python -m pipeline.run --airlines ek,ba,ai
```

## 1. Railway (backend)

1. Create a new **service** from your GitHub repo.
2. Set **root directory** to the **repo root** (`/`), not `backend/`.
3. Railway picks up [`railway.toml`](../railway.toml) and [`nixpacks.toml`](../nixpacks.toml) automatically (Nixpacks + Poetry install).
4. Set environment variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Neon pooled connection string |
| `DB_SCHEMA` | `benchmarking` |
| `CORS_ORIGINS` | `https://<your-vercel-production-domain>` (update after Vercel deploy if needed) |
| `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` |
| `EDIT_PASSWORD` | Shared password for compare-page editing (required in production) |
| `SESSION_SECRET` | Random 32+ character key for signing edit session tokens |

5. Deploy and verify:

```bash
curl https://<railway-service>.up.railway.app/health
# → {"status":"ok"}

curl https://<railway-service>.up.railway.app/api/v1/airlines/summary
# → JSON array (empty if DB not seeded)
```

Copy the public Railway URL — you need it for Vercel.

## 2. Vercel (frontend)

1. Import the repo in [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js** (auto-detected). Build command: `npm run build` (default).
4. Add environment variable for **Production** and **Preview**:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://<railway-service>.up.railway.app` (no trailing slash) |

5. Deploy. Because `NEXT_PUBLIC_*` vars are embedded at build time, **redeploy** after changing `NEXT_PUBLIC_API_URL`.

See [`frontend/.env.example`](../frontend/.env.example) for local dev.

## 3. Post-deploy CORS check

1. Open your Vercel production URL in the browser.
2. Open DevTools → Network; confirm API calls to the Railway URL succeed (no CORS errors).
3. If the production Vercel domain differs from what you set in `CORS_ORIGINS`, update that variable on Railway and redeploy the backend.

Preview deployments (`*.vercel.app`) are allowed via `CORS_ORIGIN_REGEX`.

## Environment variables reference

| Variable | Platform | Required | Purpose |
|----------|----------|----------|---------|
| `DATABASE_URL` | Railway | Yes | Neon Postgres connection |
| `DB_SCHEMA` | Railway | No | Default `benchmarking` |
| `CORS_ORIGINS` | Railway | Yes (prod) | Comma-separated allowed origins |
| `CORS_ORIGIN_REGEX` | Railway | Recommended | Regex for Vercel preview URLs |
| `EDIT_PASSWORD` | Railway | Yes (prod) | Shared password for compare editing |
| `SESSION_SECRET` | Railway | Yes (prod) | HMAC key for edit session tokens |
| `NEXT_PUBLIC_API_URL` | Vercel | Yes | Railway API base URL |

Full list: [`.env.example`](../.env.example).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Railway build fails | Poetry / Nixpacks install error | Check build logs; ensure service root is repo root |
| Railway 502 | App not binding to `$PORT` | Confirm start command in `railway.toml` uses `--port $PORT` |
| `/health` fails | Service not started | Check Railway deploy logs |
| Empty UI on Vercel | DB not seeded or wrong `DATABASE_URL` | Run pipeline locally; verify Railway `DATABASE_URL` |
| CORS errors in browser | Origin not allowed | Set `CORS_ORIGINS` to prod URL; set `CORS_ORIGIN_REGEX` for previews |
| API calls to localhost | `NEXT_PUBLIC_API_URL` not set on Vercel | Set env var and **redeploy** frontend |
| Vercel build-time fetch errors | Railway not live during first build | Deploy Railway first, then Vercel |

## Config files

| File | Purpose |
|------|---------|
| [`railway.toml`](../railway.toml) | Railway deploy settings |
| [`nixpacks.toml`](../nixpacks.toml) | Nixpacks Poetry install |
| [`Procfile`](../Procfile) | Alternative web process definition |
| [`frontend/vercel.json`](../frontend/vercel.json) | Vercel project config (placeholder) |

## Out of scope (Phase 1)

- Dockerfile (Nixpacks is used instead)
- Scheduled pipeline runs on Railway
- CI/CD GitHub Actions
- Custom domains (handled by Vercel / Railway dashboards)
