# Demo Guide

How to run EduCore AI for a presentation, using a fictional school. The step-by-step talk is in [SAMPLE_DEMO_SCENARIO.md](SAMPLE_DEMO_SCENARIO.md).

## What the demo uses

**Roshan Demo Academy** is a made-up school in Khairpur. Its database, `backend/demo.db`, is separate from `school.db`, which the demo never opens.

| Holds | Details |
|---|---|
| Students | 120 made-up students, 12 in each of 10 classes (Grades 6 to 10, sections A and B). One is archived |
| Exams | Midterm and Final Term for the current session, except one new student with no marks |
| Fees | The last 3 billing months, including paid, part-paid, and unpaid challans |
| Estimates | When built on 5 November 2026: 92 Low, 12 Medium, 14 High, 1 Not enough data |

Phone numbers start with `0999`, which no Pakistani mobile or Khairpur line uses, so nobody can be called by mistake.

## First-time setup

Install once, from the project folder:

```bash
cd backend
```

```bash
python -m pip install -r requirements-dev.txt
```

```bash
cd ../frontend
```

```bash
npm install
```

## Build the demo school

From `backend/`:

```bash
python seed_demo.py
```

This prints the `admin` password **once**, so write it down. To choose your own, set `DEMO_ADMIN_PASSWORD` before running it, with at least 10 characters. Do not reuse a real password, and do not put it in slides or documents.

Dates follow the day you build it, so **rebuild shortly before each demo**. This also undoes anything done in the last demo:

```bash
python seed_demo.py --replace
```

The script refuses any file whose name does not contain `demo`, and will not overwrite one without `--replace`.

## Start it

On Windows, from the project folder:

```bash
start_demo.bat
```

Open <http://localhost:5173> and sign in as `admin`. You should see the school's name and a **DEMO MODE** label on the sign-in page. If you see a different school, or no label, stop: you are not on the demo database.

If you are not on Windows, set the values in `start_demo.bat` yourself and start the backend from `backend/`.

## Check 10 minutes before

- [ ] Rebuilt today with `--replace`
- [ ] DEMO MODE shows on the sign-in page and in the app
- [ ] The dashboard loads, and shows 119 current students
- [ ] Ask the School Assistant one policy question, so its search has loaded. The first one after a start takes the longest
- [ ] Open one PDF. If the browser blocks the pop-up, allow it for this site
- [ ] Printer ready, if you plan to print a challan or receipt
- [ ] Browser zoom set so the back of the room can read it

## What to say about the AI

Please keep these accurate, because they will be repeated to schools:

- **The early warning is an estimate.** It was trained on made-up students and has not been validated on real ones. A teacher decides what to do. Do not call it a prediction or quote its scores as evidence.
- **Fees never affect it.** Overdue fees are a separate flag for the accounts office.
- **The School Assistant reads records and never changes them.** Each answer says where it came from, and it says so when it cannot answer.
- **Without a Groq key**, as in the steps here, answers come from built-in logic. The chatbot page shows which is in use. With a key, student names, roll numbers, marks, and fees go to Groq, a company outside Pakistan, and schools must be told. Guardian names, phones, and birth dates do not go.
- **One school only.** Do not say that several schools can share one system securely. That is not built.

## Not ready to show

| Feature | Why |
|---|---|
| Admissions | Needs extra packages and a Modal token, and a real answer has never been tested. Leave it out |
| Groq answers | Never tested with a real key. Test before you show them |
| Late fees and sibling discounts | In the policy text only. The system does not calculate them |
| Parent app, payroll, attendance, and other later ideas | Not built. Describe them only as a possible roadmap |
| Phones | Checked at phone size in a browser, not on a real phone. Try yours first |

## If something goes wrong

| Problem | What to do |
|---|---|
| "Could not reach the server" | The backend window has closed or stopped. Start `start_demo.bat` again |
| Sign-in refused | Rebuild with `--replace` and a known `DEMO_ADMIN_PASSWORD`. Too many wrong tries lock sign-in for up to 15 minutes, and restarting the backend clears this |
| The School Assistant is slow | Only the first policy question after a start. Wait, then carry on |
| Your demo data looks wrong | Rebuild with `--replace`, then start again |
| PDF does not open | Allow pop-ups for this site, then try again |
| Everything fails | Show your screenshots or recording. Make one when rehearsing |

## Afterwards

The demo database is ignored by git, and is safe to delete. The live site is separate: see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).
