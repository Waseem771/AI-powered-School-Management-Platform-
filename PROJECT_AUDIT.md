# EduCore AI: Project Audit

**Audit date:** 2026-11-04
**Scope:** all backend and frontend source, the database, deployment files, policy documents, and the running application.
**Code changes made during the audit:** none. `backend/school.db` has the same checksum before and after (`0bc8d949…`). All tests ran on copies in a temporary folder.

Companion documents: [MVP_FEATURE_MATRIX.md](MVP_FEATURE_MATRIX.md), [MVP_IMPLEMENTATION_ROADMAP.md](MVP_IMPLEMENTATION_ROADMAP.md), [DATABASE_AND_API_REVIEW.md](DATABASE_AND_API_REVIEW.md), [SECURITY_REVIEW.md](SECURITY_REVIEW.md), [MVP_TESTING_CHECKLIST.md](MVP_TESTING_CHECKLIST.md).

---

## 1. Verdict

**The foundation is good and worth keeping, but it is not ready to show a school owner yet.**

The ordinary paths work: login, student CRUD, charts, PDFs, and policy search. The problem is what happens just off those paths. In the checks I ran:

- the chatbot returned the wrong child's record
- one fee could be paid three times
- a child with no marks got a report card saying "PROMOTED"
- the AI explanations described a drop in marks that was never measured

A school owner would spot these quickly, and they are the things that lose trust. No rebuild or stack change is needed. See section 8 for the one infrastructure caveat, which is SQLite on Modal.

---

## 2. How this was tested

| Method | Detail |
|---|---|
| Code review | All backend Python and the frontend pages and shared components. `AtRisk.jsx`, `Chatbot.jsx`, and `StatCard.jsx` were read in part, using targeted sections and searches. `ErrorBoundary.jsx` was not read. Policy documents were searched, not read in full |
| Database | Schema and integrity queries on a read-only copy |
| Existing tests | Run against copies |
| API tests | About 70 positive and negative calls using FastAPI `TestClient` on database copies |
| Browser | Real UI at `localhost:5173` against a copy of the database, at 1280 px and 375 px, with the backend up and down |
| Scale | Copy inflated to 500 students and about 5,400 invoices |
| Production | Anonymous `GET` requests only, with no login. PDF response bodies were discarded unread |

**Not tested:**

- Groq with a **valid** API key: none is configured, and `backend/.env` is identical to `.env.example`. An invalid key was tested and falls back correctly.
- Any logged-in behaviour in production.
- Modal concurrency in practice.
- Visual layout: the browser pane was hidden, so there are no screenshots. Layout was measured through the DOM instead. Visual polish still needs a human look.
- PDF appearance: PDF text was extracted, but pages were not viewed.

---

## 3. Findings to read first

| # | Severity | Finding | Evidence |
|---|---|---|---|
| F1 | **Critical, live now** | The production backend serves challan PDFs without login | Anonymous `GET /fees/1/pdf` on the live Modal URL returned **200**. The local source has the auth fix, but it is not deployed |
| F2 | **Critical** | The JWT signing key is public | The key is in `config.py`, `.env.example`, and `DEPLOYMENT_GUIDE.md` in the **public** GitHub repo. A 1-year token I forged with it was accepted locally. Production was not tested, but the guide tells deployers to use this exact key |
| F3 | **Critical** | Default `admin` / `admin123` | Created automatically at startup, prefilled on the login page, printed on the login page, and published in the README |
| F4 | **Critical** | The chatbot returns the **wrong student's** record | "fee dues for Ahmed Khan" answered with **Sana Mir (#141)**. Roll `045` is treated as database ID 45 ([data_assistant_service.py:348](backend/services/data_assistant_service.py:348)). The existing test misses it because its database has only one student |
| F5 | **Critical** | Payments have no integrity checks | The same invoice was paid 3 times, Rs. 1 of 4,000 marked it fully "paid", and Rs. 999,999 and Rs. -100 were accepted ([fees.py:111](backend/routers/fees.py:111)). In the test copy the dashboard showed Rs. 164,000 collected while payment rows totalled Rs. 1,159,900 |
| F6 | **Critical** | Report cards state things that are not true | A student with **no marks** gets "PROMOTED TO NEXT HIGHER CLASS". A missing date of birth prints the invented `15-Aug-2011`. Every card has the same teacher remark. Midterm and final marks are added together with no label |
| F7 | **Critical** | AI explanations are not SHAP, and some are invented | SHAP values are calculated and thrown away (`pass` at [ai_service.py:249](backend/services/ai_service.py:249)). The UI says "Top SHAP Contributing Factors" but shows fixed rules. "Avg marks dropped from 65% to 44%" appears although only **one exam per student exists** |
| F8 | **Critical** | A fresh install breaks every database write | `requirements.txt` has `sqlmodel>=0.0.22`. Versions **0.0.45 and later** reject the project's naive datetimes, so inserts crash. All 3 backend test files fail on 0.0.48 and pass on 0.0.44. A Modal image rebuild would pick up the latest version |
| F9 | **Critical** | The next deployment will break both PDF buttons | Current PDF auth depends on a cookie. With the documented setup (`COOKIE_SECURE` unset), browsers reject that cookie across sites. Reproduced with `127.0.0.1` to `localhost`: the user is logged in, and the PDF link shows raw `{"detail":"Authentication required"}` |
| F10 | **Critical for real data** | SQLite on a Modal Volume can lose data | Modal's docs say "Last write wins" for concurrent changes to one file, distributed locking isn't supported, and other containers see changes only after a reload. No limit on containers is configured |
| F11 | **High** | The local folder is not a git repository | Recent edits (3 Nov) have no version history here, so there is no easy rollback |

---

## 4. Current architecture as found

**Frontend pages:** Login, Dashboard, Students, Fees, Results, AtRisk, Chatbot.
**Components:** Layout, StatCard, ErrorBoundary, and DataTable (**unused**).
**Backend:** 7 routers, 23 endpoints, 6 tables. Services cover AI, PDF, RAG, chatbot data tools, chatbot orchestration, and risk features.

Where the code differs from what the project documents say:

| Documented claim | What the code does |
|---|---|
| Passwords use passlib/bcrypt (`CLAUDE.md`) | Single fixed-salt SHA-256 ([user.py:16](backend/models/user.py:16)). passlib is installed but unused |
| "SHAP explains predictions" (`CLAUDE.md`, README, UI) | SHAP is calculated and discarded. Reasons come from fixed rules |
| `backend/.env` "holds real secrets" | It is byte-identical to `.env.example` |
| Challan has barcodes (README) | No barcode code exists |
| Simulator recalculates with "scikit-learn & SHAP" (UI) | A browser formula unrelated to the model |
| "Predicts dropout and academic failure probability" (Dashboard) | Trained on 300 synthetic rows labelled by a hand-written rule. It predicts neither |
| "Continuously evaluates" (At-Risk) | Calculated on page load |
| Policy: 8-digit challan number, 3-copy voucher | Code produces `CHN-` + 4 digits and 2 copies |
| Policy: promotion requires passing 5 of 6 subjects and 50% aggregate | Code promotes on any overall grade other than F |

---

## 5. Workflow audit

| Workflow | Result |
|---|---|
| Login and logout | Works. Logout leaves the token in `localStorage` ([Layout.jsx:33](frontend/src/components/Layout.jsx:33)), and that token still authenticates |
| Dashboard | Fee, enrolment, and subject numbers matched the seeded data. Collected money is derived from invoice status, not from payments. A subject with no marks shows a made-up **70.0** ([dashboard.py:51](backend/routers/dashboard.py:51)) |
| Add, edit, or delete student | Works. Editing to a duplicate roll number gives a **500**. Empty names and invalid grades are accepted. Delete permanently erases payment history |
| Issue challan | Works. Accepts negative, zero, and duplicate-month challans. The form defaults to **November 2025**, a year out of date |
| Record payment | The UI's normal path works. The API has no safeguards (F5). No partial payments, receipts, or per-student fee history |
| Marks entry | Saves correctly. API accepts 150/100, -5, 50/0, and any subject name |
| PDFs | Generate for normal names. A `<` in a name gives a 500 on both. **An Urdu name gives a 500 on the report card**, and the name could not be extracted from the challan text |
| At-risk | Loads. Honest numbers, but misleading explanations (section 6) |
| Chatbot, policy questions | Good. Retrieved the right document for all 7 policy questions tested |
| Chatbot, data questions | Unreliable (section 6) |

### Frontend problems confirmed in the browser

- **Backend failures look like empty data.** With the backend down, Students says "No matching student records found", Fees shows Rs. 0, At-Risk says "No students found", and Results shows **"Grade N/A: Promoted"**.
- **Dashboard "Try again" can never succeed.** It passes the click event as an abort signal, giving `_config.signal.addEventListener is not a function` ([Dashboard.jsx:75](frontend/src/pages/Dashboard.jsx:75)).
- **Fee cards change with the table filter.** Choosing "Paid" makes Pending Receivables show Rs. 0, which is wrong ([Fees.jsx:111](frontend/src/pages/Fees.jsx:111)).
- **Pass/Fail uses raw marks, not percentage.** 30/50 (60%) shows "Fail" ([Results.jsx:253](frontend/src/pages/Results.jsx:253)).
- **45% shows Grade F and "Pass" together.** Grades fail below 50, but the pass mark is 40.
- **Hardcoded labels on the UI:** "100% Active", "Total Capacity: 500 Pupils", "AI Stack Active", "JWT 256-Bit Auth", "FastAPI + SQLite Engine", "Term Finals".
- **"Load Ahmed Khan Preset"** loads 51% and 3 failed subjects. The real Ahmed Khan (#045) has 82.3% and none.
- **Chatbot status panel** always shows a green tick for Groq, even with no key ([Chatbot.jsx:584](frontend/src/pages/Chatbot.jsx:584)).
- **"Overdue" is not calculated.** Every pending invoice is labelled overdue. Due dates are free text, so lateness cannot be computed.

### Responsive design (measured at 375 px)

- No horizontal page overflow on any page. Tables scroll inside their own container, and the drawer navigation has good accessibility.
- Tables need sideways scrolling: Fees is 761 px wide in a 341 px space, Students 663 px.
- Almost all controls are short tap targets under 36 px: Students 160 of 161, Fees 77 of 78, At-Risk 52 of 57.
- The chatbot's suggested questions are **hidden on mobile**, so a phone user sees none.

---

## 6. AI review

### At-risk model

| Item | Finding |
|---|---|
| Training data | 300 **synthetic** rows, generated at every server start ([ai_service.py:42](backend/services/ai_service.py:42)) |
| Labels | A hand-written points rule. The forest simply re-learns that rule (99.1% agreement with the rule). **This is not real-world accuracy** |
| Real-world validation | None |
| `train_on_students` | Never called |
| `grade_trend` feature | Invented from current marks ([risk_features.py:37](backend/services/risk_features.py:37)), then fed back to users as if it were historical |
| Score adjustments | Fixed min/max rules override the model |

**Fee status drives the risk score, which you asked to avoid.** Identical academics, changing only unpaid invoices:

| Avg marks | Failed subjects | 0 unpaid | 1 | 2 | **3 unpaid** |
|---|---|---|---|---|---|
| 85% | 0 | 0 | 0 | 17 | **89 (High)** |
| 70% | 0 | 0 | 0 | 5 | **87 (High)** |
| 55% | 1 | 20 | 65 | 82 | 85 |

An 85% student becomes "High risk" because of family finances. No live student hits this today only because seed data keeps the top students' invoices low.

**Missing data reads as good news.** A student with no marks and no invoices scores 0 (Low), with the reasons "All semester dues paid on time" and "Passed all enrolled curriculum subjects".

**Overstated certainty.** Three students display "100%" risk.

**No limitations notice.** The At-Risk page does not mention synthetic data, limitations, or human review.

### Chatbot

Tested with no Groq key, so all of this is the local path. **The Groq tool-calling path has not been tested and needs a real key.** The roll-number bug in F4 sits in the shared tool code, so Groq would hit it too whenever it passes a roll number.

| Question | Result |
|---|---|
| Policy questions (7) | ✅ Correct document |
| Collection summary, pending-fee list | ✅ Correct |
| Fee dues / results / profile by name | ❌ **Wrong student** |
| "List all students in Grade 8" | ❌ Returns the *pending fees* list instead |
| "How many students are in the school?" | ❌ Asks for a student name |
| "Which students are at risk?" | ❌ Asks for a student name (no such tool exists) |
| "How much fee was collected this month?" | ❌ Quotes the fee policy, marked `grounded=True` |
| "Which subject has the lowest average?" | ❌ Quotes the exam policy, marked `grounded=True` |
| Follow-up "When are the winter holidays?" | ❌ Returns a student profile, because `"he"` matches inside `"the"` ([school_assistant_service.py:339](backend/services/school_assistant_service.py:339)) |
| Suggested prompt "roll number 5" | ❌ No such roll; returns database ID 5 |
| "Who is the prime minister?" | ⚠️ Asks for a student name instead of declining |
| Invalid Groq key | ✅ Falls back correctly |
| "Delete all students", "admin password" | ✅ Nothing harmful. The tools are read-only |

Four seeded names are also duplicated (Ahmed Khan, Bilal Tariq, Daniyal Shah, Zoya Malik), and the bot never asks which one is meant. Once the ID bug is fixed, this becomes the next wrong-student risk.

---

## 7. Demo-readiness problems

- **Stale dates:** session "2025-2026" is hardcoded, and all invoices date from Sept to Nov 2025. Today is November 2026.
- **Hardcoded school:** "Al-Noor Academy" is hardcoded in Login, Layout, Dashboard, Chatbot, and `index.html`, ignoring `SCHOOL_NAME`. The school is in Islamabad, while the target market is Karachi, Sukkur, and Khairpur.
- **Real people in the sample data:** students include Maryam Nawaz, Sana Mir, Hania Amir, and Iqra Aziz. Guardians include Babar Azam, Wasim Akram, and Shoaib Akhtar. In a Pakistani demo this will look unprofessional and needs to go.
- **A stray record:** student "waseemshaikh" (roll `01232`) has no marks or invoices. Removing it needs your approval.
- **Thin data:** one exam term only, one main fee month, and **0 Medium-risk students**, so one risk band is always empty.
- **No DEMO MODE label** anywhere.
- **Technical wording aimed at judges:** "ReportLab", "RAG", "SHAP AI", "FAISS". The README still says "Hackathon Edition". School owners need plain language.
- **Slow first impressions:** one production request took 13.7 s (one sample, likely a cold start). The first policy question took 11.2 s locally with the model already downloaded.

### What already works well

Keep these:

- All 20 data routes reject anonymous requests in the current source. Only login, logout, and the root status route are public (plus `/docs` and `/openapi.json`).
- SQL queries are parameterised. An injection string returned no rows.
- Chatbot tools are read-only and allowlisted.
- The local fallback works without Groq.
- Policy retrieval is good.
- Roll-number duplicate check on create works, as do 404s for missing records.
- Mobile navigation drawer has a focus trap and Escape handling.
- Seed data is internally consistent: every paid invoice has one matching payment, and there are no orphans.
- All at-risk feature logic is in one place.

---

## 8. Performance and infrastructure

Measured locally at 500 students and about 5,400 invoices:

| Endpoint | Time | Size |
|---|---|---|
| `/students` | 0.02 s | 88 KB |
| `/fees` | 0.27 s | 1.27 MB, no pagination |
| `/dashboard/stats` | **3.0 s** | 1 KB |
| `/ai/at-risk` | **3.3 s** | 189 KB |

Target-size schools will wait 3 s for the dashboard. Much of that is likely per-student SHAP work whose result is discarded, which makes it a cheap fix. This cause is inferred, not profiled.

**Modal plus SQLite is the one real architecture question.** It is acceptable for a controlled demo if limited to one container. It is not acceptable for a pilot holding a school's real records. Details and options are in the roadmap.

**Other infrastructure findings:**

- `modal_app.py:53` copies all of `backend/` into the image, including `.env` and `school.db`.
- The production URL is hardcoded in [client.js:6](frontend/src/api/client.js:6).
- There are no pinned dependency versions, no logging setup (only `print`), no health endpoint, and no backups.
- `npm audit` reports 3 production vulnerabilities (1 high in `follow-redirects`, 2 moderate including `react-router`).
- The JS bundle is 745 KB in a single chunk.

**Clutter to remove once you approve:** the empty `EduCore_AI_Implementation_Plan--.py`, empty `New Microsoft Word Document.docx`, `backend/log.txt`, duplicate `run_*_fix.bat` files, unused `DataTable.jsx`.

---

## 9. Test results (actually executed)

| Test | Environment | Result |
|---|---|---|
| `test_data_assistant.py` | SQLModel 0.0.48 (fresh install) | ❌ Crash on first insert |
| `test_school_assistant.py` | SQLModel 0.0.48 | ❌ Crash on first insert |
| `test_backend.py` | SQLModel 0.0.48 | ❌ Crash on first insert |
| `test_data_assistant.py` | SQLModel 0.0.44 | ✅ Pass |
| `test_school_assistant.py` | SQLModel 0.0.44 | ✅ Pass |
| `test_backend.py` | SQLModel 0.0.44, database copy | ✅ Pass |
| `session.test.js` | Node 24 | ✅ 2 of 2 |
| `vite build` | Output to temp folder | ✅ Builds, with a chunk-size warning |

**The passing tests give little assurance.** They cover normal paths only, and none of them caught F4 to F7.
