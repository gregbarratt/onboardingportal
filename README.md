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
