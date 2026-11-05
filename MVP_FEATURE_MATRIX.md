# EduCore AI: MVP Feature Matrix

**Audit date:** 2026-11-04. Each status comes from running the feature, not from seeing its UI. Evidence is in [PROJECT_AUDIT.md](PROJECT_AUDIT.md).

| Status | Meaning |
|---|---|
| ✅ Fully functional | Works, and negative cases behave |
| 🟡 Partially functional | Main path works, with real gaps |
| 🖥️ Frontend only | UI exists with no real backend behind it |
| ⚙️ Backend only | Exists in the backend, not reachable from the UI |
| ❌ Broken | Gives wrong results or fails in normal use |
| ⬜ Missing | Does not exist |

## P0: must work for the MVP

| Feature | Status | Main gap |
|---|---|---|
| **Login** | ✅ | M1: blank form, bcrypt, throttling, clear errors. Branding is M8 |
| **Logout** | ✅ | M1: token revoked on the server, all local data cleared |
| **Protected routes (current source)** | ✅ | All 20 data routes reject anonymous requests |
| **Protected PDFs in production** | ❌ | Fixed in code (M1). Live deployment still returns 200 anonymously until deployed |
| **Dashboard: total students** | ✅ | Real count |
| **Dashboard: fees collected / pending** | ✅ | M2: from payment rows, with an overdue figure |
| **Dashboard: exam performance** | 🟡 | Real averages, but a subject with no marks shows a fake 70.0 |
| **Dashboard: grade distribution** | ✅ | Real |
| **Dashboard: date ranges** | ⬜ | None; all data is all-time |
| **Dashboard: recent activity** | ⬜ | No activity data exists |
| **Dashboard: retry on error** | ❌ | "Try again" can never succeed |
| **Student list, search, grade filter** | ✅ | Works; no section filter |
| **Section filter** | ⬜ | API and UI both lack it |
| **Add student** | 🟡 | Saves. Empty names, invalid grade, section, phone, and date of birth accepted by API |
| **Edit student** | 🟡 | Duplicate roll or null field gives a 500 |
| **Delete student** | 🟡 | Works, but permanently destroys fee and exam history |
| **Student profile page** | ⬜ | No page; data exists only in table rows |
| **Fee invoice list and status filter** | ✅ | M2: shows balance and overdue; summary cards are independent of filters |
| **Issue challan** | ✅ | M2: validated, one per student per month, current-month defaults |
| **Record payment (UI path)** | ✅ | M2: full or part payment, with clear errors |
| **Payment integrity (API)** | ✅ | M2: double, over, negative, and simultaneous payments rejected |
| **Partial payments and balances** | ✅ | M2 |
| **Per-student fee history** | ⚙️ | Available only through a chatbot tool |
| **Payment records view / receipts** | 🟡 | M2: earlier payments shown in the payment dialog. Receipts are M8 |
| **Late fees, sibling concession** | ⬜ | In policy text only |
| **Challan PDF** | 🟡 | Normal names work. `<` crashes it. Urdu not extractable. Letter size rather than A4 |
| **Challan PDF in deployed setup (cross-site)** | ✅ | M1: fetched with the login token. Confirmed in Chrome across two origins, not yet on Vercel and Modal |
| **Marks entry** | 🟡 | Saves and upserts correctly. No range or subject validation in the API |
| **Grade calculation** | 🟡 | Consistent with policy table, but F below 50 conflicts with pass at 40 |
| **Subject-wise results view** | 🟡 | Works. Pass/Fail is wrong when total is not 100. Midterm and final are mixed |
| **Result summaries** | 🟡 | Aggregates mix exam types. "Promoted" shown with no data |
| **Report card PDF** | ❌ | "PROMOTED" with no marks, invented date of birth, canned remark, mixed exams, Urdu name crash |
| **Chatbot UI** | 🟡 | Good layout. Status ticks are hardcoded; prompts hidden on mobile |
| **Chatbot: policy questions** | ✅ | All 7 tested correct, with citations |
| **Chatbot: collection and pending summaries** | ✅ | Correct |
| **Chatbot: single-student lookups** | ❌ | **Returns the wrong student** |
| **Chatbot: grade list** | ❌ | Returns the pending-fee list |
| **Chatbot: memory follow-ups** | 🟡 | Pronouns work, but `"the"` triggers false follow-ups |
| **Chatbot: live vs policy distinction** | 🟡 | Badges exist, but data questions get policy answers marked grounded |
| **Chatbot with Groq tool calling** | ❓ Not tested | No valid key available |
| **Chatbot without Groq** | 🟡 | Stays up and falls back, with the routing bugs above |
| **Responsive layout** | 🟡 | No page overflow. Tiny tap targets; wide tables |
| **Loading states** | 🟡 | Present on all main pages |
| **Empty states** | 🟡 | Present, but also shown wrongly on backend failure |
| **Error states** | ❌ | Only Dashboard and Chatbot have them. Others look like "no data" |
| **Demo data** | 🟡 | Consistent, but stale, thin, and uses public figures' names |
| **DEMO MODE label** | ⬜ | None |

## AI insights (requested in section 4F)

| Feature | Status | Main gap |
|---|---|---|
| Risk score from live records | 🟡 | Runs on real records, using a synthetic-only model |
| Risk overview and filters | ✅ | Works |
| Recommended interventions | 🟡 | Simple rules; reasonable text |
| SHAP explanations | ❌ | Calculated then discarded; labelled SHAP anyway |
| Grade trend | ❌ | Invented; no history exists |
| Risk simulator | 🖥️ | Browser formula presented as the live model |
| Model limitations notice | ⬜ | None |
| Handling of missing data | ❌ | No data reads as "Low risk" and "dues paid" |
| Fees separated from academic risk | ❌ | Unpaid fees alone can produce High risk |

## AI admissions (arrived with the GitHub merge, not in the original brief)

| Feature | Status | Main gap |
|---|---|---|
| Admissions page and API | ❓ Not tested | Login check, optional loading, and the failure message are tested. **A real AI answer is not**, because that needs the Modal token. Not yet audited for quality. Uses a placeholder policy file (`dummy_policy.py`), not the real admission policy |

## P1: improve if the foundation allows

| Feature | Status | Note |
|---|---|---|
| School profile and branding | 🟡 | PDFs use env values, the frontend is hardcoded, and there is no settings page |
| Academic year configuration | ⚙️ | Table exists, barely used; no UI |
| Class and section configuration | ⬜ | Fixed lists in code, copied into the frontend |
| Fee structure configuration | ⚙️ | Table is seeded and never read |
| Teacher accounts and roles | ⬜ | `role` field exists and is never checked |
| Attendance | ⬜ | Policy text only |
| Excel/CSV export | ⬜ | |
| Activity history / audit log | ⬜ | |

## P2: roadmap only, do not build now

Parent app, payroll and HR, full accounting, transport and GPS, library, biometrics, payment gateway, multi-campus, native apps: all ⬜ and correctly out of scope.

**Multi-school isolation: ⬜ not implemented.** This is a single-school system. Do not tell prospects that schools are isolated from each other.

## Summary

| Status | Count |
|---|---|
| ✅ Fully functional | 16 |
| 🟡 Partially functional | 21 |
| 🖥️ Frontend only | 1 |
| ⚙️ Backend only | 3 |
| ❌ Broken | 10 |
| ⬜ Missing | 12 |
| ❓ Not tested | 2 |
| **Total** | **65** |

Counts cover the P0, AI, and P1 tables above, with P2 excluded.
