# EduCore AI: MVP Testing Checklist

**Baseline run:** 2026-11-04, source before any fixes, on database copies.

| Mark | Meaning |
|---|---|
| ✅ | Tested and passed |
| ❌ | Tested and failed |
| ⬜ | Not tested yet |

The **Target** for every line is ✅. Use the blank Retest column as modules land, and only mark what was actually run.

## Automated suite

| Check | Baseline | Retest |
|---|---|---|
| `test_data_assistant.py` on a fresh install | ❌ crash (SQLModel 0.0.48) | ✅ M0 |
| `test_school_assistant.py` on a fresh install | ❌ crash | ✅ M0 |
| `test_backend.py` on a fresh install | ❌ crash | ✅ M0 |
| Same three with SQLModel 0.0.44 | ✅ | not needed now |
| Full suite, clean install, without CrewAI | ⬜ | ✅ M0: 14 passed |
| App starts without CrewAI | ⬜ | ✅ M0 |
| Pinned stack reads and writes a copy of existing `school.db` | ⬜ | ✅ M0 |
| Pins resolve for Python 3.11 (Modal) | ⬜ | ✅ M0, dry run only |
| `modal_app.py` loads with the new install method | ⬜ | ✅ M0, not deployed |
| Admissions: anonymous rejected, 503 on failure, no contact details sent | ⬜ | ✅ M0 |
| Admissions: failure message shown on the page | ⬜ | ✅ M0, in browser |
| Admissions: real AI answer | ⬜ | ⬜ needs token |
| No known credential patterns in project files | ❌ | ✅ M0 |
| `npm test` (session tests) | ✅ 2 of 2 | ✅ M0 |
| `vite build` | ✅ (chunk-size warning) | ✅ M0 |
| `npm audit --omit=dev` clean | ❌ 3 issues | |
| Tests cannot touch real `school.db` | ❌ `test_backend.py` uses it by default | ✅ M0, checksum matched |

## Authentication and authorisation

| Check | Baseline | Retest |
|---|---|---|
| Valid login succeeds | ✅ | |
| Wrong password gives 401 with a generic message | ✅ | |
| Missing field gives 422 | ✅ | |
| All protected routes reject anonymous requests (source) | ✅ | |
| Production PDFs reject anonymous requests | ❌ | |
| Expired token rejected | ✅ | |
| Garbage token rejected | ✅ | |
| Token signed with the documented key rejected | ❌ | |
| App refuses to start without a strong key | ❌ | |
| Login page has no prefilled or printed password | ❌ | |
| Repeated wrong passwords get throttled | ❌ | |
| Passwords hashed with bcrypt | ❌ | |
| Logout clears all local data | ❌ | |
| Token unusable after logout | ❌ | |
| Unknown origin rejected by CORS | ✅ | |
| Arbitrary `*.vercel.app` rejected by CORS | ❌ | |
| PDF opens when frontend and API are on different domains | ❌ | |
| Role permissions enforced | ⬜ not built | |

## Students

| Check | Baseline | Retest |
|---|---|---|
| Create valid student and see it after reload | ✅ API | |
| Duplicate roll on create gives clear error | ✅ | |
| Duplicate roll on edit gives clear error | ❌ 500 | |
| Null field on edit rejected | ❌ 500 | |
| Empty name, guardian, phone rejected | ❌ | |
| Whitespace roll rejected | ❌ | |
| Invalid grade, section rejected | ❌ | |
| Invalid phone, date of birth rejected | ❌ | |
| Future date of birth rejected | ❌ | |
| Unknown ID gives 404 | ✅ | |
| Search handles SQL characters safely | ✅ | |
| Delete preserves fee and exam history | ❌ | |
| Section filter | ⬜ not built | |
| Profile page | ⬜ not built | |

## Fees

| Check | Baseline | Retest |
|---|---|---|
| Generate valid challan | ✅ | |
| Negative or zero amount rejected | ❌ | |
| Duplicate month rejected | ❌ | |
| Junk month or date rejected | ❌ | |
| Form defaults to current month | ❌ | |
| Unknown student gives 404 | ✅ | |
| Full payment recorded and persists | ✅ | |
| Second payment on paid invoice rejected | ❌ | |
| Partial payment shows correct balance | ❌ | |
| Overpayment rejected | ❌ | |
| Negative or zero payment rejected | ❌ | |
| Invalid payment mode rejected | ❌ | |
| Dashboard collected equals sum of payments | ❌ after bad payments | |
| Summary cards stay correct under filters | ❌ | |
| "Overdue" only when past due date | ❌ | |

## Results and grades

| Check | Baseline | Retest |
|---|---|---|
| Enter and update marks; upsert, no duplicates | ✅ | |
| Marks above total rejected | ❌ | |
| Negative marks rejected | ❌ | |
| Total of 0 rejected | ❌ | |
| Unknown subject or exam type rejected | ❌ | |
| Pass/Fail uses percentage | ❌ | |
| Midterm and final shown separately | ❌ | |
| Promotion follows the 5-of-6 and 50% policy | ❌ | |
| No "Promoted" without results | ❌ | |

## PDFs

| Check | Baseline | Retest |
|---|---|---|
| Challan generates for normal name | ✅ | |
| Report card generates for normal name | ✅ | |
| Name with `&` | ✅ | |
| Name with `<` | ❌ 500 | |
| Urdu name, report card | ❌ 500 | |
| Urdu name displays correctly on challan | ❌ not extractable; check by eye | |
| No invented date of birth | ❌ | |
| No canned teacher remark | ❌ | |
| Exam type shown | ❌ | |
| Session is current | ❌ | |
| A4 page | ❌ Letter | |
| Print preview checked by a person | ⬜ | |

## Dashboard

| Check | Baseline | Retest |
|---|---|---|
| Total students matches database | ✅ 51 | |
| Grade distribution matches database | ✅ | |
| Fee totals match seeded data | ✅ | |
| No invented averages for empty subjects | ❌ 70.0 | |
| No hardcoded claims ("100% Active" etc.) | ❌ | |
| Retry works after failure | ❌ | |
| Under 1.5 s at 500 students | ❌ 3.0 s | |

## AI at-risk

| Check | Baseline | Retest |
|---|---|---|
| Explanations come from real SHAP values | ❌ | |
| No invented trend statements | ❌ | |
| Unpaid fees can't make a strong student High risk | ❌ 85% to 89 High | |
| Missing data shows "Not enough data" | ❌ shows Low, 0 | |
| Limitations notice visible | ❌ | |
| Human review notice visible | ❌ | |
| Simulator honest about what it is | ❌ | |
| App still works if SHAP is unavailable | ⬜ fallback exists in code, not run | |

## Chatbot

| Check | Baseline | Retest |
|---|---|---|
| Works with no Groq key | ✅ | |
| Invalid Groq key falls back | ✅ | |
| **Valid Groq key: all paths** | ⬜ no key | |
| Policy questions answered with citations | ✅ 7 of 7 | |
| Name lookup returns the **right** student | ❌ | |
| Roll lookup returns the **right** student | ❌ | |
| Duplicate names prompt for clarification | ❌ | |
| Grade list returns the grade list | ❌ | |
| Count, top student, at-risk, and subject questions | ❌ | |
| Follow-up pronouns | ✅ | |
| Policy follow-up not hijacked by "the" | ❌ | |
| Unknown questions declined honestly | 🟡 some are | |
| Write requests cause no writes | ✅ read-only tools | |
| Oversized input rejected | ❌ | |
| Blank input rejected | ✅ | |
| AI status reflects reality | ❌ | |

## Frontend states

| Check | Baseline | Retest |
|---|---|---|
| Backend down: Dashboard shows error | ✅ by 5 s; zeros shown first in dev mode | |
| Backend down: Students shows error | ❌ says no records | |
| Backend down: Fees shows error | ❌ Rs. 0 | |
| Backend down: Results shows error | ❌ "Promoted" | |
| Backend down: At-Risk shows error | ❌ | |
| Backend down: Chatbot shows error | ✅ | |
| Session expiry redirects to login | ⬜ code exists, not run in browser | |
| Forms show field-level validation | ❌ | |
| No dead buttons or links | ⬜ needs a full click-through after M8 | |

## Responsive

| Check | Baseline | Retest |
|---|---|---|
| No page overflow at 375 px, all pages | ✅ | |
| Drawer navigation works at 375 px | ✅ | |
| Tap targets at least 44 px | ❌ | |
| Tables usable without sideways scroll | ❌ | |
| Chatbot prompts available on mobile | ❌ | |
| Tablet (768 px) | ⬜ | |
| Real phone | ⬜ | |
| Screenshot review by a person | ⬜ pane was hidden | |

## Database safety

| Check | Baseline | Retest |
|---|---|---|
| Existing data has no integrity problems | ✅ | |
| Foreign keys enforced | ❌ | |
| Duplicate-preventing unique indexes | ❌ | |
| Migration tested on a copy | ⬜ none yet | |
| Backup and restore tested | ⬜ | |
| `school.db` unchanged by audit | ✅ checksum matched | |

## 10-minute demo walkthrough (run after M9)

| Step | Baseline | Retest |
|---|---|---|
| 1. Log in with safe demo credentials | ❌ uses public default | |
| 2. Dashboard overview | 🟡 stale data, hype labels | |
| 3. Search and open a student | ❌ no profile page | |
| 4. Show invoice and payment | 🟡 no payment history view | |
| 5. Generate challan | 🟡 works locally; ❌ cross-site after deploy | |
| 6. Enter marks | ✅ | |
| 7. Generate report card | 🟡 same deploy problem; inaccurate statements | |
| 8. Ask the AI about demo data | ❌ wrong student | |
