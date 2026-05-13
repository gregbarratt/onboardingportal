# Admin Guide

This guide explains how One Travel Club staff manage the Travel Agent Onboarding Hub.

## Admin Login

Open the portal:

```text
http://127.0.0.1:5173
```

Demo staff accounts use this password:

```text
Password123!
```

Demo staff logins:

```text
superadmin@example.com
admin@example.com
training@example.com
compliance@example.com
```

## Admin Dashboard

The admin dashboard gives a quick overview of the portal.

It includes cards for:

- Total agents
- Active agents
- Agents in onboarding
- Awaiting payment setup
- Awaiting final approval
- Failed payments
- Overdue training
- Missed calls
- Compliance hold
- Suspended agents

## Agent List

The Agent List shows all agents.

Use it to find an agent and open their full record.

Admins can see all agents. Agents can only see their own profile.

## Agent Detail

The Agent Detail page brings an agent's key records together.

It is used to review:

- Profile details
- Membership status
- Payment status
- Onboarding progress
- Training progress
- Documents
- Compliance status
- Certificates
- Attendance
- Final approval checks
- Admin notes
- Audit history

## Membership And Payments Admin

Admins can manage membership and payment records.

This includes:

- Membership type
- Setup fee
- Monthly fee
- Membership status
- Payment status
- Payment method
- Last payment date
- Next payment date
- Failed payment count
- Access level
- Internal notes

Agents can view their own membership records, but payment status updates are admin-controlled.

Stripe is prepared for later but does not charge real money in this version.

## Onboarding Management

Admins can manage onboarding checklist steps and agent progress.

Default onboarding steps include:

- Profile completion
- ID document
- Proof of address
- Bank details
- Contractor agreement
- Membership terms
- Payment setup
- Welcome call
- Compliance call
- Required training
- Social media and advertising policy
- Final assessment
- Admin final approval

Some steps require approval. Admins can approve or reject these items.

## Training Module List

Admins can view training modules.

Training modules can be:

- Mandatory or optional
- Published or archived
- Linked to videos, PDFs, or text content
- Given pass marks
- Linked to certificates
- Set to require renewal

## Training Module Builder

Admins can create and edit training modules.

This allows One Travel Club to add more lessons later without creating a separate system.

Further Training uses the same training system.

## Live Training Sessions

Admins can create and manage live training sessions.

Session types include:

- Welcome Call
- Compliance Call
- Systems Training Call
- Sales Process Call
- Marketing Call
- Supplier Training
- Final Sign-Off Call
- Refresher Training
- Further Training
- Team Meeting

Sessions can include meeting links, recording links, required attendance, and follow-up notes.

## Attendance Logs

Admins can record attendance for live sessions.

Attendance statuses include:

- Invited
- Attended
- Missed
- Late
- Rearranged
- Watched Recording
- Excused

Attendance is part of the compliance record.

## Document Review

Admins can review documents uploaded or linked by agents.

Document statuses include:

- Requested
- Uploaded
- Awaiting Review
- Verified
- Rejected
- Expired

Important document types include:

- Contractor Agreement
- Membership Terms
- ID Document
- Proof of Address
- Bank Details Confirmation
- Social Media Policy
- GDPR Policy
- Compliance Policy
- Training Certificate

Admins can open the uploaded file from Document Review, then verify or reject it.

## Compliance Dashboard

The Compliance Dashboard helps staff track compliance risk.

It shows:

- Expired compliance training
- Missing documents
- Agents on compliance hold
- Policy acceptance logs

Admins can also create compliance policies for agents to accept.

## Certificates

Admins can create, expire, and revoke certificates.

Certificates prove that an agent has completed training or assessment requirements.

Certificate statuses include:

- Active
- Expired
- Revoked

## Supplier Access

Supplier Access is a protected resource area.

Admins can add supplier details, including:

- Supplier name
- Supplier type
- Portal URL
- Login instructions
- Access notes
- Training requirement
- Linked training module
- Visibility to agents

Agents only see supplier access after they are Approved to Trade.

## Marketing Hub

Admins can add marketing resources, including:

- Brand guidelines
- Approved logo files
- Social media templates
- Approved offer wording
- Advertising policy
- CMA-compliant pricing guidance
- Campaign assets
- Downloadable resources

Agents only see marketing resources after accepting the social media and advertising policy.

## Audit Logs

Audit logs are the compliance history of the system.

They record important events such as:

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

Audit logs help prove what happened and when.

## Admin Notes

Admin notes are internal only.

Agents cannot see admin notes.

Use admin notes for staff comments, follow-up reminders, and internal decisions.

## Notifications

Notifications are in-portal messages.

Admins can create notifications for agents and staff.

Email sending can be added later.

## Reports

The Reports page includes:

- Agents by status
- Payment status report
- Training completion report
- Overdue training report
- Attendance report
- Compliance expiry report
- Documents awaiting review
- Final approval queue

Reports help admins find the agents who need attention.

## Final Approval Workflow

The final approval workflow is the last gate before an agent can trade.

An agent cannot be Approved to Trade unless:

- Membership is active
- Payment setup is complete
- Contractor agreement is signed
- ID is verified
- Proof of address is verified
- Welcome call is attended
- Compliance call is attended
- Mandatory training is complete
- Final assessment is passed
- Social media policy is accepted
- Admin final approval is completed

When every requirement is met, an admin can approve the agent to trade.

The system then:

- Updates the agent status
- Completes the final onboarding step
- Creates an audit log entry
- Unlocks Supplier Access
- Allows Marketing Hub access if the social media policy is accepted

## Stripe Notes

Stripe is prepared but not live.

This version includes:

- Customer creation placeholder
- Subscription creation placeholder
- Subscription cancellation placeholder
- Payment success handler
- Payment failure handler
- Webhook route placeholder

Do not add real Stripe keys until the business is ready to test real payments.

## Routine Admin Checks

Good daily checks:

- Review final approval queue.
- Check failed payments.
- Check documents awaiting review.
- Check missed calls.
- Check overdue training.
- Check agents on compliance hold.

Good weekly checks:

- Review compliance expiry report.
- Review suspended agents.
- Review audit logs for important changes.
- Check whether new training or policies need adding.
