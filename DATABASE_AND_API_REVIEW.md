# EduCore AI: Database and API Review

> **Update, M2:** fee findings in sections 2, 4, 5, 6, and 8 are fixed on branch `mvp/m2-fees`, as designed in section 8. A unique index replaces the planned billing-period and due-date columns; see the roadmap.

> **Update, M3:** student and results findings in sections 2, 4, 5, and 6 are fixed on branch `mvp/m3-records`. An `archived_at` column replaces the planned `status` column. Student averages now use one calculation, total over total. Foreign keys remain unenforced, and the delete rule keeps orphans from arising through the app.

**Audit date:** 2026-11-04. Inspected on read-only copies. `backend/school.db` was not changed.

## 1. Database as found

SQLite, journal mode `delete`. `PRAGMA foreign_keys` is **0**, so the declared foreign keys are not enforced.

| Table | Rows | Notes |
|---|---|---|
| `users` | 1 | `admin`, 64-character SHA-256 hash |
| `students` | 51 | 50 seeded plus `waseemshaikh` (roll `01232`) |
| `invoices` | 54 | 35 paid (Rs. 140,000), 19 pending (Rs. 75,500) |
| `payments` | 35 | Exactly one per paid invoice |
| `results` | 300 | All "Final Term" |
| `academic_years` | 1 | `2025-2026` |
| `fee_structures` | 5 | Seeded, never read by application code |

```
students 1──* invoices 1──* payments
students 1──* results
academic_years 1──* fee_structures
academic_years 1┄┄* results    (column exists with no FK; never filtered on)
users                          (no link to anything)
```

### Integrity of existing data: clean

Orphan rows: 0. Duplicate rolls: 0. Paid invoices with no payment: 0. Pending invoices with a payment: 0. Payment amount differing from invoice amount: 0. Out-of-range marks: 0. Duplicate result keys: 0.

**This matters:** existing data can move to a payments-based balance model with no data repair.

### Data quality issues

- Four duplicated names: Ahmed Khan (045, 101), Bilal Tariq (012, 102), Daniyal Shah (018, 106), Zoya Malik (023, 127).
- Public figures' names used for students and guardians.
- `month` and `due_date` are free text, so overdue logic and date filters are impossible.
- Money is stored as `FLOAT`. For this scale and whole-rupee amounts the risk is low, but sums should be rounded consistently.

## 2. Schema gaps

| Gap | Effect | Proposed fix | Destructive? |
|---|---|---|---|
| No `UNIQUE(student_id, month)` on invoices | Duplicate monthly challans | Add a billing-period field and unique index | No |
| No `UNIQUE(student_id, subject, exam_type, academic_year_id)` on results | Only application code prevents duplicates | Add unique index | No |
| No `is_active` / archive on students | Delete destroys financial history | Add `status` column; archive instead of delete | No |
| `due_date` is text | No overdue calculation | Add real date column, backfill by parsing existing values | No |
| Foreign keys off | Orphans possible | Enable `PRAGMA foreign_keys=ON` per connection | No |
| No `recorded_by` / audit log | No accountability | P1: add `audit_log` table | No |
| Results ignore academic year | Years would mix together | Filter by current year | No |

**No destructive schema change is needed.** Every change above is additive.

## 3. Migration approach

The project has no migrations, and the documented method is "delete the database and reseed". **That stops today.**

Proposed process for every schema change:

1. Back up to a timestamped copy using SQLite's backup API.
2. Add an idempotent script in `backend/migrations/`.
3. Test it on a copy, and compare row counts and money totals before and after.
4. Only then run it on the real file, with your approval.
5. Write down rollback steps: restore the backup, because all changes are additive.

**Production Modal volume:** needs the same process, run as a Modal function, and only with explicit approval.

## 4. API inventory

All routes below were called. "Anon" is the status with no token against the **current source**.

| Method and route | Anon | Validation found |
|---|---|---|
| `POST /auth/login` | Public | Required fields only. No rate limit |
| `POST /auth/logout` | Public | Clears cookie only |
| `GET /auth/me` | 401 | OK |
| `GET /students` | 401 | Search is safe. `%` matches everything |
| `POST /students` | 401 | Duplicate roll OK. **Nothing else validated** |
| `GET /students/{id}` | 401 | 404 and 422 correct |
| `PUT /students/{id}` | 401 | **500** on duplicate roll or null field |
| `DELETE /students/{id}` | 401 | Hard-deletes financial records |
| `GET /fees` | 401 | Invalid status silently returns empty. No pagination |
| `POST /fees/generate` | 401 | Student existence only |
| `POST /fees/{id}/pay` | 401 | Invoice existence only |
| `GET /fees/{id}/pdf` | 401 | **500** on `<` in name |
| `GET /results/{student_id}` | 401 | 404 correct |
| `POST /results` | 401 | Student existence only |
| `GET /results/{student_id}/report-card/pdf` | 401 | **500** on `<` or Urdu name |
| `GET /dashboard/stats` | 401 | OK |
| `GET /ai/at-risk`, `/{student_id}` | 401 | 404 correct. Invalid filter returns empty |
| `POST /chatbot/ask` | 401 | Blank rejected. **200,000 characters accepted** |
| `GET/DELETE /chatbot/history/{session_id}` | 401 | No ownership check |
| `GET /chatbot/topics` | 401 | School name hardcoded |
| `GET /`, `/docs`, `/openapi.json` | 200 | Public, including in production |

## 5. Negative-case results

| Input | Expected | Actual |
|---|---|---|
| Wrong password | 401 | ✅ 401 |
| Missing login field | 422 | ✅ 422 |
| Duplicate roll on create | 400/409 | ✅ 400 |
| Duplicate roll on update | 409 | ❌ **500** |
| `name: null` on update | 422 | ❌ **500** |
| Empty name, guardian, phone | 422 | ❌ 200 |
| Whitespace roll number | 422 | ❌ 200 |
| "Grade 99", section "Z" | 422 | ❌ 200 |
| Phone `not-a-phone`, date of birth `banana` | 422 | ❌ 200 |
| Date of birth 2099 | 422 | ❌ 200 |
| Unknown student or invoice | 404 | ✅ 404 |
| Non-numeric ID | 422 | ✅ 422 |
| SQL injection string in search | Safe | ✅ No rows |
| Invoice Rs. -500 or Rs. 0 | 422 | ❌ 200 |
| Duplicate invoice same month | 409 | ❌ 200 |
| Month `banana`, due date `??` | 422 | ❌ 200 |
| Pay an already-paid invoice | 409 | ❌ 200, extra payment row |
| Pay Rs. 1 of 4,000 | Partial | ❌ Fully paid |
| Pay Rs. 999,999 of 4,000 | 422 | ❌ 200 |
| Pay Rs. -100 | 422 | ❌ 200 |
| Pay Rs. 0 | 422 | ❌ 200, records **full amount** (`0 or invoice.amount`) |
| Payment mode `bitcoin` | 422 | ❌ 200 |
| Marks 150/100 | 422 | ❌ 200, graded A+ |
| Marks -5 | 422 | ❌ 200 |
| Total marks 0 | 422 | ❌ 200, grade N/A |
| Subject "Basket Weaving", exam "Pizza Test" | 422 | ❌ 200 |
| Expired or garbage token | 401 | ✅ 401 |

**A note on 500 errors in the browser:** FastAPI's unhandled-error response may lack CORS headers, so the frontend would see a network error and show only a generic message. I did not check this directly in a browser; validating inputs properly avoids the case.

## 6. Calculation review

| Calculation | Finding |
|---|---|
| Collected | **Wrong source.** Sums invoice amounts where status is paid, ignoring what was actually received ([dashboard.py:27](backend/routers/dashboard.py:27)). Same in the chatbot's collection summary, so all three figures need one shared function |
| Student average | Dashboard and risk use total/total; chatbot uses mean of percentages. These differ when subject totals differ |
| Overall grade | Mixes midterm and final |
| Promotion | Any overall grade other than F. Policy requires 5 of 6 subjects passed and 50% aggregate |
| Pass/Fail UI | Raw marks ≥ 40 instead of percentage |
| Challan split | Tuition capped at Rs. 3,500; remainder labelled "Examination & Lab" regardless of what it really is |
| Challan number | Random 4 digits, widening to 6 when crowded, checked for uniqueness. Fine but not policy-compliant (8 digits) |

## 7. API consistency

- No shared response envelope. Keep it simple: use normal FastAPI responses and one consistent error shape, rather than rewriting every route.
- Creates return 200 instead of 201. Conflicts use 400 instead of 409.
- No pagination on `/students`, `/fees`, or `/ai/at-risk`. Add limit and offset when needed for 500-student schools.
- Fixed lists (grades, sections, subjects) exist in `config.py` **and** are copied into `Students.jsx` and `Results.jsx`. Add one `GET /config` endpoint as the single source.

## 8. Recommended target for fees

No new tables are needed:

- **Paid amount** = sum of `payments.amount_paid` for the invoice.
- **Balance** = invoice amount minus paid amount.
- **Status** = derived and stored: `pending`, `partial`, or `paid`.
- **Payment rules:** amount above 0, amount no greater than the remaining balance, valid mode, already-paid invoices rejected with 409, all inside one transaction.
- **Dashboard** uses payments as the source.

The current data is already consistent with this model.
