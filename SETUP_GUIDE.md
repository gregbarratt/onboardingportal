# Setup Guide

This guide explains how to run the Travel Agent Onboarding Hub on your computer.

It is written for a non-developer. Follow one section at a time.

## What You Are Starting

The portal has two parts:

- Backend: the private engine that stores data and checks permissions.
- Frontend: the website you see in the browser.

You normally need two PowerShell windows open:

- One window keeps the backend running.
- One window keeps the frontend running.

If either window is closed, that part of the portal stops.

## Step 1: Check The Project Folder Exists

The project folder is:

```text
C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub
```

Inside it you should see:

- `backend`
- `frontend`
- `README.md`
- `SETUP_GUIDE.md`
- `USER_GUIDE.md`
- `ADMIN_GUIDE.md`

## Step 2: Install Backend Packages

Open PowerShell and run:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

What this does:

- Creates a private Python area for this project.
- Installs the backend tools the app needs.

## Step 3: Add Backend Settings

The backend needs private settings. These settings are kept out of GitHub.

Create or check this file:

```text
C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\.env
```

For local preview, it can contain:

```text
DATABASE_URL="sqlite:///./travel_hub_dev.db"
FRONTEND_URL="http://127.0.0.1:5173"
JWT_SECRET_KEY="change-this-before-real-use"
STRIPE_SECRET_KEY=""
STRIPE_WEBHOOK_SECRET=""
```

Do not put real passwords or secret keys into GitHub.

## Step 4: Prepare The Database

A database stores the portal records.

For a real business setup, this project is prepared for PostgreSQL. PostgreSQL is a reliable business database.

For local preview, SQLite can be used. SQLite is a small database file on your computer.

To apply database migrations, run this from the backend folder:

```powershell
.\.venv\Scripts\activate
alembic upgrade head
```

A migration is a safe database update. It creates or changes the tables the app needs.

## Step 5: Add Demo Data

Demo data lets you test the portal without typing everything in manually.

From the backend folder, run:

```powershell
.\.venv\Scripts\activate
python seed_demo_data.py
```

This creates:

- Staff users
- Demo agents
- Membership records
- Payment records
- Onboarding checklist progress
- Training records
- Live call attendance
- Documents
- Certificates
- Audit logs
- Reports data

## Step 6: Start The Backend

Open PowerShell and run:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
$env:DATABASE_URL="sqlite:///./preview_ui.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Leave this PowerShell window open.

To check it is working, open:

```text
http://127.0.0.1:8001/health
```

You should see:

```json
{
  "status": "ok",
  "message": "Travel Agent Onboarding Hub backend is running"
}
```

You can also open the backend API docs:

```text
http://127.0.0.1:8001/docs
```

## Step 7: Install Frontend Packages

Open a second PowerShell window and run:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\frontend"
npm install
```

What this does:

- Installs the website tools.
- Installs React, Vite, Tailwind CSS, and page dependencies.

## Step 8: Check Frontend Settings

The frontend needs to know where the backend is.

Check this file:

```text
C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\frontend\.env.local
```

It should contain:

```text
VITE_API_BASE_URL="http://127.0.0.1:8001"
```

## Step 9: Start The Frontend

In the second PowerShell window, run:

```powershell
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Leave this PowerShell window open.

## Step 10: Log In

Use this password for all demo accounts:

```text
Password123!
```

Admin login:

```text
admin@example.com
```

Agent login:

```text
david.smith@example.com
```

## Step 11: Run Safety Checks

Backend smoke test:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
.\.venv\Scripts\activate
python phase23_smoke_test.py
```

Frontend build test:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\frontend"
npm run build
```

If both finish without errors, the project is in a healthy state.

## Common Problems

### The login page will not log in

Usually the backend is not running.

Start the backend again:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
$env:DATABASE_URL="sqlite:///./preview_ui.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### `npm` is not recognised

Node.js may not be available in the current PowerShell window.

Close PowerShell, open a fresh PowerShell window, and try again:

```powershell
npm --version
```

### The browser says the site cannot be reached

Check that the correct window is still running:

- Backend should show it is running on `127.0.0.1:8001`.
- Frontend should show it is running on `127.0.0.1:5173`.

### The database looks empty

Run the seed data command again:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
.\.venv\Scripts\activate
python seed_demo_data.py
```

### A port is already in use

This means something is already running on that address.

Close old backend or frontend PowerShell windows, then start them again.

### Frontend build says `Access is denied`

If the normal frontend build hits a Windows folder access message, run this from the `frontend` folder:

```powershell
.\node_modules\.bin\vite.cmd build --configLoader runner --clearScreen false
```

This uses Vite in a way that avoids scanning too far outside the project folder.

## GitHub Push

Use normal Git commands:

```powershell
git status
git add .
git commit -m "Phase X: short description"
git push origin main
```

Or use the helper script:

```powershell
& "C:\Users\gregb\OneDrive\Documents\New project 2\PUSH_TRAVEL_HUB_TO_GITHUB.cmd"
```
