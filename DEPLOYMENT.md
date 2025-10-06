# Deploying Klerno Labs

This guide covers two recommended paths:

- Docker Compose on a single VM (nginx → app → Postgres/Redis)
- GitHub Container Registry (GHCR) build/push + pull to your infra

## Prerequisites

- Docker and Docker Compose v2
- Domain/DNS pointed to your server (optional)
- Strong secrets ready (JWT_SECRET, Postgres password)

## Option A: Compose on a VM

1. Create a `.env` file with production values (not committed):

```
# .env (do not commit!)
APP_ENV=production
JWT_SECRET=your-super-strong-64char-secret
DATABASE_URL=postgresql+psycopg://klerno:klerno@db:5432/klerno
POSTGRES_USER=klerno
POSTGRES_PASSWORD=your-strong-db-pass
POSTGRES_DB=klerno
```

1. Build and start stack:

```
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

1. Verify:
- http://SERVER_IP/ → professional landing
- http://SERVER_IP/docs → FastAPI docs

1. Logs and health:

```
docker compose -f docker-compose.prod.yml logs -f app
```

## Option B: Build and push image (GHCR)

A workflow is provided to build and push `ghcr.io/<org>/klerno-labs:latest`.

1. Set GitHub repo secrets:
- `GHCR_PAT` or use GITHUB_TOKEN permissions

1. Trigger the workflow or push to main; then pull on your server:

```
docker login ghcr.io -u <USER> -p <TOKEN>
docker pull ghcr.io/<org>/klerno-labs:latest
```

1. Run with compose by referencing the image instead of building locally. Update `docker-compose.prod.yml` to use `image: ghcr.io/<org>/klerno-labs:latest` for service `app`.

## Notes

## Render (optional)

1. Push your branch to GitHub and ensure it contains `render.yaml`.
1. Create a new Blueprint in Render and point it at your repo.
1. This blueprint uses an external DB/cache model. Before deploying, set Web Service env vars:
   - `APP_ENV=production`
   - `PORT=8000`
   - `HOST=0.0.0.0`
   - `JWT_SECRET=<strong 64+ char secret>`
   - `DATABASE_URL=<your Neon connection string>`
   - `REDIS_URL=<your Upstash redis url>` (optional)
1. Deploy; health check path is `/health`.
