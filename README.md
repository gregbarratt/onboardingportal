# Travel Agent Onboarding Hub

Travel Agent Onboarding Hub is a secure web portal for One Travel Club.

Its purpose is to help onboard independent travel agents in one organised place. Over the full build, the hub will manage membership payments, onboarding checklists, training, live call attendance, documents, compliance, certificates, supplier access, marketing resources, and admin approval before an agent is allowed to trade.

## Project Folders

### backend

The `backend` folder will hold the private engine of the app.

Later phases will add the Python and FastAPI code here. This part will manage logins, database records, payments, permissions, and business rules.

### frontend

The `frontend` folder will hold the visible website that agents and admins use.

Later phases will add the React and Tailwind CSS code here. This part will include dashboards, forms, checklists, tables, and buttons.

## What GitHub Is Used For

GitHub is where the project code can be safely stored online.

Each completed phase will be saved as a commit. A commit is like a labelled checkpoint. If something goes wrong later, we can look back at earlier checkpoints and understand what changed.

## Phase Progress

- Phase 0: Project and GitHub setup
- Phase 1: Backend foundation
- Phase 2: Database setup
- Phase 3: Authentication and user roles
- Phase 4: Agent profiles
- Phase 5: Membership and payment tracking
- Phase 6: Onboarding checklist
- Phase 7: Training academy
- Phase 8: Further training
- Phase 9: Live calls and attendance logging

## Backend

The backend is the private engine of the system. It is built with FastAPI, a Python tool for creating web APIs.

An API is a set of web addresses the frontend can talk to. In this phase, there is one simple test address:

`GET /health`

It returns:

```json
{
  "status": "ok",
  "message": "Travel Agent Onboarding Hub backend is running"
}
```

To start the backend later, Python must be installed first. Once Python is installed, use these commands from the `backend` folder:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

`http://127.0.0.1:8000/health`

## Database Setup

The database will store the portal information, such as users, agents, payments, training progress, documents, and approvals.

This project is prepared for PostgreSQL. PostgreSQL is a reliable database system often used for business web apps.

The backend reads the database connection from `DATABASE_URL`. That value lives in a private `.env` file later. The safe example is shown in `.env.example`.

Alembic is also set up. Alembic tracks database changes in small files called migrations. A migration is like a database checkpoint: it says what changed and lets us apply those changes in the right order.

To check that Alembic can see its migration files, use this command from the `backend` folder:

```bash
alembic heads
```

Once a real PostgreSQL database exists and `DATABASE_URL` has real details, `alembic current` can show which migration the database has reached.

This phase does not create business tables yet. Those start in Phase 3 and Phase 4.

## Authentication

Authentication means proving who someone is before they can use private parts of the portal.

This project now has basic user accounts, password protection, login tokens, and roles.

The built-in roles are:

- Super Admin
- Admin
- Training Manager
- Compliance Manager
- Agent

Agents and admins need different roles because they should not see or change the same information. For example, an agent should see their own onboarding tasks, while an admin can later approve agents and manage compliance.

A login token is a temporary digital pass. After someone logs in, the backend gives them a token. The frontend will send that token back with future requests so the backend knows who is using the portal.

Authentication endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Registration currently creates an `Agent` user. Admin users will be created through controlled setup and seed data in later phases.

## Agent Profiles

An agent profile stores the business and contact information for a travel agent.

It is linked to a user account. The user account is for logging in; the agent profile is for the agent's onboarding record.

Agent profile information includes:

- Name and contact details
- Business name
- Agent status
- Joining date
- Address and postcode
- Bank details for commission payments

Admins can see and manage all agent profiles. Agents can only see their own profile. Agents can update their own personal details, but only an admin can update an agent status.

Agent profile endpoints:

- `POST /agents`
- `GET /agents`
- `GET /agents/{id}`
- `PUT /agents/{id}`

## Membership and Payment Tracking

This phase tracks membership and payment information, but it does not charge real money.

Membership records store the agent's membership type, setup fee, monthly fee, membership status, payment status, Stripe reference fields, key payment dates, access level, and internal notes.

Payment records store individual payment entries, such as setup fees, monthly fees, manual payments, failed payments, refunds, invoice links, and notes.

Stripe is not fully connected yet. Placeholder functions have been added so a real Stripe connection can be added safely in a later phase.

Membership and payment endpoints:

- `GET /agents/{id}/membership`
- `PUT /agents/{id}/membership`
- `POST /agents/{id}/payments`
- `GET /agents/{id}/payments`

Agents can view their own membership and payments. Admins can manage membership and payment status. Payment status changes will be connected to audit logs in a later phase.

## Onboarding Checklist

The onboarding checklist is the set of steps an agent must complete before they can trade.

It includes profile completion, ID and proof of address checks, bank details, agreements, membership payment setup, welcome and compliance calls, training, social media policy acceptance, final assessment, and admin final approval.

Admins can create or update checklist steps. Agents can see their own checklist and add notes or evidence links. Admins can approve checklist items that need review.

Onboarding endpoints:

- `GET /onboarding/steps`
- `POST /onboarding/steps`
- `PUT /onboarding/steps/{id}`
- `GET /agents/{id}/onboarding`
- `PUT /agents/{id}/onboarding/{progress_id}`
- `POST /agents/{id}/onboarding/{progress_id}/approve`

## Training Academy

The Training Academy stores lessons that agents complete during onboarding and later development.

Training modules can include text, videos, PDFs, external links, quizzes, pass marks, certificates, and renewal settings.

The default mandatory modules have been added, including welcome training, travel sales basics, compliance, CRM, supplier training, social media policy, GDPR, and the final assessment.

Admins can create, update, publish, archive, and assign training modules. Agents can see their assigned training and update their own progress, while admin-only result fields such as scores and certificates stay protected.

Training endpoints:

- `GET /training/modules`
- `POST /training/modules`
- `GET /training/modules/{id}`
- `PUT /training/modules/{id}`
- `POST /training/modules/{id}/publish`
- `POST /training/modules/{id}/archive`
- `POST /training/modules/{id}/assign`
- `GET /agents/{id}/training`
- `PUT /agents/{id}/training/{progress_id}`

## Further Training

Further Training is the ongoing development area for agents after onboarding training is complete.

It reuses the Training Academy system, so further training modules can still have categories, videos, PDFs, quizzes, pass marks, certificates, renewal settings, and admin assignment.

Further Training stays locked for an agent until all mandatory onboarding training is complete. Admins can mark any further training module as mandatory later.

Example optional modules have been added, including sales development, destination knowledge, cruise, Disney, marketing, compliance refresher, and advanced CRM training.

Further training endpoints:

- `GET /further-training`
- `GET /agents/{id}/further-training`

## Live Calls and Attendance Logging

Live calls are online sessions such as welcome calls, compliance calls, systems training, supplier training, team meetings, and final sign-off calls.

This phase records the session details and keeps an attendance history for each agent. That means the portal can show who was invited, who attended, who missed a call, who arrived late, and who watched a recording later.

Attendance becomes part of the agent's compliance record because some onboarding calls must be completed before an agent can be approved to trade.

Live call and attendance endpoints:

- `POST /live-sessions`
- `GET /live-sessions`
- `GET /live-sessions/{id}`
- `PUT /live-sessions/{id}`
- `POST /live-sessions/{id}/assign`
- `POST /live-sessions/{id}/attendance`
- `POST /live-sessions/{id}/attendance/bulk`
- `GET /agents/{id}/attendance`
