# EduCore AI Deployment Guide

This guide deploys the platform:

- **Backend:** [Modal](https://modal.com) (serverless FastAPI)
- **Frontend:** [Vercel](https://vercel.com) (React + Vite)

The backend refuses to start without safe settings. That is deliberate, and the error message in the Modal logs says which setting is missing.

---

## Part 1: Backend on Modal

### Step 1: Install the Modal CLI and sign in

```bash
pip install modal
```

```bash
modal setup
```

### Step 2: Generate a signing key

Run this and keep the output private:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Step 3: Create or update the Modal secret

In the Modal dashboard, open **Secrets** and create or edit `educore-secrets` with these values. Using the dashboard keeps them out of your shell history.

| Name | Required | Value |
|---|---|---|
| `SECRET_KEY` | Yes | The output of Step 2 |
| `ADMIN_PASSWORD` | Yes, on first deploy or if the account still uses an old default | A private password of at least 10 characters |
| `FRONTEND_URL` | Yes | Your exact Vercel address, such as `https://your-app.vercel.app`, with no trailing slash. Separate several with commas |
| `GROQ_API_KEY` | No | Without it, the chatbot uses its local answers |
| `GROQ_MODEL` | No | For example `openai/gpt-oss-120b` |
| `MODAL_PROXY_TOKEN_ID`, `MODAL_PROXY_TOKEN_SECRET` | No | Needed only for AI Admissions. Without them, only that feature is unavailable |

Do not set `APP_ENV` on Modal. Without it, the app uses its production safeguards.

**What these settings do**

- `ADMIN_PASSWORD` is used when the admin account is created, or to replace a known default password. It does not overwrite a password you later change in the app.
- **Forgot the password?** Set `ADMIN_PASSWORD` to a new value, add `ADMIN_PASSWORD_RESET=true`, and deploy. Once you can sign in, remove `ADMIN_PASSWORD_RESET` and deploy again.
- Changing `SECRET_KEY` signs everyone out.

### Step 4: Seed demo data (new database only)

Skip this if the volume already holds data. Seeding is safe to re-run, because it stops if 50 or more students already exist.

```bash
cd backend
```

```bash
modal run modal_app.py::seed_database_volume
```

### Step 5: Upgrade an existing database, before deploying

Skip this for a brand-new database. **For any other database, do this first:** the new code refuses to start until it is done, and leaves the database untouched. The upgrade adds a field for archiving students, and stops duplicate challans and duplicate marks at database level. No existing records change, and the old code keeps working on an upgraded database.

First, see the report. It changes nothing, and lists any records that need a person to review:

```bash
modal run modal_app.py::upgrade_database
```

Then stop the app so nothing is writing, and apply. This backs up the database on the volume first:

```bash
modal app stop educore-ai-school-platform
```

```bash
modal run modal_app.py::upgrade_database --apply
```

If the report lists duplicate challans or marks, the upgrade stops and changes nothing. Decide which record is right before trying again.

To undo: restore the backup file, named `school.db.backup-<date>`, on the volume.

### Step 6: Deploy

```bash
modal deploy modal_app.py
```

The app runs in **one container at a time**, because SQLite on a Modal Volume is safe with a single writer only. The first request after an idle period can take 10 seconds or more. Before a live demo, open the app a few minutes early, or keep a container warm with `min_containers=1` in `modal_app.py`, which costs money while it runs.

### Step 7: Copy the backend URL

Modal prints it after deploying:

```
https://<your-username>--educore-ai-school-platform-fastapi-app.modal.run
```

---

## Part 2: Frontend on Vercel

1. In Vercel, choose **Add New**, then **Project**, and import your GitHub repository.
2. Set **Root Directory** to `frontend`. Vercel should detect Vite.
3. Add the environment variable `VITE_API_URL` with your backend URL, with no trailing slash.
4. Click **Deploy**.
5. If the Vercel address differs from `FRONTEND_URL`, update the Modal secret and deploy the backend again. Until they match, browsers cannot reach the API and sign-in shows a connection error.

**Vercel preview deployments** use different addresses, so they are blocked unless you add them to `FRONTEND_URL`.

---

## Part 3: Check it

1. Open your Vercel address and sign in as `admin` with your `ADMIN_PASSWORD`.
2. Open a fee challan and a report card from the Fees and Results pages.
3. Sign out, then confirm that going back to `/dashboard` returns you to the sign-in page.
4. Confirm that `<backend-url>/docs` returns "Not Found".

---

## Rolling back

Passwords are upgraded to bcrypt at first sign-in, and code from before this change cannot read those hashes. If you roll back to older code after signing in, the admin account will not be able to sign in until its password hash is restored from a backup.

The `revoked_tokens` table is new and is created automatically. Older code ignores it, so it does not need removing.
