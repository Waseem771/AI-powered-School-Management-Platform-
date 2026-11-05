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
| **Dashboard: exam performance** | ✅ | M3: each student's latest exam only; a subject with no marks is left out |
| **Dashboard: grade distribution** | ✅ | Real |
| **Dashboard: date ranges** | ⬜ | None; all data is all-time |
| **Dashboard: recent activity** | ⬜ | No activity data exists |
| **Dashboard: retry on error** | ❌ | "Try again" can never succeed |
| **Student list, search, grade filter** | ✅ | Works; no section filter |
| **Section filter** | ⬜ | API and UI both lack it |
| **Add student** | ✅ | M3: all fields validated, with clear messages. Urdu names accepted |
| **Edit student** | ✅ | M3: duplicate roll and null fields rejected clearly |
| **Delete student** | ✅ | M3: archive and restore keep all history. Permanent delete refused if any records exist |
| **Student profile page** | ⬜ | No page; data exists only in table rows |
| **Fee invoice list and status filter** | ✅ | M2: shows balance and overdue; summary cards are independent of filters |
| **Issue challan** | ✅ | M2: validated, one per student per month, current-month defaults |
| **Record payment (UI path)** | ✅ | M2: full or part payment, with clear errors |
| **Payment integrity (API)** | ✅ | M2: double, over, negative, and simultaneous payments rejected |
| **Partial payments and balances** | ✅ | M2 |
| **Per-student fee history** | ⚙️ | Available only through a chatbot tool |
| **Payment records view / receipts** | 🟡 | M2: earlier payments shown in the payment dialog. Receipts are M8 |
| **Late fees, sibling concession** | ⬜ | In policy text only |
| **Challan PDF** | ✅ | M4: A4, special characters safe, Urdu printed in Nastaliq |
| **Challan PDF in deployed setup (cross-site)** | ✅ | M1: fetched with the login token. Confirmed in Chrome across two origins, not yet on Vercel and Modal |
| **Marks entry** | ✅ | M3: range, subject, and exam type validated. Stored against the current year |
| **Grade calculation** | 🟡 | Consistent with policy table, but F below 50 conflicts with pass at 40 |
| **Subject-wise results view** | ✅ | M3: Pass/Fail by percentage, with an exam picker |
| **Result summaries** | ✅ | M3: one exam at a time. Promotion follows the written policy, with reasons |
| **Report card PDF** | ✅ | M3: truthful, one exam, policy-based. M4: A4, special characters safe, Urdu printed in Nastaliq |
| **Chatbot UI** | 🟡 | M5: status comes from the server. Prompts are still hidden on mobile |
| **Chatbot: policy questions** | ✅ | All 7 tested correct, with citations |
| **Chatbot: collection and pending summaries** | ✅ | Correct |
| **Chatbot: single-student lookups** | ✅ | M5: right student by roll or name; asks when several match |
| **Chatbot: grade list** | ✅ | M5, with counts, top students, subject averages, at-risk, and monthly collection |
| **Chatbot: memory follow-ups** | ✅ | M5: only real follow-ups use memory |
| **Chatbot: live vs policy distinction** | ✅ | M5: unrelated questions are declined, with no sources |
| **Chatbot with Groq tool calling** | ❓ Not tested | M5: logic tested against a stand-in only. No valid key available |
| **Chatbot without Groq** | ✅ | M5: every path works with no key |
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
| Recommended interventions | 🟡 | M6: fees removed, and worded as steps to consider. Still simple rules |
| SHAP explanations | ✅ | M6: real values, in plain language, one student at a time |
| Grade trend | ✅ | M6: only from a midterm and final of the same year, or none |
| Risk simulator | ✅ | M6: "Try the model" calls the real model, with no fee input |
| Model limitations notice | ✅ | M6: on every view of an estimate |
| Handling of missing data | ✅ | M6: "Not enough data", with no score |
| Fees separated from academic risk | ✅ | M6: no fee input; separate follow-up flag |

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
| ✅ Fully functional | 36 |
| 🟡 Partially functional | 10 |
| 🖥️ Frontend only | 0 |
| ⚙️ Backend only | 3 |
| ❌ Broken | 3 |
| ⬜ Missing | 11 |
| ❓ Not tested | 2 |
| **Total** | **65** |

Counts cover the P0, AI, and P1 tables above, with P2 excluded.
