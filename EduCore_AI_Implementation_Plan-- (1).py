content = """================================================================================
        EDUCORE AI - IMPLEMENTATION PLAN (HACKATHON EDITION - 2 DAYS)
         AI-Powered Education Management Platform | Al-Noor Academy
================================================================================

  School Name   : Al-Noor Academy
  Build Time    : 2 Days (Hackathon)
  Backend       : FastAPI + SQLite + Python
  Frontend      : React + Vite + Tailwind CSS + shadcn/ui
  AI Stack      : scikit-learn + SHAP + FAISS + Groq API (Free)
  PDF Reports   : Fee Challan + Report Card (ReportLab)
  Auth          : JWT  |  Login: admin / admin123
  Currency      : PKR (Pakistani Rupee - Rs.)
  Generated     : September 12, 2026

================================================================================
 SECTION 1: PROJECT GOAL
================================================================================

Build a demo-ready, AI-powered School Management System in 48 hours that
replaces manual Excel-based school administration with a centralized digital
platform.

Judges will see:
  - Real data flows (students, fees, results)
  - Professional PDF outputs (fee challans + report cards)
  - Machine learning at-risk student predictions with plain-English explanations
  - AI-powered RAG policy chatbot that answers school policy questions
  - All running live on localhost

================================================================================
 SECTION 2: PROJECT SCOPE
================================================================================

  IN SCOPE (Building in 2 Days)           OUT OF SCOPE (Removed)
  -------------------------------------   ----------------------------
  [x] Student registration & management  [ ] Attendance tracking
  [x] Fee management + PDF challan        [ ] WhatsApp/SMS alerts
  [x] Result entry + report card PDF      [ ] Parent portal
  [x] Admin dashboard with live charts    [ ] Timetable scheduling
  [x] At-Risk AI prediction + SHAP        [ ] Multi-tenancy (Phase 4)
  [x] RAG Policy Chatbot (Groq + FAISS)
  [x] JWT secure admin login

================================================================================
 SECTION 3: TECH STACK
================================================================================

 BACKEND TOOLS
 ──────────────────────────────────────────────────────────────────────────
 Tool                   Role                        Beginner Note
 ──────────────────────────────────────────────────────────────────────────
 Python + FastAPI        Server + all API endpoints  Auto-generates /docs page
 SQLite                  Database (single .db file)  Zero setup, no server
 SQLModel                ORM - Python to DB tables   Write Python = DB tables
 ReportLab               Generate PDF files          Challans + report cards
 scikit-learn            Machine learning library    At-risk prediction model
 SHAP                    Explain AI decisions        Plain English reasons
 sentence-transformers   Text embeddings (free)      Policy text to numbers
 FAISS                   Vector similarity search    Finds relevant chunks
 Groq API (Free)         LLM - LLaMA 3 model         Chatbot answers (free)
 JWT                     Secure auth tokens          Industry-standard login
 ──────────────────────────────────────────────────────────────────────────

 FRONTEND TOOLS
 ──────────────────────────────────────────────────────────────────────────
 Tool            Role                    Beginner Note
 ──────────────────────────────────────────────────────────────────────────
 React + Vite    Web UI framework        Component-based, fast dev setup
 Tailwind CSS    Styling                 Class names = styles, no CSS file
 shadcn/ui       UI components           Ready-made buttons, tables, forms
 React Router    Page navigation         Links between pages
 Axios           HTTP requests           Talks to the FastAPI backend
 Recharts        Charts and graphs       Bar charts on dashboard
 ──────────────────────────────────────────────────────────────────────────

================================================================================
 SECTION 4: PROJECT FOLDER STRUCTURE
================================================================================

  G:\\Edutech\\
  |
  +-- backend\\
  |   +-- main.py                   <- Start server: uvicorn main:app --reload
  |   +-- config.py                 <- School name, API keys, settings
  |   +-- database.py               <- SQLite connection
  |   +-- seed_data.py              <- Load 50 demo students for judges
  |   +-- requirements.txt          <- All Python packages
  |   |
  |   +-- models\\
  |   |   +-- __init__.py
  |   |   +-- user.py               <- Admin login accounts
  |   |   +-- student.py            <- Student records
  |   |   +-- fee.py                <- Invoices and payments
  |   |   +-- result.py             <- Exam marks
  |   |
  |   +-- routers\\
  |   |   +-- __init__.py
  |   |   +-- auth.py               <- POST /auth/login
  |   |   +-- students.py           <- CRUD /students
  |   |   +-- fees.py               <- /fees - challan, pay, PDF
  |   |   +-- results.py            <- /results - marks + report card
  |   |   +-- dashboard.py          <- /dashboard/stats
  |   |   +-- ai.py                 <- /ai/at-risk predictions
  |   |   +-- chatbot.py            <- /chatbot/ask  [RAG - NEW]
  |   |
  |   +-- services\\
  |   |   +-- pdf_service.py        <- Generate challan + report card PDFs
  |   |   +-- ai_service.py         <- At-risk ML model (Random Forest)
  |   |   +-- rag_service.py        <- RAG chatbot logic  [NEW]
  |   |
  |   +-- knowledge_base\\           <- School policy documents  [NEW]
  |       +-- fee_policy.txt
  |       +-- exam_policy.txt
  |       +-- admission_policy.txt
  |       +-- conduct_rules.txt
  |       +-- academic_calendar.txt
  |
  +-- frontend\\
      +-- index.html
      +-- package.json
      +-- vite.config.js
      +-- tailwind.config.js
      +-- postcss.config.js
      |
      +-- src\\
          +-- main.jsx              <- Entry point
          +-- App.jsx               <- All routes defined here
          |
          +-- api\\
          |   +-- client.js         <- All API calls (Axios)
          |
          +-- pages\\
          |   +-- Login.jsx
          |   +-- Dashboard.jsx
          |   +-- Students.jsx
          |   +-- Fees.jsx
          |   +-- Results.jsx
          |   +-- AtRisk.jsx        <- AI at-risk predictions page
          |   +-- Chatbot.jsx       <- RAG chatbot page  [NEW]
          |
          +-- components\\
              +-- Layout.jsx        <- Sidebar + header wrapper
              +-- StatCard.jsx      <- Dashboard stat boxes
              +-- DataTable.jsx     <- Reusable sortable table

================================================================================
 SECTION 5: DATABASE TABLES
================================================================================

  users          : id, username, password_hash, role
  students       : id, name, roll_number, grade, section, guardian_name,
                   phone, dob, created_at
  academic_years : id, label (e.g. 2025-2026), is_current
  fee_structures : id, grade, label, amount, academic_year_id
  invoices       : id, student_id, amount, due_date, challan_number,
                   status (paid/pending), created_at
  payments       : id, invoice_id, amount_paid, paid_at,
                   payment_mode (cash/bank/online)
  results        : id, student_id, subject, marks_obtained,
                   total_marks, exam_type, academic_year_id

  NOTE: RAG chatbot uses flat .txt files + in-memory FAISS index.
        No extra database table is needed for the chatbot.

================================================================================
 SECTION 6: API ENDPOINTS
================================================================================

 AUTH
   POST   /auth/login                  Returns JWT token

 STUDENTS
   GET    /students                    List all students (with search/filter)
   POST   /students                    Add new student
   GET    /students/{id}               Get one student
   PUT    /students/{id}               Update student
   DELETE /students/{id}               Delete student

 FEES
   GET    /fees                        List all invoices (paid/pending filter)
   POST   /fees/generate               Create challan for a student
   POST   /fees/{id}/pay               Mark invoice as paid
   GET    /fees/{id}/pdf               Download challan as PDF

 RESULTS
   GET    /results/{student_id}                   All marks for student
   POST   /results                                Enter new marks
   GET    /results/{student_id}/report-card/pdf   Download report card PDF

 DASHBOARD
   GET    /dashboard/stats             Total students, fees collected, pending

 AI - AT-RISK
   GET    /ai/at-risk                  All students with risk scores
   GET    /ai/at-risk/{student_id}     One student detail + SHAP reasons

 CHATBOT - RAG [NEW]
   POST   /chatbot/ask                 Ask a school policy question
   GET    /chatbot/topics              List topics the bot knows

================================================================================
 SECTION 7: AI FEATURES
================================================================================

 7.1  AT-RISK STUDENT PREDICTION
 ──────────────────────────────────────────────────────────────────────────

  HOW IT WORKS (Step by Step):
    Step 1: Server starts -> reads all student data from database
    Step 2: Calculates 4 features per student:
              avg_marks_pct     = average of all subject marks %
              fee_defaults      = number of unpaid invoices
              failing_subjects  = count of subjects below 50%
              grade_trend       = are marks going up or down?
    Step 3: Trains Random Forest Classifier (scikit-learn)
              Students who failed = labeled 1 (at risk)
              Students who passed = labeled 0 (not at risk)
              Training takes about 2 seconds total
    Step 4: Predicts risk score 0-100% for each student
    Step 5: SHAP explains the top 3 reasons in plain English

  RISK LABELS:
    RED    [HIGH RISK]    Score > 70%   Auto-flagged, shown to principal
    YELLOW [MEDIUM RISK]  Score 40-70%  Monitor closely
    GREEN  [LOW RISK]     Score < 40%   Student is doing well

  EXAMPLE OUTPUT:
    Ahmed Khan  --- Risk Score: 84%  [HIGH RISK]
      Reason 1: "Average marks dropped from 72% to 51%"
      Reason 2: "Failing 3 subjects this semester"
      Reason 3: "2 unpaid fee invoices"

    Sara Malik  --- Risk Score: 55%  [MEDIUM RISK]
    Bilal Ahmed --- Risk Score: 18%  [LOW RISK]

 ──────────────────────────────────────────────────────────────────────────

 7.2  RAG POLICY CHATBOT  [NEW]
 ──────────────────────────────────────────────────────────────────────────

  WHAT IS RAG? (Plain English)
    RAG = Retrieval-Augmented Generation
    The chatbot SEARCHES your school policy documents first,
    then answers using ONLY what it found.
    It says "I don't know" if the answer is not in the documents.
    This prevents AI from making up (hallucinating) wrong answers.

  SETUP (runs once when server starts):
    1. Load 5 policy text files from knowledge_base/ folder
    2. Split each file into small chunks (~200 words each)
    3. Convert chunks to number vectors using sentence-transformers
       - Runs locally and is completely FREE (no API key needed)
    4. Store all vectors in FAISS (fast in-memory search index)

  WHEN USER ASKS A QUESTION:
    1. Convert user question to a number vector
    2. FAISS finds the 3 most relevant policy chunks
    3. Send: user question + 3 chunks to Groq API (free LLaMA 3)
    4. Groq generates a clear, grounded answer
    5. Return: answer + source document name to frontend

  EXAMPLE:
    User    : "What is the fee refund policy?"
    FAISS   : Finds fee_policy.txt chunk about refunds
    Answer  : "According to the fee policy, refunds are only
               issued within 15 days of payment if the student
               withdraws before the term begins."
    Source  : fee_policy.txt

  KNOWLEDGE BASE FILES:
    fee_policy.txt        - Fee due dates, late fees, refund rules
    exam_policy.txt       - Exam schedule, grading, retake rules
    admission_policy.txt  - Admission requirements, documents needed
    conduct_rules.txt     - Uniform, discipline, leave rules
    academic_calendar.txt - Term dates, holidays, exam dates

================================================================================
 SECTION 8: 2-DAY BUILD SCHEDULE
================================================================================

 DAY 1 - BACKEND (10 HOURS)
 ──────────────────────────────────────────────────────────────────────────
 Hour   Task                               Files Created
 ──────────────────────────────────────────────────────────────────────────
 1-2    Setup + DB models + JWT auth        config.py, database.py,
                                            models/*.py, routers/auth.py
 3-4    Students API (full CRUD)            routers/students.py
 5-6    Fee API + challan PDF               routers/fees.py,
                                            services/pdf_service.py
 7      Results API + report card PDF       routers/results.py
 8      Dashboard + seed 50 students        routers/dashboard.py,
                                            seed_data.py
 9      At-Risk AI model + endpoint         services/ai_service.py,
                                            routers/ai.py
 10     RAG Chatbot                         services/rag_service.py,
                                            routers/chatbot.py,
                                            knowledge_base/*.txt
 ──────────────────────────────────────────────────────────────────────────

 DAY 2 - FRONTEND (10 HOURS)
 ──────────────────────────────────────────────────────────────────────────
 Hour   Task                               Files Created
 ──────────────────────────────────────────────────────────────────────────
 1-2    React setup + Layout + Login        package.json, App.jsx,
                                            Layout.jsx, Login.jsx
 3-4    Dashboard + Students pages          Dashboard.jsx, Students.jsx
 5      Fees management page                Fees.jsx
 6      Results entry page                  Results.jsx
 7      At-Risk AI page (color badges)      AtRisk.jsx
 8      RAG Chatbot page (chat UI)          Chatbot.jsx
 9      API client - wire everything        api/client.js
 10     Polish UI + full demo test          Final rehearsal
 ──────────────────────────────────────────────────────────────────────────

================================================================================
 SECTION 9: PDF OUTPUT DESIGNS
================================================================================

 FEE CHALLAN PDF
 ──────────────────────────────────────────────────────────────────────────
   AL-NOOR ACADEMY -- Fee Challan
   ----------------------------------------------------------
   Student : Ahmed Khan              Roll No : 045
   Class   : Grade 8-B               Month   : October 2025
   ----------------------------------------------------------
   Tuition Fee  . . . . . . . . . .   Rs. 3,500
   Exam Fee . . . . . . . . . . . .   Rs.   500
   ----------------------------------------------------------
   TOTAL  . . . . . . . . . . . . .   Rs. 4,000
   Due Date: 10-Oct-2025       Challan No: CHN-1045
   ----------------------------------------------------------
     [ Bank Copy ]                  [ Student Copy ]
 ──────────────────────────────────────────────────────────────────────────

 REPORT CARD PDF
 ──────────────────────────────────────────────────────────────────────────
   AL-NOOR ACADEMY -- Student Report Card (2025-2026)
   ----------------------------------------------------------
   Student: Ahmed Khan      Roll: 045      Class: Grade 8-B
   ----------------------------------------------------------
   Subject               Marks Obtained    Total    Grade
   English                     78           100       B
   Mathematics                 91           100       A
   Science                     85           100       A
   Urdu                        72           100       B
   Islamiat                    88           100       A
   Pakistan Studies            80           100       A
   ----------------------------------------------------------
   Total: 494 / 600        Percentage: 82.3%       Grade: A
 ──────────────────────────────────────────────────────────────────────────

================================================================================
 SECTION 10: 5-MINUTE DEMO SCRIPT FOR JUDGES
================================================================================

  Step  Action                                    Time     Impact
  ──────────────────────────────────────────────────────────────────────────
  1     Login as admin (admin / admin123)          30 sec   Shows security
  2     Dashboard - live stats + bar charts        45 sec   Shows data value
  3     Add a new student via the form             30 sec   Core feature
  4     Generate fee challan -> download PDF       1 min    Tangible output
  5     Enter exam marks -> download report card   30 sec   Tangible output
  6     At-Risk page -> red student + 3 reasons    1 min    *** AI WOW #1 ***
  7     Chatbot: "What is the fee refund policy?"  30 sec   *** AI WOW #2 ***
  ──────────────────────────────────────────────────────────────────────────
  TOTAL: 5 minutes

  TIP: Steps 6 and 7 are your WINNING moments. Show them last
       so judges leave with the AI impression fresh in their minds.

================================================================================
 SECTION 11: SETUP INSTRUCTIONS (3 STEPS)
================================================================================

 STEP 1 - GET FREE GROQ API KEY (1 minute)
   1. Go to  : https://console.groq.com
   2. Sign up free
   3. Go to  : API Keys section
   4. Click  : Create API Key
   5. Copy   : the key (starts with gsk_...)

 STEP 2 - BACKEND SETUP
   Open PowerShell and run these one by one:

     cd G:\\Edutech\\backend
     pip install -r requirements.txt
     echo GROQ_API_KEY=your_key_here > .env
     python seed_data.py
     uvicorn main:app --reload

   Server runs at  : http://localhost:8000
   API test page   : http://localhost:8000/docs

 STEP 3 - FRONTEND SETUP
   Open a NEW PowerShell window and run:

     cd G:\\Edutech\\frontend
     npm install
     npm run dev

   App runs at: http://localhost:5173

================================================================================
 SECTION 12: DEFAULT DEMO CONFIGURATION
================================================================================

  Setting           Value
  ──────────────────────────────────────────────────────────────────────────
  School Name       Al-Noor Academy
  Grades            Grade 6, Grade 7, Grade 8, Grade 9, Grade 10
  Subjects          English, Urdu, Mathematics, Science,
                    Islamiat, Pakistan Studies
  Tuition Fee       Rs. 3,500 per month
  Exam Fee          Rs. 500 per semester
  Currency          PKR (Rs.)
  Admin Username    admin
  Admin Password    admin123
  Demo Students     50 students seeded across all grades and sections
  Chatbot Topics    Fee policy, Exam rules, Admission, Conduct, Calendar
  ──────────────────────────────────────────────────────────────────────────

================================================================================
 SECTION 13: GRADING SCALE
================================================================================

  Percentage       Grade    Remarks
  ──────────────────────────────────────────────────────────────────────────
  90% and above      A+     Outstanding
  80% - 89%          A      Excellent
  70% - 79%          B      Very Good
  60% - 69%          C      Good
  50% - 59%          D      Satisfactory
  Below 50%          F      Fail (student flagged as at-risk)
  ──────────────────────────────────────────────────────────────────────────

================================================================================
 ALL OUTPUT FILES
================================================================================

  G:\\Edutech\\
  +-- EduCore_AI_Implementation_Plan.txt   <- This file (plain text)
  +-- EduCore_AI_Implementation_Plan.pdf   <- PDF version
  +-- EduCore_AI_Implementation_Plan.docx  <- Word version

================================================================================
 END OF IMPLEMENTATION PLAN
================================================================================

  EduCore AI  |  Hackathon Edition  |  2-Day Build
  Al-Noor Academy  |  September 12, 2026
  Beginner-Friendly | FastAPI + React + AI

================================================================================
"""

with open(r"G:\Edutech\EduCore_AI_Implementation_Plan.txt", "w", encoding="utf-8") as f:
    f.write(content)

import os
size = os.path.getsize(r"G:\Edutech\EduCore_AI_Implementation_Plan.txt")
print(f"Text file created successfully!")
print(f"Location: G:\\Edutech\\EduCore_AI_Implementation_Plan.txt")
print(f"Size: {size} bytes ({size//1024} KB)")
