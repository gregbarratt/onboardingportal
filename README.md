# Travel Agent Onboarding Hub

Travel Agent Onboarding Hub is a secure web portal for One Travel Club.

It helps onboard independent travel agents in one organised place. The hub tracks agent profiles, membership payments, onboarding checklists, training, live call attendance, documents, compliance, certificates, supplier access, notifications, reports, and admin approval before an agent is allowed to trade.

## Project Folders

`backend`

The backend is the private engine of the portal. It is built with Python and FastAPI. It controls logins, permissions, database records, business rules, and API endpoints. An API endpoint is a web address the frontend can ask for information.

`frontend`

The frontend is the visible portal in the browser. It is built with React and Tailwind CSS. React builds the screens. Tailwind controls the design.

## Main Features

- Secure login with JWT tokens
- Staff and agent roles
- Agent profile management
- Agent CSV import with Stripe ID fields
- Membership and payment tracking
- Stripe customer, subscription, invoice sync, and billing portal support
- Onboarding checklist with admin approval
- Training Academy
- Further Training
- Live sessions and attendance logs
- Documents and agreements
- Compliance Centre
- Certificate tracking
- Supplier Access
- Audit logs and admin notes
- Notifications
- Admin reports
- Final approval workflow before an agent can trade
- Demo data and demo logins

## Main Business Rules

- Agents can only see their own private records.
- Admin users can manage all agent records.
- Supplier Access is locked until an agent is Approved to Trade.
- Further Training is locked until mandatory onboarding training is complete.
- An agent cannot be Approved to Trade until the final approval checks are complete.
- Stripe can be connected to register agents through Stripe Checkout, then read customer subscriptions, invoices, payment status, and send agents to Stripe's secure billing portal for card updates.

The final approval checks include:

- Membership is active
- Payment setup is complete
- Contractor agreement is signed
- ID document is verified
- Proof of address is verified
- Welcome call is attended
- Compliance call is attended
- Mandatory training is complete
- Final assessment is passed
- Social media policy is accepted
- Admin final approval is completed

## Requirements

To run the project locally, you need:

- Python
- Node.js
- Git
- PostgreSQL for a real database setup

For local preview and testing, the project can also use SQLite. SQLite is a small local database file on your computer. It is easier for testing, but PostgreSQL is the better choice for a real deployed business app.

## Install Backend

Open PowerShell and run:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Backend Settings

Private settings live in a `.env` file. The project includes `.env.example` as a safe example.

For a simple local preview, this is a useful `.env` setup:

```text
DATABASE_URL="sqlite:///./travel_hub_dev.db"
FRONTEND_URL="http://127.0.0.1:5173"
JWT_SECRET_KEY="change-this-before-real-use"
STRIPE_SECRET_KEY=""
STRIPE_WEBHOOK_SECRET=""
STRIPE_AGENT_SETUP_PRICE_ID=""
STRIPE_AGENT_MONTHLY_PRICE_ID=""
```

Use a Stripe test key first, starting with `sk_test_`. Only use a live key, starting with `sk_live_`, when the business is ready to connect live billing data.

For public agent registration with payment, add a Stripe monthly membership Price ID. Add a setup fee Price ID too if One Travel Club charges a joining fee.

For PostgreSQL, the database setting will look more like this:

```text
DATABASE_URL="postgresql+psycopg://username:password@localhost:5432/travel_agent_onboarding_hub"
```

`DATABASE_URL` tells the backend where the database is and how to connect to it.

## Run Database Migrations

Migrations are safe database change files. They tell the database which tables and columns the app needs.

From the `backend` folder, run:

```powershell
.\.venv\Scripts\activate
alembic upgrade head
```

## Seed Demo Data

Seed data means sample data for testing. It creates staff users, demo agents, training, payments, documents, attendance, certificates, and reports.

From the `backend` folder, run:

```powershell
.\.venv\Scripts\activate
python seed_demo_data.py
```

## Run Backend

For the local browser preview used during this build, run the backend on port 8001:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\backend"
$env:DATABASE_URL="sqlite:///./preview_ui.db"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Keep this PowerShell window open while using the portal.

Backend API docs:

```text
http://127.0.0.1:8001/docs
```

Health check:

```text
http://127.0.0.1:8001/health
```

Expected health check response:

```json
{
  "status": "ok",
  "message": "Travel Agent Onboarding Hub backend is running"
}
```

## Install Frontend

Open a second PowerShell window and run:

```powershell
cd "C:\Users\gregb\OneDrive\Documents\New project 2\Travel Agent Onboarding Hub\frontend"
npm install
```

The frontend uses this local setting in `frontend\.env.local`:

```text
VITE_API_BASE_URL="http://127.0.0.1:8001"
```

## Run Frontend

From the `frontend` folder, run:

```powershell
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Keep this second PowerShell window open while using the portal.

## Demo Logins

All demo accounts use this password:

```text
Password123!
```

Staff logins:

```text
superadmin@example.com
admin@example.com
training@example.com
compliance@example.com
```

Agent logins:

```text
sarah.jones@example.com
mark.evans@example.com
emma.clarke@example.com
david.smith@example.com
rachel.brown@example.com
```

Useful demo agent examples:

- Sarah Jones is in onboarding with payment active.
- Mark Evans is payment pending.
- Emma Clarke is awaiting final approval.
- David Smith is approved to trade.
- Rachel Brown is suspended for failed payment.

## Test The Project

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

The smoke test checks login, role access, agent profiles, memberships, payments, onboarding, training, further training locks, live calls, documents, compliance, final approval, supplier access, marketing access, audit logs, and reports.

## Push To GitHub

GitHub stores the project safely online. A commit is a labelled checkpoint. Each phase is committed so the project history is easy to follow.

Normal Git commands:

```powershell
git status
git add .
git commit -m "Phase X: short description"
git push origin main
```

This computer also has a helper script:

```powershell
& "C:\Users\gregb\OneDrive\Documents\New project 2\PUSH_TRAVEL_HUB_TO_GITHUB.cmd"
```

Use the helper script if normal pushing from Codex is not available.

## Deploy Later

Deployment means putting the portal online so real users can access it.

A future deployment will need:

- A hosted PostgreSQL database
- A hosted FastAPI backend
- A hosted React frontend
- Private environment variables set on the hosting platform
- `DATABASE_URL` pointing to the hosted database
- `FRONTEND_URL` pointing to the live website
- `VITE_API_BASE_URL` pointing to the live backend
- `JWT_SECRET_KEY` set to a long private value
- Stripe keys added only when real payments are ready

Before a real launch:

- Replace all demo passwords.
- Use a real PostgreSQL database.
- Review security settings.
- Move uploaded documents from local storage to proper cloud file storage.
- Connect Stripe using real Stripe keys.
- Enable Stripe's hosted customer portal if agents need to update card details or manage billing.
- Check compliance wording with the business.
- Run the smoke test and a manual user test.

## Extra Guides

More plain-English guides are included:

- `SETUP_GUIDE.md` explains how to install and run the project.
- `USER_GUIDE.md` explains how an agent uses the portal.
- `ADMIN_GUIDE.md` explains how staff manage the portal.
- `DEPLOYMENT_GUIDE.md` explains how to put the portal online.
