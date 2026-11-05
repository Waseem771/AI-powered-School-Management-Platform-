# CLAUDE.md (frontend)

Frontend guidance for Claude Code. Project-wide context is in [../CLAUDE.md](../CLAUDE.md).

## Run

Run from `frontend/`.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # output in dist/
npm test
```

There is no lint or formatter. The backend must be running on `localhost:8000` (or `VITE_API_URL` set) for any page to load data.

## Stack

React 18 (plain JS/JSX), Vite 5, Tailwind 3, React Router 6, Axios, Recharts, lucide-react, clsx, tailwind-merge.

## Structure

- `src/App.jsx`: routes `/login`, `/dashboard`, `/students`, `/fees`, `/results`, `/at-risk`, `/chatbot`, `/admissions`. Protected routes render inside `components/Layout.jsx`.
- `src/api/client.js`: the single axios instance and `api` object. Adds the bearer token from `localStorage`, redirects to `/login` on 401. Add every new endpoint here, never call axios directly from a page.
- `src/pages/`: `Login`, `Dashboard`, `Students`, `Fees`, `Results`, `AtRisk`, `Chatbot`, `Admissions`.
- `src/components/`: `Layout` (sidebar and accessible mobile drawer), `DataTable`, `StatCard`, `ErrorBoundary`.
- `src/lib/`: `session.js` (stored user, `clearSession`), `pdf.js` (open a fetched PDF), `errors.js` (`apiErrorMessage`, safe text for users).

## Conventions

- Style with Tailwind utility classes; the visual language is slate neutrals with blue/indigo accents and rounded-2xl cards.
- Pages fetch in `useEffect`, show a loading state, and show a friendly error with a retry (see `Dashboard.jsx`). Abort in-flight requests on unmount where it is cheap.
- PDFs use `components/PdfButton.jsx`, which fetches them with the bearer token. Plain links cannot authenticate.
- Keep accessibility intact in `Layout` (focus trap, Escape to close the drawer).
- Do not add `console.log`; existing code only uses `console.error`/`warn` for failures.

## Local storage keys

`educore_user`, `educore_token` (auth token), `educore_chat_history`, `educore_chat_session_id`, `educore_chat_memory_enabled`.

## Gotchas

- `ProtectedRoute` only checks `educore_user`; the backend does the real authorization.
- Risk scores are written with `scoreText` from `lib/risk.js`, as "Score 85 of 100", never as a percentage. Any page showing an estimate shows `MODEL_NOTE`.
- Production builds need `VITE_API_URL`; update `.env.production` and Vercel when the backend URL changes. The backend must list this site in `FRONTEND_URL`.
- In development, the backend CORS allows ports 5173 and 5174, plus `FRONTEND_URL`. Production allows `FRONTEND_URL` only.
