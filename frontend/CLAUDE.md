# CLAUDE.md (frontend)

Frontend guidance for Claude Code. Project-wide context is in [../CLAUDE.md](../CLAUDE.md).

## Run

Run from `frontend/`.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # output in dist/
node --test src/lib/session.test.js
```

There is no lint, formatter, or `npm test` script. The backend must be running on `localhost:8000` (or `VITE_API_URL` set) for any page to load data.

## Stack

React 18 (plain JS/JSX), Vite 5, Tailwind 3, React Router 6, Axios, Recharts, lucide-react, clsx, tailwind-merge.

## Structure

- `src/App.jsx`: routes `/login`, `/dashboard`, `/students`, `/fees`, `/results`, `/at-risk`, `/chatbot`. Protected routes render inside `components/Layout.jsx`.
- `src/api/client.js`: the single axios instance and `api` object. Adds the bearer token from `localStorage`, redirects to `/login` on 401. Add every new endpoint here, never call axios directly from a page.
- `src/pages/`: `Login`, `Dashboard`, `Students`, `Fees`, `Results`, `AtRisk`, `Chatbot`.
- `src/components/`: `Layout` (sidebar and accessible mobile drawer), `DataTable`, `StatCard`, `ErrorBoundary`.
- `src/lib/session.js`: `getStoredUser()` reads `educore_user` from `localStorage` with a safe default.

## Conventions

- Style with Tailwind utility classes; the visual language is slate neutrals with blue/indigo accents and rounded-2xl cards.
- Pages fetch in `useEffect`, show a loading state, and show a friendly error with a retry (see `Dashboard.jsx`). Abort in-flight requests on unmount where it is cheap.
- PDFs open as plain links to the backend PDF URLs and authenticate via the HttpOnly cookie.
- Keep accessibility intact in `Layout` (focus trap, Escape to close the drawer).
- Do not add `console.log`; existing code only uses `console.error`/`warn` for failures.

## Local storage keys

`educore_user`, `educore_token` (auth token), `educore_chat_history`, `educore_chat_session_id`, `educore_chat_memory_enabled`.

## Gotchas

- `ProtectedRoute` only checks `educore_user`; the backend does the real authorization.
- The Risk Simulator in `AtRisk.jsx` is a local formula, not the real model.
- Production builds fall back to a hardcoded Modal URL when `VITE_API_URL` is unset; update `.env.production` when the backend URL changes.
- The backend CORS allows ports 5173 and 5174 only (plus `FRONTEND_URL` and `*.vercel.app`).
