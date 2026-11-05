# EduCore AI: Security Review

**Audit date:** 2026-11-04. Local tests ran on database copies. **Production was contacted only with anonymous `GET` requests.** I did not log in to production or try the forged token or default password there, so those two risks are unconfirmed on the live system and should be assumed real.

**Update, 2026-11-04 (M0):** the first version of this review covered only the local folder. Comparing with GitHub then exposed S0 and S0a below, which are in GitHub `main` and on production. The full git history was also scanned: S0's token pair is the only credential that matched the patterns searched. No `.env` or database file was ever committed.

**Secrets:** `backend/.env` matches `.env.example`, and `GROQ_API_KEY` is blank.

## Status after M1 (2026-11-05)

**Fixed in the code on `mvp/foundation`. Production stays exposed until this is deployed.**

| IDs | Status |
|---|---|
| S0 | Code fixed. **The token must still be revoked in Modal** |
| S0a, S1 | Fixed in code; live until deployed |
| S2 | Fixed: PDFs are fetched with the login token. Confirmed in real Chrome across two origins |
| S3 | Fixed: production refuses a missing, short, or published key. Key removed from docs. **A new key must be set on Modal** |
| S4 | Fixed: no default password. Production refuses to run on the old one. Removed from the login page and docs |
| S5 | Fixed: bcrypt, with old hashes upgraded at next login |
| S6 | Fixed: 10 failures per username, 30 per address, per 15 minutes |
| S7 | Fixed: exact origins only |
| S8 | Fixed: logout revokes the token and clears all local data, including chat history |
| S11 | Partly: token lifetime cut to 8 hours and auth cookies removed. A browser CSP is still open, and needs testing with the PDF viewer (M10) |
| S17, S20 | Fixed on the API. Frontend gets basic headers through `vercel.json` |
| S19 | Python pinned, `follow-redirects` fixed. **Accepted for now:** 2 moderate `react-router` advisories need a major upgrade to v7. They concern open redirects from dynamic navigation and server rendering; this app navigates only to fixed paths and has no server rendering. Revisit in M10 |
| S10 | Fixed in M3: students are archived, and delete is refused if they have invoices or results |
| S13 | Fixed in M5: question, history, and session id are limited. Rate limiting per user is not built |
| S14 | Fixed in M5: sessions belong to one user. Page-sent history is limited, and used only when the server has none |
| S15 | Partly, in M5: guardian names, phones, and birth dates no longer go to Groq. **Student names, roll numbers, marks, and fees still do when a key is set, so schools must be told.** There is no switch yet beyond leaving the key blank |
| S16, S21 | Fixed in M4 |
| S9, S12 | Still open; planned in P1 and M8 |

**Added in M1:** `POST /auth/change-password`, which ends all older sessions, and a Change Password dialog. No request limit applies to anything except login and password changes; general limits are not built.

## Do these first

These need **you**, because they touch your production accounts and I will not deploy without approval:

0. **Revoke the Modal proxy token** (S0) in the Modal dashboard and create a new one. Do this first: it is public now, and removing it from code does not make it safe.
1. **Set a new random `SECRET_KEY`** in the Modal secret `educore-secrets`. Generate one with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. **Change the production admin password**, once a way to do so exists (module M1).
3. **Deploy the PDF auth fix** once M1 is done. Do not deploy the current source as it stands, because it breaks PDFs (S2).
4. **Check Modal's dashboard** for any Groq key or other secret set there. Rotate the Groq key if it was ever shared.

## Findings

### Critical

| ID | Finding | Evidence | Fix |
|---|---|---|---|
| S0 | **Modal proxy token published on public GitHub** | Written in `backend/school_crew/llm_config.py` and `backend/test_modal.py` since 2026-10-04. Anyone can use it to call your DeepSeek endpoint | **Code fixed in M0** (environment only, with a test that blocks known patterns). **You must still revoke the token.** It remains readable in public git history, so rotation is the real fix |
| S0a | **Live admissions route has no login check** | Per the code on GitHub `main`, `POST /api/admissions-crew/evaluate` has no auth, and the route is listed on production. Anyone could look up a student's name by roll number and trigger paid AI calls. It also sent guardian name and phone to the AI. Not called on production, to avoid cost | **Fixed in M0** (login required, contact details removed). Live until the next deploy |
| S1 | **Live PDFs need no login** | Anonymous `GET /fees/1/pdf` on production returned 200. IDs are sequential, so anyone could walk through every challan, and report cards likely too. Currently synthetic data, but this would expose real children's records | Deploy auth fix (needs S2 first) |
| S2 | **PDF auth design doesn't work across domains** | Cookie is rejected under documented config: logged-in user gets a 401 page. Reproduced locally | Frontend fetches the PDF with the bearer token and opens it as a blob. Works without third-party cookies |
| S3 | **Public JWT signing key** | Key is in `config.py`, `.env.example`, and `DEPLOYMENT_GUIDE.md` on the public repo. Forged 1-year admin token accepted locally | Remove default; refuse to start without a strong key; scrub docs; rotate |
| S4 | **Default admin credentials** | Auto-created in `main.py:30`, prefilled in `Login.jsx:7-8`, and shown on the page and in the public README | First-run password from env; no prefill; demo credentials only in demo mode, and never reused in production |
| S5 | **Weak password hashing** | One fixed salt, one SHA-256 round ([user.py:16](backend/models/user.py:16)) | bcrypt (already a dependency), upgrading old hashes at next login |

### High

| ID | Finding | Evidence | Fix |
|---|---|---|---|
| S6 | **No login rate limiting** | 30 rapid wrong passwords all returned 401, never throttled | Per-username and per-IP limit with lockout. In-memory is acceptable with a single container |
| S7 | **Any `*.vercel.app` site is trusted with credentials** | Preflight from `https://attacker-demo.vercel.app` was approved with `allow-credentials: true`. Anyone can create such a site. Once `COOKIE_SECURE=true` allows cross-site cookies, it could read data as the logged-in user | Remove the regex; allow only your exact domain via `FRONTEND_URL` |
| S8 | **Logout doesn't really log out** | Token stays in `localStorage` and still returned 200 afterwards. By code, chat history containing student data also stays for the next person on a shared office computer | Clear all `educore_*` keys; add a server-side token version so tokens can be revoked |
| S9 | **No role enforcement** | `role` is stored and never checked. The UI always shows "Administrator" | Add `require_role`, then teacher, accountant, and admin permissions (P1). Apply to chatbot tools too |
| S10 | **Students' financial records can be permanently erased** | Delete removed 8 payment rows with no trace | Archive instead; delete allowed only with no financial records; add audit log |
| S11 | **Token stored in `localStorage`** | Any XSS could steal a 24-hour token. No XSS was found: React escapes output, and no `dangerouslySetInnerHTML` appears in the chatbot page | Accept for this MVP since bearer auth is needed across domains. Keep lifetime short and add a CSP header. Revisit if frontend and API share a domain |

### Medium

| ID | Finding | Fix |
|---|---|---|
| S12 | **Student PII shown broadly.** At-Risk lists guardian phone on every card; the chatbot returns phone numbers | Show on detail views only; respect roles |
| S13 | **Unlimited chatbot input.** 200,000 characters accepted. With a Groq key, cost and abuse risk | Limit question and history length; rate-limit per user |
| S14 | **Chat history has no owner.** Any logged-in user can read or delete any session by ID. Client-supplied `history` is trusted and fed to the LLM, which allows prompt-injection attempts. Tools being read-only limits the harm | Bind sessions to the user; ignore or bound client history |
| S15 | **PII sent to Groq.** Tool results with names, phones, and marks go to a third party | Tell schools plainly; add a config switch; send only required fields |
| S16 | **Unescaped text in PDFs.** `<` in a name crashes generation, and ReportLab parses names as markup. `Ali <b>Bold` gave a 500. A `<script>…` name produced a PDF without that name appearing in its extracted text | Escape all user text before `Paragraph()` |
| S17 | **`/docs` and `/openapi.json` public in production** | Disable outside development |
| S18 | ~~`.env` and `school.db` baked into the Modal image~~ | **Resolved** by the GitHub `main` merge, which added an ignore list to `add_local_dir` |
| S19 | **Dependency issues.** Python packages pinned in M0. Still open: 3 npm production vulnerabilities (1 high, `follow-redirects`; 2 moderate) | `npm audit fix`; test `react-router` update (M1) |
| S20 | **No security headers** (HSTS, CSP, X-Content-Type-Options) | Add middleware |
| S21 | **Sensitive filename in header.** Student name is placed in `Content-Disposition`; probably the cause of the Urdu-name 500 | Use roll number plus RFC 5987 encoding |

### Low

- Login uses a generic error message, so there's no user enumeration. ✅ Good.
- Username lookup timing could differ slightly when the user doesn't exist. Low risk here.
- `print()` is used for logging. No passwords or keys were seen in printed output in the code reviewed, but a Groq error is printed whole. Move to structured logging.

## Checklist from your brief

| Item | Status |
|---|---|
| Default demo credentials | ❌ S4 |
| Password hashing | ❌ S5 |
| JWT expiry and validation | ✅ Expired and invalid tokens rejected; 24 hours; algorithm fixed. ❌ Key is public (S3) |
| Protected API routes | ✅ In source. ❌ Live PDFs (S1) |
| Role permissions | ❌ S9 |
| CORS | ❌ S7. Unknown origins rejected ✅ |
| Secrets and env vars | ❌ S3, S18 |
| SQL injection | ✅ Parameterised; injection string safely returned nothing |
| Input validation | ❌ See [DATABASE_AND_API_REVIEW.md](DATABASE_AND_API_REVIEW.md) section 5 |
| Sensitive data in logs | 🟡 Nothing seen; no real logging either |
| Unauthorised data access | ❌ S1, S3 |
| PDF access permissions | ❌ S1, S2 |

## Multi-school statement

This system has **no tenant isolation**. Every table belongs to one school and there is no `school_id`. Each school needs its own separate deployment and database until a dedicated multi-tenant milestone is built and tested. **Do not tell a prospect that several schools are securely isolated.**

## Data protection before any real pilot

These are required before holding real children's data, and I recommend getting local legal advice on them:

- Unique credentials per school and per staff member.
- Daily off-platform backups, with a tested restore.
- A managed database or single-writer guarantee.
- A written agreement on data ownership and deletion.
- Disclosure of AI and third-party processing.
