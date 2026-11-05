# EduCore AI: MVP Implementation Roadmap

**Status:** approved. M0 and M1 are in pull request #1 (not merged or deployed). M2 is complete on branch `mvp/m2-fees`, built on M1. M3 is complete on branch `mvp/m3-records`, built on M2. M4 is complete on branch `mvp/m4-pdfs`, built on M3, and waits for the owner's review of printed samples. M5 is complete on branch `mvp/m5-chatbot`, built on M4, except its test against a real Groq key. M6 is complete on branch `mvp/m6-honest-ai`, built on M5. M7 is complete on branch `mvp/m7-design`, built on M6. M8 is complete on branch `mvp/m8-pages`, built on M7. M9 is complete on branch `mvp/m9-demo`, built on M8, except removing old files, which waits for approval. M10 is complete on branch `mvp/m10-qa`, built on M9, except what needs the owner. See `MVP_FINAL_REPORT.md`. All branches are on GitHub, not merged or deployed.

## Principles

- Keep the stack: FastAPI, SQLModel, React, Tailwind. Nothing found justifies replacing it.
- One module at a time. After each: backend tests, frontend build, API check, and persistence check, with results reported as they actually were.
- Tests come first for each bug fix, so that each fix is proven.
- Database changes are additive and tested on a copy, with a backup and rollback steps.
- No deployment or production change without your explicit approval.

## Decisions (confirmed by the project owner, 2026-11-04)

| # | Decision | Chosen | Effect |
|---|---|---|---|
| D1 | **Version control** | Clone the GitHub repo, compare with this folder, and commit the current state on a new branch | Rollback point before any edits. Nothing is pushed without approval |
| D2 | **Demo school identity** | A clearly fictional school, with synthetic names. City set by D9 | Removes public figures' names and the Islamabad address |
| D3 | **Existing `school.db`** | Leave it untouched. Build a new `demo.db` from an improved seed | Honours the no-reseed rule, and can be regenerated for each demo |
| D4 | **Hosting for the demo** | Stay on Modal with `max_containers=1` and one warm container | One writer removes the data-loss risk, and avoids a slow first load. Warm containers cost money, so check the price before enabling |
| D5 | **Hosting for a real pilot** | Decide later: managed Postgres or a small VPS with SQLite plus backups | Must be settled before any real records |
| D6 | **Risk score design** | Academics only, with real SHAP. Fees appear as a separate admin flag | See M6 |
| D7 | **Partial payments** | Supported | No new tables needed |
| D8 | **Student delete** | Archive by default; permanent delete only with no financial history | Adds one column through a backed-up migration |
| D9 | **Demo city** | **Khairpur** | Demo school, addresses, and phone codes are set in Khairpur. Replaces the earlier Karachi assumption in M9 |

## Milestones

Effort figures are rough working-session estimates, not commitments.

### Stage 1: Stop the bleeding (before any demo)

#### M0. Safety net ✅ complete
- Git baseline on `mvp/foundation`, merged with GitHub `main` so Admissions and other work are kept.
- All Python versions pinned to one set that works on Python 3.13 and resolves for 3.11. `modal_app.py` installs from the same files.
- `pytest` with isolated test databases, so tests can never touch `school.db`.
- Admissions: login required, CrewAI optional, published token removed from code, contact details no longer sent to the AI.

**Done:** a fresh install in a clean environment passes all 14 tests.

**Deployment impact when next deployed:** Modal rebuilds the image with the pinned versions. `MODAL_PROXY_TOKEN_ID` and `MODAL_PROXY_TOKEN_SECRET` must be in the `educore-secrets` Modal secret, or Admissions returns 503 (everything else keeps working). Not deployed yet.

**Admissions follow-ups:** review answer quality and replace the placeholder policy with the real one, once a new token exists. Unused CrewAI variants (`routers/admissions.py`, `services/crew_service.py`, `services/agents/`) and `routers/assemble_educore.py` (a video script in the wrong folder) are candidates for removal in M9, with approval.

#### M1. Authentication and security ✅ complete in code, not deployed
- Require `SECRET_KEY` at startup, except in explicit local dev mode. Scrub the key from docs.
- bcrypt with upgrade at login.
- Admin password from env on first run; no default in production; a change-password endpoint.
- PDFs fetched with bearer token and opened as a blob. This replaces cookie dependence.
- Login rate limit. Exact-origin CORS. Full logout, with token revocation.
- Hide `/docs` in production. Exclude `.env` and `*.db` from the Modal image. `npm audit fix`.

**Done:** 68 backend tests pass on a clean install. Production startup was tested on a copy of `school.db`: the default password was replaced, the hash became bcrypt, and row counts and money totals did not change.

**To deploy, in this order** (full steps in `DEPLOYMENT_GUIDE.md`):
1. Set `SECRET_KEY`, `ADMIN_PASSWORD`, and `FRONTEND_URL` in the Modal secret. Without the first two the backend will not start. Without the third, browsers cannot reach it.
2. Publish the frontend. The old frontend's PDF links stop working on the new backend, so both must go together.
3. `modal deploy modal_app.py`.

**What changes for users:** everyone is signed out once, and Vercel preview addresses are blocked unless listed in `FRONTEND_URL`.

**Database effect:** one new table, `revoked_tokens`, created automatically. No existing table changes. See "Rolling back" in the guide, because bcrypt hashes cannot be read by older code.

**`min_containers=1` is not set**, because it costs money. Check the price and add it before a live demo (D4).

#### M2. Fee and payment integrity ✅ complete in code, not deployed
- Input validation on invoices and payments.
- Payments-based balances, with `partial` status.
- Reject double payments and overpayments; transactional writes.
- Prevent duplicate challans per student per month (migration).
- One shared calculation for dashboard, fees page, and chatbot.
- Real due dates, enabling real "overdue" (migration).

**Done:** all fee negative cases return the right errors, and a test reconciles the Fees page, dashboard, and chatbot against the payments table. Tested with 8 simultaneous payments: exactly one is recorded.

**Simpler than planned:** no new due-date column was needed. New challans store the month and due date in one fixed format, and older text is read tolerantly, so an unreadable date is simply never called overdue. The only schema change is one unique index, applied with `migrate_db.py`. It has been tested on a copy of `school.db`, and **has not been run on the real `school.db` or on Modal**.

**Left for later:** receipts and a per-student fee history page (M8). Late fees and sibling concessions remain unbuilt.

#### M3. Student and results integrity ✅ complete in code, not deployed
- Validation on all student fields and marks. Friendly 409 on duplicate rolls.
- Archive instead of delete (migration, D8).
- Results separated by exam type and academic year.
- Promotion based on the actual policy: 5 of 6 subjects and 50% aggregate.
- Grade label conflict: a 40-49% subject is a "pass" but Grade F, because the policy says both. Kept as the policy states it, with promotion labelled separately. **Waiting for the owner's confirmation.**

**Done:** the report card covers one exam, and its promotion statement comes from the marks under the written policy. With no marks there is no report card. Also moved here from M4, because they were statements the data did not support: the invented date of birth and the canned teacher remark.

**Schema:** one empty column, `students.archived_at`, and one unique index on `results`, applied with `migrate_db.py`. Tested on a copy of `school.db`: backup made, all rows identical, safe to re-run. **It has not been run on the real `school.db` or on Modal, and the app refuses to start on a database without it.**

**Assumption to confirm:** promotion uses Final Term marks alone. The policy also gives a 20/30/50 weightage across quizzes, midterms, and finals, which the system does not record or apply. `academic_years` holds only 2025-2026, and there is no screen to start a new year; M9's demo data sets the right current year.

**Left for later:** a page to review a whole class's promotions, and starting a new academic year.

#### M4. PDFs ✅ complete in code, not deployed
- Escape user text. Handle Urdu names, which needs an embedded Nastaliq-capable font and correct shaping, so this needs a separate test.
- A4 size. Show exam type, dynamic session, and school address. Align challan policy text with reality.

**Done:** special-character and Urdu-name tests pass, including about 1,500 name combinations through the challan. Samples were rendered and checked on screen. **Not done: a review on real printed paper by the owner.**

**Added:** Noto Nastaliq Urdu fonts (SIL Open Font License) and the `uharfbuzz` package, with the owner's approval. Fixes found along the way: a ReportLab crash on some Urdu letter combinations, and a report card table header that was dark on dark.

**Wording:** an invoice stores only a total, so anything above tuition now prints as "Other Charges", not "Examination & Lab". The challan says its amount excludes late charges, because the policy's surcharges are not calculated. The fee policy text now matches the 2-part challan and the actual challan number format.

#### M5. Chatbot correctness ✅ complete in code, not deployed, not tested on real Groq
- **Fix wrong-student bug:** match roll number first, then ID only when explicitly requested.
- Ask which student when names are ambiguous.
- Fix `"he"`/`"the"` routing and the Grade-list mix-up, using word boundaries.
- Add data tools: student counts, top students, subject averages, at-risk list, and per-month collection. Each must have a local fallback.
- Say "I can't answer that" rather than returning unrelated policy text as grounded.
- Bound inputs. Bind sessions to users. Show real AI status from the backend.
- Test against a valid Groq key (**I need one from you for this**).

**Done:** a labelled question set, including students with duplicate names, answers correctly on the local path, and policy questions were checked on both FAISS and TF-IDF. The Groq path's logic is tested against a stand-in, not the real service. **Not done: a test with a valid Groq key, because `backend/.env` has none.**

**Also found and fixed:** results for a named student came from the wrong person, a school-wide or policy question after a student conversation answered about that student, a `%` matched every name, a model reply with no tool behind it was marked as school data, and the page's greeting was being read as the latest message. The header's fixed "AI Stack Active" claim is removed.

**Limits:** counts with a condition ("how many students failed") are declined, not answered. With TF-IDF only, an unrelated question sharing a rare word with a policy can still get that policy's line. At-risk answers still use the current model until M6.

#### M6. Honest AI ✅ complete in code, not deployed
- Remove fees from the academic score. Show "fee follow-up" as a separate administrative flag.
- Use actual SHAP values for explanations, in plain language.
- Remove the invented trend. Compute a real trend only when midterm and final both exist.
- Show "Not enough data" for students without marks.
- Replace "100%" with bands (High, Medium, Low) plus a score, and add a visible note: "Trained on synthetic data. Not validated on real students. A teacher should review before acting."
- Simulator: call the real model, or relabel it as illustrative. Remove the false Ahmed Khan preset.
- Stop computing SHAP during bulk lists, which should speed up the dashboard.

**Done:** every statement on the At-Risk page comes from the student's marks, the model's output, its SHAP values, or the fee ledger. Unpaid fees no longer change a score, and tests prove it. The seeded demo's Bilal Tariq shows High from marks alone, with his fees flagged apart.

**Also fixed:** the band counts changed with the filter, guardian phones were on every card (now only in the one-student view), the model's hand-written score overrides are gone, the At-Risk page shows an error instead of "no data" when the server fails, and fixed dashboard claims ("100% Active", "AI Monitored") are removed.

**Limits:** the model is still trained on made-up students, so its bands and thresholds are not evidence about real ones. The suggested steps are simple rules. Seed data has one exam each, so no real trend shows until both a midterm and final are entered.

### Stage 2: Make it look and feel professional

#### M7. Design system and shared UI ✅ complete in code, not deployed
- Tokens for navy, blue, and cyan. Consistent type, spacing, cards, buttons, and tables.
- Shared `ErrorState`, `EmptyState`, `Modal`, `Toast`, and form fields. Replace `alert()` and `confirm()`.
- Every page distinguishes loading, empty, and failed, with a working Retry.
- 44 px touch targets. Card layout for tables on mobile. Replace the 500-item select with a search.
- Plain language instead of "RAG", "SHAP AI", "ReportLab". Remove hardcoded labels.

**Done:** shared components in `components/ui/`, used by every page. At 375 px, on all 7 pages: no sideways overflow, no control under 44 px, and no tables, only cards. Browser alerts are gone. A student search replaces both whole-school dropdowns. The school name and session in the app's header come from `GET /school/info`, and the login page shows the EduCore AI name and tagline.

**Limits:** form errors appear at the top of a form, not beside each field. The login page has no school name, because it is shown before sign-in. The chatbot's suggested questions are still hidden on phones (M8). Not yet checked on a real phone, at tablet width, or by a person looking at every page.

#### M8. Page improvements ✅ complete in code, not deployed
- **Login:** EduCore AI branding and tagline, validation, DEMO MODE label only in demo mode.
- **Dashboard:** real KPIs only, a date range or month filter, real recent activity (fees and enrolments).
- **Students:** section filter, profile page combining biodata, fees, and results.
- **Fees:** fixed summary cards, payment history, balance, partial payment form, receipt.
- **Results:** exam-type selector, correct Pass/Fail, whole-class entry if time allows.
- **Chatbot:** visible prompts on mobile, clear "From school records" vs "From policy documents" labels.
- School name and session come from one backend config.

**Done:** all of the above, including whole-class marks entry. No database change was needed: the dates on existing records give recent activity. Fees filter by billing month, not by a free date range, because that is how fees are organised here.

**Limits:** the dashboard's filter applies to fee figures only. A receipt's "Received by" line is for signing by hand. Receipts were checked on screen, not on paper. Field-level form errors are still not built: errors appear at the top of a form, except on whole-class marks.

### Stage 3: Demo

#### M9. Demo data and docs ✅ complete in code, not deployed
- New seed: fictional Khairpur school, 100+ synthetic students, 2 exam terms, 3 months of fees, partial payments, and a realistic spread of High, Medium, and Low risk. Current-year dates.
- `DEMO_MODE` banner.
- Write `DEMO_GUIDE.md`, `SAMPLE_DEMO_SCENARIO.md`, `MVP_RELEASE_CHECKLIST.md`.
- Update README, CLAUDE.md, and the deployment guide. Remove clutter (with approval).

**Done:** `seed_demo.py` builds the fictional Roshan Demo Academy, Khairpur, in its own `demo.db`: 120 students, midterm and final, 3 months of fees, and on a 5 November 2026 build 92 Low, 12 Medium, 14 High, and 1 Not enough data. Policies no longer carry one school's name. The scenario was run in a browser, and `test_demo_seed.py` keeps it true.

**Not done:** old files stay until the owner approves removing them (`MVP_RELEASE_CHECKLIST.md`, section 7). The demo has only been run locally. The Final Term marks carry no date, and sit in the current session so that real trends show, though December's exams would not have happened yet on some build dates. The calendar's dates are made up.

#### M10. Full QA and release ✅ complete locally, not deployed
- Run all of [MVP_TESTING_CHECKLIST.md](MVP_TESTING_CHECKLIST.md). Add Playwright for the 10-minute demo flow.
- Rehearse the demo on real phone and desktop.
- Prepare the final report. **Deploy only with your approval.**

**Done:** 53 browser tests on the production build, a browser security policy, speed at 500 students, backup and restore, and `MVP_FINAL_REPORT.md`. **Not done: rehearsal on a real phone, which needs the owner, and deployment, which needs approval.**

### Stage 4: P1, only after the MVP demo works

Priority order, based on what school owners are likely to ask for first. This order is a judgement call and should be checked against real demo feedback.

1. Excel/CSV export.
2. Teacher and accountant roles.
3. Attendance.
4. School profile and academic year settings.
5. Activity history.
6. Class and section configuration.

Each is additive on the current schema.

### Future (P2): not now

Parent app, payroll and HR, full accounting, transport, library, biometrics, payment gateway (JazzCash/Easypaisa), native apps, and multi-tenant SaaS. Multi-tenancy should be the first of these once several schools sign up, and until then each school gets a separate deployment.

## Order and dependencies

```
M0 → M1 → M2 → M3 → M4 ─┐
        └→ M5           ├→ M7 → M8 → M9 → M10
        └→ M6 ──────────┘
```

M2 needs to land before M5 so the chatbot uses the corrected fee calculation. M3 needs to land before M6 so a real trend is possible.

## What is still needed

- ~~Revoke the published Modal proxy token~~ Done by the owner on 2026-11-05.
- A Groq API key in your local `backend/.env` before M5. Do not paste it in chat.
- A new Modal proxy token in your local `backend/.env` before reviewing Admissions.
- Approval to deploy after M1.
