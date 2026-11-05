# EduCore AI

**Simple School Management, Smarter Decisions.**

A school management system for private schools in Pakistan, replacing Excel and paper for enrollment, fees, exam results, and reports, with AI help where it can be trusted.

> **Status:** an MVP for demonstrations, not yet ready for real school records. See [MVP_RELEASE_CHECKLIST.md](MVP_RELEASE_CHECKLIST.md). It serves one school. It does not separate several schools.

## What it does

| Area | Features |
|---|---|
| **Dashboard** | Students, fees, and academic estimates from live records, a billing-month filter, and recent activity |
| **Students** | Add, edit, archive, restore, search, and filter by grade and section. A profile page for each student |
| **Fees** | Monthly challans, part payments, balances, payment history, and overdue tracking. A4 challans and receipts, with Urdu names |
| **Results** | Marks for one student or a whole class, midterm and final, grades, promotion by policy, and A4 report cards |
| **Academic Early Warning** | An estimate from marks only, with the model's reasons. Fees are a separate flag. **Trained on synthetic data and not validated on real students, so a teacher should review before acting** |
| **School Assistant** | Answers from school records and policy documents, says which, and says when it cannot answer. Read-only. Works with no AI key |
| **Admissions** | Optional AI suggestion. A real answer is not yet tested |

## Try it

The fastest way to see it is the fictional demo school. Follow [DEMO_GUIDE.md](DEMO_GUIDE.md), then [SAMPLE_DEMO_SCENARIO.md](SAMPLE_DEMO_SCENARIO.md).

## Run it for development

You need Python 3.13 and Node.js. Backend, from `backend/`:

```bash
python -m pip install -r requirements-dev.txt
```

Copy `.env.example` to `.env`. It contains the settings for local work.

```bash
python seed_data.py
```

```bash
python -m uvicorn main:app --reload
```

With no admin password set, a one-time password is printed in that window. The API runs at <http://localhost:8000>, with its documentation at `/docs`.

Frontend, from `frontend/`:

```bash
npm install
```

```bash
npm run dev
```

Open <http://localhost:5173>. On Windows, `start_all.bat` starts both.

## Tests

From `backend/`:

```bash
python -m pytest
```

From `frontend/`:

```bash
npm test
```

```bash
npm run test:e2e
```

The last one runs the whole demo in Microsoft Edge, on its own ports and a throwaway database.

Tests use a temporary database and blank keys, so they cannot touch `school.db` or call an AI service.

## Technology

| Part | Stack | Deployed to |
|---|---|---|
| `backend/` | FastAPI, SQLModel, SQLite, ReportLab, scikit-learn, SHAP, FAISS, sentence-transformers, optional Groq | Modal |
| `frontend/` | React 18, Vite, Tailwind, React Router, Axios, Recharts | Vercel |

## Documents

| Document | For |
|---|---|
| [DEMO_GUIDE.md](DEMO_GUIDE.md), [SAMPLE_DEMO_SCENARIO.md](SAMPLE_DEMO_SCENARIO.md) | Running and presenting the demo |
| [MVP_FINAL_REPORT.md](MVP_FINAL_REPORT.md) | Where the project stands, test results, and next steps |
| [MVP_RELEASE_CHECKLIST.md](MVP_RELEASE_CHECKLIST.md) | What remains before going online, or using real records |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Modal and Vercel |
| [CLAUDE.md](CLAUDE.md) | How the code is organised |
| [SECURITY_REVIEW.md](SECURITY_REVIEW.md), [MVP_TESTING_CHECKLIST.md](MVP_TESTING_CHECKLIST.md) | Security findings and test results |
