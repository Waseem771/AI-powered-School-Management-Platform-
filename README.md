# EduCore AI — AI-Powered Education Management Platform
### Al-Noor Academy &bull; Hackathon Edition

A full-stack, demo-ready School Management System designed to replace manual Excel-based school administration with a centralized digital platform featuring live analytics, official PDF generation, explainable ML-based at-risk student predictions, and a grounded RAG policy chatbot.

---

## 🌟 Key Features

1. **JWT Secure Admin Authentication**:
   - Industry-standard bearer token login with pre-configured demo account: `admin` / `admin123`.
2. **Student Enrollment & Management**:
   - Full CRUD support with search, filtering by grade, sections, and parent contact details.
   - Seeded with **50 realistic student profiles** across Grades 6 through 10.
3. **Fee Management & ReportLab Challan PDF**:
   - Invoice generation, fee recovery tracking, cash/bank/online payment recording.
   - **One-click official 2-part Fee Challan PDF** ([Bank Copy] and [Student Copy]) with barcodes, line items, and signature lines.
4. **Exam Results & ReportLab Report Card PDF**:
   - Subject-wise marks entry across English, Urdu, Mathematics, Science, Islamiat, and Pakistan Studies.
   - Auto-computed total marks, percentages, letter grades (A+, A, B, C, D, F), and **Official Report Card PDF download**.
5. **AI At-Risk Student Early Warning (scikit-learn + SHAP)**:
   - Random Forest Classifier evaluates `avg_marks_pct`, `fee_defaults`, `failing_subjects`, and `grade_trend`.
   - Generates 0–100% Risk Probability and classifies into **High Risk (>70%)**, **Medium Risk (40–70%)**, and **Low Risk (<40%)**.
   - **SHAP Explainability**: Plain-English root causes per student (e.g., *"Avg marks dropped significantly from 65% to 44%"*, *"Failing 3 core subjects"*, *"2 unpaid fee invoices"*).
   - Actionable remediation roadmap and teacher intervention guidelines.
6. **RAG Policy Chatbot (FAISS + sentence-transformers + Groq LLaMA 3)**:
   - Ingests 5 official school policy documents (`fee_policy.txt`, `exam_policy.txt`, `admission_policy.txt`, `conduct_rules.txt`, `academic_calendar.txt`).
   - Dense vector similarity search with FAISS and grounded answer generation.
   - Includes automatic local grounded fallback so it **never crashes** if an external API key is absent.

---

## 🚀 Quick Start Instructions

### 1. Backend Setup
```bash
cd backend
python -m pip install -r requirements.txt
python seed_data.py
python -m uvicorn main:app --reload
```
- **Backend Server**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- **Frontend App**: [http://localhost:5173](http://localhost:5173)

### 3. One-Click Launch (Windows)
Double-click `start_all.bat` or run:
```bat
start_all.bat
```

---

## 🎯 5-Minute Demo Script for Judges

| # | Action | Screen | Impact |
|---|--------|--------|--------|
| 1 | **Login** | `/login` | Click *"Prefill Demo Login"* (`admin` / `admin123`) and sign in. Demonstrates JWT security. |
| 2 | **Dashboard** | `/dashboard` | View enrollment (50 students), fees collected vs pending, grade bar charts, and AI radar. |
| 3 | **Register Student** | `/students` | Filter by Grade 8, click *"Register New Student"*, fill details, and show live update. |
| 4 | **Download Challan PDF** | `/fees` | Click *"Challan PDF"* on Ahmed Khan (#045, CHN-1045) to open the official ReportLab two-part bank & parent slip. |
| 5 | **Download Report Card PDF** | `/results` | Select Ahmed Khan (#045), view subject marks table, and click *"Download Report Card PDF"*. |
| 6 | **AI At-Risk & SHAP Explanations** | `/at-risk` | Filter by *"High Risk (>70%)"*, click on Bilal Tariq (#012, 100% risk), and highlight the 3 SHAP plain-English reasons and intervention roadmap. |
| 7 | **RAG Policy Chatbot** | `/chatbot` | Ask: *"What is the fee refund policy?"* or click one of the quick inquiry pills to see grounded answers with document citations. |

---

## ⚙️ Configuration

Set in `backend/.env`:
```ini
SCHOOL_NAME=Al-Noor Academy
GROQ_API_KEY=your_groq_api_key_here  # Optional: falls back to local grounded extractor if left blank
GROQ_MODEL=llama-3.3-70b-versatile
```
