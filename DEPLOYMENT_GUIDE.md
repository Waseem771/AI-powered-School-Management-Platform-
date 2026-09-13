# 🚀 EduCore AI Deployment Guide (Beginner Friendly)

This guide shows you how to deploy the entire platform live:
- **Backend**: [Modal](https://modal.com) (Serverless FastAPI Python backend)
- **Frontend**: [Vercel](https://vercel.com) (React + Vite single-page application)

---

## Part 1: Deploy Backend to Modal (FastAPI)

Modal allows you to deploy serverless Python backends with zero server configuration.

### Step 1: Install Modal CLI
Open your terminal in the project directory and run:
```bash
pip install modal
```

### Step 2: Create a Modal Account & Authenticate
1. Sign up for a free account at [https://modal.com](https://modal.com).
2. Authenticate your computer by running:
```bash
modal setup
```
*(This will open a browser window to link your Modal account to your terminal).*

### Step 3: Create Secrets on Modal
Your backend needs your Groq API key and Secret key. Run:
```bash
modal secret create educore-secrets GROQ_API_KEY="<YOUR_GROQ_API_KEY>" SECRET_KEY="educore_super_secret_jwt_key_2026_al_noor" GROQ_MODEL="openai/gpt-oss-120b"
```
*(You can also manage or update these secrets anytime in your [Modal Dashboard](https://modal.com/secrets)).*

### Step 4: Seed Initial Data on Modal
To seed the 50 students, grades, fee structures, and sample invoices into your persistent Modal volume:
```bash
cd backend
modal run modal_app.py::seed_database_volume
```

### Step 5: Deploy the Backend
Deploy your FastAPI application to production:
```bash
modal deploy modal_app.py
```

### Step 6: Save Your Backend URL
After deployment finishes, Modal will print a public URL, for example:
```
https://<your-username>--educore-ai-school-platform-fastapi-app.modal.run
```
Copy this URL! You will use it in Part 2 for the frontend.

---

## Part 2: Deploy Frontend to Vercel (React + Vite)

### Step 1: Sign up / Log in to Vercel
1. Go to [https://vercel.com](https://vercel.com).
2. Log in using your **GitHub account**.

### Step 2: Import Your Repository
1. Click **"Add New..."** → **"Project"**.
2. Find and select your GitHub repository:
   `https://github.com/Waseem771/AI-powered-School-Management-Platform-`
3. Click **"Import"**.

### Step 3: Configure Project Settings on Vercel
In the Vercel project configuration screen:

1. **Root Directory**:
   - Click **Edit** next to Root Directory.
   - Select `frontend` and click **Continue**.
2. **Framework Preset**:
   - Vercel will automatically detect `Vite`. If not, select **Vite**.
3. **Build & Output Settings**:
   - Build Command: `npm run build` *(default)*
   - Output Directory: `dist` *(default)*
4. **Environment Variables**:
   - Add the following variable:
     - **Key**: `VITE_API_URL`
     - **Value**: Your Modal Backend URL from Part 1 (e.g. `https://<your-username>--educore-ai-school-platform-fastapi-app.modal.run`)
     *(Make sure there is NO trailing slash at the end).*
   - Click **Add**.

### Step 4: Deploy
Click the **"Deploy"** button!
Vercel will build your React app and deploy it globally in under a minute.

---

## Part 3: Verify & Log In

1. Open your live Vercel URL (e.g., `https://ai-powered-school-management-platform.vercel.app`).
2. Log in using the default administrative credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Test features:
   - **Dashboard**: View school statistics & fees recovery.
   - **Students**: Search, edit, and add student records.
   - **AI Risk Engine**: Test the interactive At-Risk student simulator.
   - **AI Chatbot**: Test conversational queries with memory (e.g., *"Show me Ahmed Khan"* followed by *"What are his pending fees?"*).
