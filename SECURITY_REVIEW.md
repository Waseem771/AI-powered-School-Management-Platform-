# EduCore AI: Security Review

**Audit date:** 2026-11-04. Local tests ran on database copies. **Production was contacted only with anonymous `GET` requests.** I did not log in to production or try the forged token or default password there, so those two risks are unconfirmed on the live system and should be assumed real.

**Secrets:** no real secrets were found in the local project. `backend/.env` matches `.env.example`, and `GROQ_API_KEY` is blank. `.env` and `school.db` were not reachable at the public repo's `main` branch paths (404). I did not search the git history.

## Do these first

These need **you**, because they touch your production accounts and I will not deploy without approval:

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
| S18 | **`.env` and `school.db` baked into the Modal image** ([modal_app.py:53](backend/modal_app.py:53)) | Exclude with an ignore pattern |
| S19 | **Dependency issues.** Unpinned Python packages. 3 npm production vulnerabilities (1 high, `follow-redirects`; 2 moderate) | Pin versions; `npm audit fix`; test `react-router` update |
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
