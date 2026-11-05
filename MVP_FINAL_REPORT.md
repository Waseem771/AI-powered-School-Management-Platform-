# EduCore AI: MVP Final Report

**Date:** 5 November 2026. **Code:** branch `mvp/m10-qa`, which holds all of M0 to M10. **All branches are on GitHub. Nothing from M2 onward is merged or deployed.**

## Verdict

**Ready for a local demonstration with the fictional school.** The full 10-minute demo runs start to finish, as an automated browser test and with the sample data.

**Not ready to go online until you complete section 8, and not ready for a real school's records until section 6 of [MVP_RELEASE_CHECKLIST.md](MVP_RELEASE_CHECKLIST.md) is done.** The live site still runs older code with known security problems.

## 1. Summary of improvements

The project began as a 2-day hackathon build that looked finished but gave wrong answers. It is now:

- **Correct:** fee totals come from real payments, and part payments work. Marks from different exams are never mixed, and promotion follows the written policy. The chatbot no longer reports on the wrong student.
- **Safe:** published passwords and keys are gone from the code, PDFs need a login, and sign-ins are limited. Students are archived rather than erased, and database changes are additive, with a backup.
- **Honest:** the risk estimate uses marks only, with the model's real reasons and a visible notice. Failures no longer look like "no records", and fixed claims such as "AI Stack Active" are gone.
- **Usable:** one design across all pages, works at phone size, with a student search, student profiles, receipts, whole-class marks, and plain language.
- **Demonstrable:** a fictional Khairpur school in its own database, with a guide and a script.

## 2. Completed modules

| Milestone | Delivered |
|---|---|
| M0 Safety net | Rollback point, pinned packages, isolated tests, GitHub code merged |
| M1 Security | Sign-in hardening, PDF access, production safeguards |
| M2 Fees | Accurate ledger, part payments, duplicate protection |
| M3 Records | Archive and restore, one exam at a time, promotion by policy, database upgrade tool |
| M4 PDFs | A4, safe with any text, Urdu names printed in Nastaliq |
| M5 Chatbot | Right student, asks when unsure, 6 new data tools, declines what it cannot answer |
| M6 Honest AI | Marks-only estimate, real SHAP reasons, real trends, separate fee flag, real model trial |
| M7 Design | Shared components, loading, failed, and empty states, 44 px controls, cards on phones |
| M8 Pages | Student profile, receipts, whole-class marks, month filter, recent activity, section filter, demo label |
| M9 Demo | Roshan Demo Academy, demo guide, scenario, release checklist, new README |
| M10 QA | 53 browser tests, security policy, longer-list handling, and the fixes in section 3 |

By the feature matrix's own count, 49 of 65 features are fully working, up from fewer than half at the audit.

## 3. What final QA found and fixed

| Found by | Problem | Fix |
|---|---|---|
| Looking at pages | Money was cut off on stat cards at laptop width, from my own M7 change | Cards redesigned, with a test |
| Looking at pages | The Fees list on a phone was over 100,000 pixels tall | Lists now show 25 at a time, with Show more |
| Looking at pages | Chatbot examples named students not in the demo school | Examples are now school-wide |
| Browser tests | Student-name links were too small to tap | Enlarged |
| Browser tests | Keyboard focus could fall out of a dialog when the student list closed | Fixed |
| Backend tests | A policy file's title could beat the real rules in keyword search | Titles no longer searched |

## 4. Test results

All run on 5 November 2026, on a clean install of the pinned packages (Python 3.13.11).

| Check | Result |
|---|---|
| Backend tests | **487 passed**, 0 failed. `pip check` clean |
| Frontend tests | **52 passed**, 0 failed |
| Frontend build | **Succeeds**, with a chunk-size warning only |
| Browser tests, in Microsoft Edge | **53 passed** on the production build, with security headers, at 1280, 768, and 375 px wide |
| Speed at 500 students | Slowest page under 0.45 s, against a 1.5 s target. Measured on this computer, not online |
| Backup and restore | Worked: data deleted on purpose came back exactly, and the app read it |
| `school.db` | Unchanged throughout M4 to M10 |

**The browser tests cover:** all 9 demo steps, refused entries, opening PDFs, session expiry, sign-out, server failures with Try again, archive, restore, delete, and keyboard use in dialogs.

## 5. Not verified

Please do not assume these work:

- **Anything on Modal or Vercel.** No deployment was made, so nothing has run in its real environment. That includes the new security policy, tested only on a local production build.
- **Real Groq answers.** `backend/.env` has no key, so this was tested against a simulated service.
- **A real Admissions answer.** It needs a Modal token. Leave it out of demos.
- **A real phone or tablet,** only browsers set to those sizes.
- **Printed paper,** and Urdu names read by a native reader.
- **`start_demo.bat` by double-click.** Its settings were tested, not the launcher itself.
- **Your own review of how it looks.** I checked screenshots, but your judgement is the real test.

## 6. Security findings

| Status | Findings |
|---|---|
| **Needs you now** | **The live site** still has S0a, S1, S3, S4, and S5 until pull request #1 is deployed |
| Fixed in code | Sign-in key and password handling, hashing, sign-in limits, exact-origin CORS, logout, PDF access, safe PDF text, file names, chatbot input limits, per-user chat, delete protection, security headers, and a browser security policy |
| Partly fixed | **S11:** tokens stay in browser storage, now short-lived and backed by a security policy. **S12:** contact details are on fewer screens. **S15:** contact details no longer go to Groq, but names, marks, and fees do when a key is set, so schools must be told |
| Open | **S9:** no staff roles, so every account has full access. No general request limits beyond sign-in. No record of who changed what |
| Accepted for now | 2 moderate `react-router` advisories, which need a major upgrade and do not match how this app navigates. Revisit before real use |

Database foreign keys are not enforced by SQLite here; the app's own rules prevent orphaned records.

Details: [SECURITY_REVIEW.md](SECURITY_REVIEW.md).

## 7. Known limitations

- **One school only.** Separate schools on one system are not built or tested, so do not claim them.
- **The early warning is unvalidated.** It was trained on made-up students. Do not present it as a prediction or quote its accuracy.
- **Not built:** late fees and concessions (policy text only, and challans say so), a new-academic-year screen, staff roles, attendance, and the P2 roadmap items.
- **Promotion** uses Final Term marks only, not the policy's 20/30/50 weighting.
- **PDFs:** Urdu sits in left-to-right order within mixed lines, and scripts other than Latin and Urdu do not print.
- **Forms:** most errors appear at the top of a form rather than beside each field.
- **Chatbot:** counts with a condition ("how many failed") are declined. Memory is lost on restart. The keyword fallback can match on a shared rare word. Policy answers without a language model are less polished.
- **Demo data:** Final Term marks sit in the current session so that trends show, and the calendar's dates are made up.
- **Large schools:** the Fees list loads every invoice at once. It is fast at 500 students, but needs server paging before years of records build up.
- **Hosting:** a single SQLite file on one server, suitable for a demo only.

## 8. Decisions and steps that need you

In order of urgency:

1. ~~Revoke the published Modal token.~~ Done on 5 November 2026.
2. **Set `SECRET_KEY`, `ADMIN_PASSWORD`, and `FRONTEND_URL`** in the Modal secret, then **approve deploying** the security fixes.
3. ~~Approve pushing branches M2 to M10.~~ Done on 5 November 2026.
4. **Answer two policy questions:** does a 40-49% subject count as a pass (now Grade F and Pass, as written), and should promotion use Final Term only?
5. **Review:** click through the app, print the samples on A4, and have an Urdu reader check the names.
6. **Add a Groq key** to `backend/.env` if you want AI wording in demos. Do not paste it in chat.
7. **Approve removing** the old files in section 7 of the release checklist, and the "waseemshaikh" record in `school.db`.

## 9. Demo login

No password is stored in the project. From `backend/`, build the demo:

```bash
python seed_demo.py --replace
```

Sign in at <http://localhost:5173> as `admin`, with the password printed **once** by that command, or one you set beforehand with `DEMO_ADMIN_PASSWORD`. Do not reuse a real password, or put it in slides. Full steps: [DEMO_GUIDE.md](DEMO_GUIDE.md) and [SAMPLE_DEMO_SCENARIO.md](SAMPLE_DEMO_SCENARIO.md).

## 10. Deployment

**Nothing has been deployed.** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) has the steps. In brief:

1. Set the Modal secret `educore-secrets`: `SECRET_KEY`, `ADMIN_PASSWORD`, `FRONTEND_URL`.
2. **Upgrade the Modal database, with a backup, before deploying the new code.** The app refuses to start on an old database, leaving it untouched.
3. Run `modal deploy modal_app.py`, which keeps one container for SQLite.
4. Import the repo into Vercel with root directory `frontend`, and set `VITE_API_URL`.
5. Check sign-in, PDFs, and the chatbot on the live addresses. The new security policy allows `*.modal.run`, so a different backend address means updating `frontend/vercel.json`.

Showing the demo school online needs a separate Modal app and Volume. Never put `demo.db` in place of a database holding other records.

## 11. Recommended next phase

**Finish the release first, in this order:**

1. Complete section 8, then deploy and test on the live addresses.
2. Rehearse on a real phone and laptop, then show one friendly school owner.
3. Let that feedback set priorities, rather than building ahead of it.

**Then, before a pilot with real records (P1):**

1. **Staff roles** (admin, accountant, teacher). This is the largest safety gap.
2. **Hosting and backups:** managed Postgres or a small server, with restores tested.
3. **Audit log** of who changed what.
4. **Late fees and sibling concessions,** which schools will ask about first.
5. **New-academic-year and class promotion screens.**
6. **Early warning:** validate on real outcomes, or switch it off.

Hold parent apps, payroll, transport, and multi-campus until a school has used this and asked for them.
