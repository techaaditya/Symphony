# Symphony Dashboard

Next.js (App Router) + TypeScript + Tailwind dashboard for the Symphony agent society. Consumes
the FastAPI server in `../symphony/api/` — start that first (`uvicorn symphony.api.app:app`).

## Getting started

```bash
cp .env.local.example .env.local   # points at the local API by default
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Structure

- `app/` — the four views (`live`, `ledger`, `conflicts`, `benchmark`) plus the overview page.
- `lib/api.ts` — typed client for the §12 REST endpoints and the `/sim/stream` SSE URL.
- `lib/types.ts` — TypeScript types mirroring `symphony/api/schemas.py` / `symphony/models.py`.
- `components/` — shared shell components (`NavBar`) and view placeholders (`StubView`).

Theme tokens in `app/globals.css` follow the project's dataviz palette (light default, dark
selected via `prefers-color-scheme`).

## Checks

```bash
npm run lint
npx tsc --noEmit
npm run build
```
