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
- Phase 10: Documents and agreements
- Phase 11: Compliance centre
- Phase 12: Certificates
- Phase 13: Supplier access and marketing hub
- Phase 14: Audit logs and admin notes
- Phase 15: Notifications
- Phase 16: Frontend setup
- Phase 17: Agent frontend pages
- Phase 18: Admin frontend pages
- Phase 19: Final approval workflow
- Phase 20: Seed data and demo logins
- Phase 21: Admin reports
- Phase 22: Stripe preparation
- Phase 23: Testing and bug fixes

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

## Documents and Agreements

Documents are the contracts, ID checks, proof of address files, policies, bank confirmations, and certificates that support an agent's onboarding record.

This phase records document details, including the file name, file link, document type, signature status, expiry date, review status, and admin notes.

Agents can add and view their own documents. Admins can view documents for any agent and can verify or reject them.

This phase records document links. It does not yet connect to a real file storage service; that can be added later when the portal needs real file uploads.

Document endpoints:

- `POST /agents/{id}/documents`
- `GET /agents/{id}/documents`
- `POST /documents/{id}/verify`
- `POST /documents/{id}/reject`

## Compliance Centre

The Compliance Centre keeps proof that agents have seen and accepted important policies.

It stores policies such as customer money handling rules, advertising and social media rules, data protection, GDPR, complaints process, and general compliance rules.

Agents can view published policies, accept them, and see their own compliance status. Admins can create policies and see a compliance dashboard showing missing documents, expired compliance training, agents on compliance hold, and recent policy acceptance records.

Compliance endpoints:

- `GET /compliance/policies`
- `POST /compliance/policies`
- `POST /compliance/policies/{id}/accept`
- `GET /agents/{id}/compliance-status`
- `GET /admin/compliance-dashboard`

## Certificates

Certificates prove that an agent has completed a training module or assessment.

This phase records certificate details, including the linked agent, linked training module, certificate name, certificate link, issued date, expiry date, renewal requirement, and certificate status.

Agents can view their own certificates. Admins can create certificates and can expire or revoke them when needed.

Certificate statuses are:

- Active
- Expired
- Revoked

Certificate endpoints:

- `GET /agents/{id}/certificates`
- `POST /agents/{id}/certificates`
- `POST /certificates/{id}/expire`
- `POST /certificates/{id}/revoke`

## Supplier Access and Marketing Hub

Supplier Access stores protected supplier portal links, login instructions, access notes, and training requirements.

Marketing Hub stores protected business resources such as brand guidelines, approved logo files, social media templates, approved offer wording, advertising policy guidance, pricing guidance, campaign assets, and downloadable resources.

Supplier Access is locked for agents until they are Approved to Trade. Marketing Hub is locked for agents until they have accepted the social media and advertising policy.

Admins can create supplier and marketing resources. Agents can view the resources only after meeting the access rules.

Supplier types are:

- Tour Operator
- Cruise
- Flight Supplier
- Hotel Supplier
- Transfer Supplier
- Insurance
- Ancillary

Marketing asset types are:

- Brand Guidelines
- Approved Logo File
- Social Media Template
- Approved Offer Wording
- Advertising Policy
- CMA Pricing Guidance
- Campaign Asset
- Downloadable Resource
- Other

Supplier and marketing endpoints:

- `GET /supplier-access`
- `POST /supplier-access`
- `GET /marketing-assets`
- `POST /marketing-assets`

## Audit Logs and Admin Notes

Audit logs are the compliance history of the system. They record important actions such as account creation, payment changes, document checks, training progress, call attendance, approval to trade, suspensions, access changes, and module updates.

Admin notes are private internal notes for the One Travel Club team. Agents cannot see admin notes.

This phase adds the storage and viewing area for audit logs, plus admin-only notes on an agent file. When an admin note is added, the system also creates an audit log entry.

Audit action types are:

- Account created
- Agreement signed
- Payment setup completed
- Payment status changed
- Membership status changed
- Document uploaded
- Document verified
- Training module started
- Training module completed
- Quiz failed
- Quiz passed
- Call attendance marked
- Agent approved to trade
- Agent suspended
- Access level changed
- Admin note added
- Module created
- Module edited
- Module archived

Audit and admin note endpoints:

- `GET /audit-logs`
- `GET /agents/{id}/audit-logs`
- `POST /agents/{id}/admin-notes`
- `GET /agents/{id}/admin-notes`

## Notifications

Notifications are messages inside the portal. They are not emails yet, but the system is ready to show alerts to agents and admins.

Agent notifications include welcome messages, payment reminders, failed payment alerts, training assigned, training overdue, call reminders, missed call alerts, document required, document rejected, approved to trade, and certificate expiring.

Admin notifications include new agent registered, payment failed, ID uploaded, document awaiting review, training failed, call missed, final approval ready, compliance training expired, and agent suspended.

Admins can create notifications. Users can see their own notifications, and admins can see all notifications. Notifications can be marked as read.

Notification endpoints:

- `GET /notifications`
- `POST /notifications`
- `POST /notifications/{id}/read`

## Frontend

The frontend is the visible web portal that agents and admins will use in the browser.

This phase creates the React app foundation with Tailwind CSS styling, routing, login, dashboard layout, sidebar navigation, top bar, API client, authentication context, protected routes, and role guards.

React builds the screens users see. Tailwind CSS controls the visual styling. Protected routes stop people seeing private portal pages unless they are logged in. Role guards stop users seeing areas they do not have permission to access.

Frontend files are in the `frontend` folder.

Frontend commands:

- `npm install`
- `npm run dev`
- `npm run build`

## Agent Frontend Pages

The agent side of the portal now has real pages instead of placeholders.

Agents can use the frontend to view their dashboard, profile, membership and payments, onboarding checklist, training academy, further training, live calls, documents, certificates, supplier access, marketing hub, and compliance centre.

Some sections are deliberately locked by backend rules. For example, supplier access only opens after final approval, and marketing resources only open after the social media and advertising policy has been accepted.

## Admin Frontend Pages

The admin side of the portal now has its own menu and management pages.

Admins can review the dashboard, agent list, agent detail records, memberships and payments, onboarding progress, training modules, live sessions, attendance logs, document review, compliance dashboard, certificates, audit logs, and settings.

These pages use the backend security rules already built in earlier phases. Admin users can manage records, while agents remain limited to their own portal pages.

## Final Approval Workflow

The final approval workflow is the gate before an agent is allowed to trade.

The backend now checks membership, payment setup, signed agreements, verified ID and proof of address, welcome and compliance call attendance, mandatory training, final assessment, and social media policy acceptance.

Admins can see these checks on the Agent Detail page. When every blocking item is complete, the admin can press Approve to Trade. The system then marks the agent as Approved to Trade, completes the Admin final approval checklist step, and creates an audit log entry.

Supplier Access unlocks when the agent status is Approved to Trade. Marketing Hub access still depends on the social media and advertising policy being accepted.

Final approval endpoints:

- `GET /agents/{id}/final-approval`
- `POST /agents/{id}/approve-to-trade`

## Seed Data and Demo Logins

Seed data means sample records that make the portal easier to test.

The Phase 20 seed script creates demo staff users, five demo agents, onboarding progress, training progress, live calls, attendance logs, membership records, payments, documents, certificates, and audit logs.

To load or refresh the demo data, run this from the `backend` folder:

```bash
python seed_demo_data.py
```

All demo accounts use this password:

```text
Password123!
```

Staff demo logins:

- `superadmin@example.com`
- `admin@example.com`
- `training@example.com`
- `compliance@example.com`

Agent demo logins:

- `sarah.jones@example.com` - Onboarding In Progress, payment active
- `mark.evans@example.com` - Payment Pending
- `emma.clarke@example.com` - Awaiting Final Approval
- `david.smith@example.com` - Approved to Trade
- `rachel.brown@example.com` - Suspended for failed payment

## Admin Reports

The Reports page gives admins simple tables for common operational checks.

It includes:

- Agents by status
- Payment status report
- Training completion report
- Overdue training report
- Attendance report
- Compliance expiry report
- Documents awaiting review
- Final approval queue

Admins can open the reports from the admin sidebar or from the admin dashboard shortcut.

Report endpoint:

- `GET /admin/reports`

## Stripe Preparation

Stripe is the payment provider that can later take setup fees and recurring membership payments.

Phase 22 prepares the project for Stripe, but it does not charge real money. The current Stripe code is still in safe placeholder mode.

Prepared Stripe areas:

- Customer creation placeholder
- Subscription creation placeholder
- Subscription cancellation placeholder
- Payment success handler
- Payment failure handler
- Subscription cancelled handler
- Webhook route placeholder

Stripe environment settings:

```text
STRIPE_SECRET_KEY=""
STRIPE_WEBHOOK_SECRET=""
```

These values should stay blank until real Stripe keys are available. When real Stripe keys are added later, the webhook endpoint will be:

```text
POST /stripe/webhook
```

## Testing and Bug Fixes

Phase 23 adds a smoke-test script. A smoke test is a quick safety check that runs the most important workflows and confirms the app still behaves correctly.

The Phase 23 smoke test checks:

- Login
- Role access
- Agent profile access
- Membership and payment update
- Onboarding checklist
- Training progress
- Further training lock
- Live call attendance
- Document upload and verification
- Compliance policy acceptance
- Final approval
- Supplier access unlock
- Marketing access unlock
- Audit logs
- Admin compliance dashboard
- Admin reports

To run it from the `backend` folder:

```bash
python phase23_smoke_test.py
```

The script uses a temporary test database, so it does not change the preview data you use in the browser.
