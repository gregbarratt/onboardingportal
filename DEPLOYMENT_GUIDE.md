# Deployment Guide

This guide explains how to put the Travel Agent Onboarding Hub online.

Deployment means moving the portal from your computer to a hosting company, so you can open it from a normal web address.

## What We Are Using

We are preparing this project for Render.

Render can host three parts for us:

- The frontend, which is the website your agents and admins see.
- The backend, which is the private system that handles logins, agent data, training, documents, payments, and reports.
- PostgreSQL, which is the live database where portal records are stored.

## Important Cost Note

This setup uses a paid backend service because document uploads need a persistent disk. A persistent disk keeps uploaded contracts and documents safe when the app restarts or redeploys.

Render may also charge for the PostgreSQL database.

## What The Deployment File Creates

The `render.yaml` file creates:

- `one-travel-club-onboarding` for the website.
- `one-travel-club-onboarding-api` for the backend.
- `one-travel-club-onboarding-db` for the PostgreSQL database.
- A small upload disk for contracts, ID documents, proof of address files, and certificates.

## Before You Start

Make sure the latest code has been pushed to GitHub.

The GitHub repository is:

`https://github.com/gregbarratt/onboardingportal`

## Step 1: Create A Render Account

Go to:

`https://render.com`

Sign up or log in.

Use the same GitHub account that owns the portal repository.

## Step 2: Create A Blueprint

In Render:

1. Click `New`.
2. Choose `Blueprint`.
3. Connect GitHub if Render asks you to.
4. Select the `gregbarratt/onboardingportal` repository.
5. Render should find the `render.yaml` file.

Render will show the services it is about to create.

## Step 3: Add The Secret Settings

Render will ask for secret values.

Add:

`INITIAL_ADMIN_PASSWORD`

Choose a strong temporary password. This creates the first admin login.

The first admin email will be:

`admin@onetravelclub.co.uk`

For Stripe, you can add either test keys or live keys:

`STRIPE_SECRET_KEY`

Use a Stripe secret key such as `sk_test_...` for testing or `sk_live_...` only when you are ready for live billing data.

`STRIPE_WEBHOOK_SECRET`

You can leave this blank for the first deployment if you have not created the Stripe webhook yet. Add it later after Step 7.

## Step 4: Deploy

Click the Render button to create or apply the Blueprint.

Render will build the backend, create the database, run the database setup, create the first admin account, and build the frontend.

This can take several minutes.

## Step 5: Check The Backend

When the backend has deployed, open:

`https://one-travel-club-onboarding-api.onrender.com/health`

You should see:

```json
{
  "status": "ok",
  "message": "Travel Agent Onboarding Hub backend is running"
}
```

If Render gives the backend a slightly different web address, use that address instead.

## Step 6: Check The Website

Open:

`https://one-travel-club-onboarding.onrender.com`

Log in with:

Email:

`admin@onetravelclub.co.uk`

Password:

The password you entered in Render.

If the login screen loads but login does not work, check the website and backend addresses in Render:

- Backend service setting: `FRONTEND_URL`
- Website service setting: `VITE_API_BASE_URL`

They must point to the real Render web addresses.

## Step 7: Connect Stripe Webhooks

In Stripe:

1. Go to `Developers`.
2. Go to `Webhooks`.
3. Add an endpoint.
4. Use this endpoint URL:

`https://one-travel-club-onboarding-api.onrender.com/stripe/webhook`

If Render gave your backend a different address, use that backend address instead.

Choose these Stripe events:

- `invoice.paid`
- `invoice.payment_failed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Stripe will give you a webhook signing secret that starts with `whsec_`.

Copy that value into Render as:

`STRIPE_WEBHOOK_SECRET`

Then redeploy the backend service.

## Step 8: Import Agents

After the admin login works:

1. Go to the admin agent area.
2. Use the CSV import feature.
3. Import a small test CSV first.
4. Confirm the agent appears correctly.
5. Then import the real agents.

## Step 9: Test The Main Portal Areas

Before inviting real agents, test:

- Admin login.
- Agent list.
- Agent import.
- Agent profile.
- Membership page.
- Stripe subscription sync.
- Stripe invoice sync.
- Document upload.
- Contract upload.
- Onboarding checklist.
- Training academy.
- Reports.

## After Deployment

Every time new code is pushed to GitHub, Render can rebuild and redeploy the portal automatically.

Do not put private Stripe keys, passwords, or database passwords into GitHub. Keep them inside Render environment settings.
