# MVP Release Checklist

What must be true before showing EduCore AI online, and before any real school's records go in. Detailed test results are in [MVP_TESTING_CHECKLIST.md](MVP_TESTING_CHECKLIST.md).

✅ done &nbsp; ⬜ not done &nbsp; 👤 needs the owner

## 1. Stop the current exposure 👤

The live site still runs older code. These do not wait for the rest.

- [ ] 👤 Revoke the Modal proxy token published in the repo's history, and create a new one
- [ ] 👤 Set `SECRET_KEY`, `ADMIN_PASSWORD`, and `FRONTEND_URL` in the Modal secret `educore-secrets`
- [ ] 👤 Approve merging and deploying the safety fixes in pull request #1

## 2. Decisions still open 👤

- [ ] 👤 Does a subject at 40-49% count as a pass? It now reads Grade F and Pass, as the policy is written
- [ ] 👤 Should promotion use Final Term marks only? The policy's 20/30/50 weighting is not built
- [ ] 👤 Review or replace the sample policies in `backend/knowledge_base/`. They are written for a demo, and the calendar was updated to 2026-2027 with made-up event dates
- [ ] 👤 Approve removing the old files listed in section 7
- [ ] 👤 Approve the record called "waseemshaikh" being removed from the local `school.db`

## 3. Code

- ✅ M0 to M10 complete in code, on branches built one on another. Results are in [MVP_FINAL_REPORT.md](MVP_FINAL_REPORT.md)
- [ ] 👤 Approve pushing branches M2 to M10
- [ ] Merge in order and confirm tests still pass after each
- ✅ M10: full QA pass on the local production build

## 4. Tests

- ✅ Backend and frontend tests pass on a clean install, with results recorded per milestone
- [ ] Tests pass on the merged code
- [ ] 👤 Valid Groq key added locally, and all chatbot paths run against it
- [ ] 👤 New Modal token added locally, and a real Admissions answer reviewed
- ✅ Run in a browser at phone and tablet widths
- [ ] 👤 Run on a real phone
- [ ] 👤 You look over every page
- [ ] 👤 Challan, report card, and receipt printed on A4, and Urdu names checked by a native reader
- ✅ Browser security policy tested with PDFs, on a local production build
- ✅ Session expiry tested in a browser
- [ ] Security policy confirmed on Vercel

## 5. Online demo

- [ ] Database upgraded before the code that needs it, with a backup: see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md), Step 5
- [ ] Backend deployed to Modal with `max_containers=1`
- [ ] 👤 Price of one warm container checked, then a decision made
- [ ] Frontend deployed to Vercel, and `VITE_API_URL` set
- [ ] Sign-in, PDFs, and chatbot checked on the live addresses
- [ ] Rehearsed from start to finish using [SAMPLE_DEMO_SCENARIO.md](SAMPLE_DEMO_SCENARIO.md)
- [ ] Screenshots or a recording ready, in case of failure

## 6. Before any real school's records

The demo is not ready for this. All of these are needed first:

- [ ] 👤 Hosting chosen: managed Postgres, or a small server with SQLite and tested backups (decision D5)
- [ ] Backups automatic, and one restore actually tested
- [ ] Separate staff roles (admin, accountant, teacher). Everyone has full access today
- [ ] A record of who changed what
- [ ] General request limits, beyond sign-in
- [ ] 👤 Privacy terms agreed with the school, covering what goes to Groq if it is used
- [ ] 👤 Early warning either validated on real outcomes, or turned off
- [ ] Late fees and concessions, if the school needs them
- [ ] A way to start a new academic year. The current year is only set in the database today
- [ ] 👤 Support plan: who answers when something breaks

Do not put several schools on one system. Isolation between schools is not built or tested.

## 7. Old files to remove, with your approval

All are tracked in git, so they could be recovered. None is used by the app.

| File | Why it can go |
|---|---|
| `New Microsoft Word Document.docx` | Empty |
| `EduCore_AI_Implementation_Plan--.py` | Empty |
| `EduCore_AI_Hackathon_Presentation.pdf`, `generate_presentation_pdf.py` | Hackathon slides and their generator |
| `EduCore_AI_Pitch_Deck.html`, `EduCore_AI_Video_Generation_Prompt.md` | Hackathon material, with outdated claims |
| `EduCore_AI_Implementation_Plan.pdf`, `implementation-plan .txt` | The original 2-day plan, now history |
| `test_crew.py` | A manual script, outside the test suite |
| `run_backend_fix.bat`, `run_frontend_fix.bat` | Old launchers |
| `backend/log.txt`, `backend/modal_deploy.log` | Old logs. Check them for private details too |

`AGENTS.md` and `GEMINI.md` are for AI coding tools, and are left alone unless you prefer otherwise.
