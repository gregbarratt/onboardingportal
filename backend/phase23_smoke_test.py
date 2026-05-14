from __future__ import annotations

import os
import tempfile
import base64
from pathlib import Path
from typing import Any


def configure_temporary_database() -> tempfile.TemporaryDirectory[str]:
    temp_dir = tempfile.TemporaryDirectory(prefix="travel-hub-phase23-", ignore_cleanup_errors=True)
    db_path = Path(temp_dir.name) / "phase23_smoke_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["JWT_SECRET_KEY"] = "phase23-smoke-test-only"
    os.environ["FRONTEND_URL"] = "http://127.0.0.1:5173"
    os.environ["UPLOAD_DIR"] = str(Path(temp_dir.name) / "uploads")
    os.environ["STRIPE_SECRET_KEY"] = ""
    os.environ["STRIPE_WEBHOOK_SECRET"] = ""
    return temp_dir


TEMP_DIR = configure_temporary_database()

from fastapi.testclient import TestClient  # noqa: E402

from app.db.seed_demo_data import seed_demo_data  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


client = TestClient(app)


def main() -> None:
    try:
        seed_demo_data()
        run_smoke_tests()
    finally:
        client.close()
        engine.dispose()
        TEMP_DIR.cleanup()


def run_smoke_tests() -> None:
    superadmin_token = login("superadmin@example.com", "Password123!")
    admin_token = login("admin@example.com", "Password123!")
    agent_token = login("david.smith@example.com", "Password123!")
    sarah_token = login("sarah.jones@example.com", "Password123!")
    mark_token = login("mark.evans@example.com", "Password123!")
    emma_token = login("emma.clarke@example.com", "Password123!")

    superadmin_headers = auth_headers(superadmin_token)
    admin_headers = auth_headers(admin_token)
    agent_headers = auth_headers(agent_token)
    sarah_headers = auth_headers(sarah_token)
    mark_headers = auth_headers(mark_token)
    emma_headers = auth_headers(emma_token)

    assert_status("current admin user", client.get("/auth/me", headers=admin_headers), 200)
    assert_status("agent blocked from audit logs", client.get("/audit-logs", headers=agent_headers), 403)
    assert_status(
        "email test needs SMTP configuration",
        client.post("/admin/email-test", headers=admin_headers, json={"to_email": "admin@example.com"}),
        400,
    )
    test_organizations(superadmin_headers, admin_headers)

    agents = assert_json("admin agent list", client.get("/agents", headers=admin_headers), 200)
    assert len(agents) >= 5, "Expected at least five demo agents."
    onboarding_summary = assert_json("admin onboarding summary", client.get("/admin/onboarding-summary", headers=admin_headers), 200)
    assert len(onboarding_summary) >= 5, "Expected onboarding summary to include demo agents."
    assert "total_steps" in onboarding_summary[0], "Onboarding summary did not include checklist totals."
    admin_dashboard = assert_json("admin dashboard summary", client.get("/admin/dashboard-summary", headers=admin_headers), 200)
    assert admin_dashboard["total_agents"] >= 5, "Expected dashboard summary to include demo agents."
    assert_json("admin membership summary", client.get("/admin/memberships", headers=admin_headers), 200)
    assert_json("admin document summary", client.get("/admin/documents", headers=admin_headers), 200)
    assert_json("admin attendance summary", client.get("/admin/attendance", headers=admin_headers), 200)
    assert_json("admin certificate summary", client.get("/admin/certificates", headers=admin_headers), 200)

    own_agent_list = assert_json("agent own profile list", client.get("/agents", headers=agent_headers), 200)
    assert len(own_agent_list) == 1, "Agent should only see their own profile."

    sarah = find_agent(agents, "sarah.jones@example.com")
    mark = find_agent(agents, "mark.evans@example.com")
    emma = find_agent(agents, "emma.clarke@example.com")
    david = find_agent(agents, "david.smith@example.com")

    test_password_reset(admin_headers, david)
    test_agent_profile(admin_headers, david)
    test_membership_and_payment(admin_headers, mark, mark_headers)
    test_onboarding(admin_headers, emma, mark, emma_headers)
    test_training(admin_headers, sarah, david, sarah_headers, agent_headers)
    test_attendance(admin_headers, david)
    test_documents(admin_headers, mark, mark_headers)
    test_compliance_policy_acceptance(mark_headers)
    test_final_approval(admin_headers, emma)
    test_supplier_and_marketing_access(sarah_headers, agent_headers, emma_headers)
    test_audit_logs(admin_headers, emma)
    test_agent_csv_import(admin_headers)
    test_admin_dashboard_reports(admin_headers)

    print("Phase 23 smoke tests passed.")


def login(email: str, password: str) -> str:
    response = assert_json(
        f"login {email}",
        client.post("/auth/login", json={"email": email, "password": password}),
        200,
    )
    token = response.get("access_token")
    assert token, f"Login for {email} did not return a token."
    return token


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_password_reset(admin_headers: dict[str, str], agent: dict[str, Any]) -> None:
    reset_request = assert_json(
        "admin password reset link",
        client.post(f"/auth/users/{agent['user_id']}/password-reset-link", headers=admin_headers),
        200,
    )
    reset_url = reset_request.get("reset_url", "")
    assert "token=" in reset_url, "Password reset link did not include a token."
    token = reset_url.split("token=", 1)[1]

    assert_json(
        "confirm password reset",
        client.post(
            "/auth/password-reset/confirm",
            json={"token": token, "password": "Password123!"},
        ),
        200,
    )
    login(agent["email"], "Password123!")


def test_agent_profile(headers: dict[str, str], agent: dict[str, Any]) -> None:
    profile = assert_json("agent profile", client.get(f"/agents/{agent['id']}", headers=headers), 200)
    assert profile["email"] == agent["email"], "Agent profile email did not match."
    assert profile["organization_id"], "Agent organisation was missing."
    assert profile["personal_email"], "Agent personal email was missing."
    assert profile["company_email"], "Agent company email was missing."
    assert profile["portal_access_enabled"] is True, "Agent portal access flag was missing."


def test_organizations(superadmin_headers: dict[str, str], admin_headers: dict[str, str]) -> None:
    organizations = assert_json("organizations list", client.get("/organizations", headers=admin_headers), 200)
    assert organizations, "Organisation list was empty."
    assert organizations[0]["slug"] == "one-travel-club", "Default organisation was missing."

    created = assert_json(
        "create organization",
        client.post(
            "/organizations",
            headers=superadmin_headers,
            json={"name": "Partner Travel Company", "slug": "partner-travel-company", "status": "Active"},
        ),
        201,
    )
    assert created["slug"] == "partner-travel-company", "Organisation slug was not saved."

    assert_status(
        "normal admin blocked from creating organization",
        client.post(
            "/organizations",
            headers=admin_headers,
            json={"name": "Blocked Company", "slug": "blocked-company", "status": "Active"},
        ),
        403,
    )


def test_membership_and_payment(admin_headers: dict[str, str], agent: dict[str, Any], agent_headers: dict[str, str]) -> None:
    membership = assert_json("membership", client.get(f"/agents/{agent['id']}/membership", headers=admin_headers), 200)
    assert membership["payment_status"], "Membership payment status was missing."

    updated = assert_json(
        "payment update",
        client.put(
            f"/agents/{agent['id']}/membership",
            headers=admin_headers,
            json={"membership_status": "Active", "payment_status": "Paid", "access_level": "Smoke test access"},
        ),
        200,
    )
    assert updated["membership_status"] == "Active", "Membership status update failed."
    assert updated["payment_status"] == "Paid", "Membership payment update failed."

    stripe_ids = assert_json(
        "manual Stripe IDs update",
        client.put(
            f"/agents/{agent['id']}/membership",
            headers=admin_headers,
            json={"stripe_customer_id": "cus_smoke_test", "stripe_subscription_id": "sub_smoke_test"},
        ),
        200,
    )
    assert stripe_ids["stripe_customer_id"] == "cus_smoke_test", "Stripe customer ID was not saved."

    assert_status(
        "Stripe invoices need configuration",
        client.get(f"/agents/{agent['id']}/stripe/invoices", headers=admin_headers),
        400,
    )
    assert_status(
        "Stripe subscriptions need configuration",
        client.post(f"/agents/{agent['id']}/stripe/subscriptions/sync", headers=admin_headers),
        400,
    )
    assert_status(
        "Stripe billing portal needs configuration",
        client.post(f"/agents/{agent['id']}/stripe/billing-portal", headers=admin_headers),
        400,
    )

    assert_status(
        "agent blocked from creating payment",
        client.post(
            f"/agents/{agent['id']}/payments",
            headers=agent_headers,
            json={
                "amount": "1.00",
                "currency": "GBP",
                "payment_type": "Agent Attempt",
            },
        ),
        403,
    )

    payment = assert_json(
        "create test payment",
        client.post(
            f"/agents/{agent['id']}/payments",
            headers=admin_headers,
            json={
                "amount": "12.50",
                "currency": "GBP",
                "payment_type": "Phase 23 Smoke Test",
                "payment_status": "Pending",
                "notes": "Temporary smoke test payment.",
            },
        ),
        201,
    )
    assert payment["payment_status"] == "Pending", "Payment creation failed."

    logs = assert_json("membership audit logs", client.get(f"/agents/{agent['id']}/audit-logs", headers=admin_headers), 200)
    assert any(log["action_type"] == "Membership status changed" for log in logs), "Membership status audit log was missing."
    assert any(log["action_type"] == "Payment status changed" for log in logs), "Payment status audit log was missing."
    assert any(log["action_type"] == "Access level changed" for log in logs), "Access level audit log was missing."


def test_onboarding(
    admin_headers: dict[str, str],
    ready_agent: dict[str, Any],
    in_progress_agent: dict[str, Any],
    ready_agent_headers: dict[str, str],
) -> None:
    steps = assert_json("onboarding checklist", client.get(f"/agents/{ready_agent['id']}/onboarding", headers=admin_headers), 200)
    assert any(step["step"]["title"] == "Admin final approval" for step in steps), "Onboarding final approval step missing."

    final_approval_step = next(step for step in steps if step["step"]["title"] == "Admin final approval")
    assert_status(
        "agent blocked from completing approval step",
        client.put(
            f"/agents/{ready_agent['id']}/onboarding/{final_approval_step['id']}",
            headers=ready_agent_headers,
            json={"completion_status": "Complete"},
        ),
        403,
    )

    mark_steps = assert_json("in-progress onboarding checklist", client.get(f"/agents/{in_progress_agent['id']}/onboarding", headers=admin_headers), 200)
    id_document_step = next(step for step in mark_steps if step["step"]["title"] == "Upload ID document")
    approved_step = assert_json(
        "onboarding approval notes",
        client.post(
            f"/agents/{in_progress_agent['id']}/onboarding/{id_document_step['id']}/approve",
            headers=admin_headers,
            json={"admin_notes": "Approved during smoke test."},
        ),
        200,
    )
    assert approved_step["completion_status"] == "Complete", "Onboarding approval did not complete the step."
    assert approved_step["admin_notes"] == "Approved during smoke test.", "Onboarding approval notes were not saved."


def test_training(
    admin_headers: dict[str, str],
    sarah: dict[str, Any],
    david: dict[str, Any],
    sarah_headers: dict[str, str],
    david_headers: dict[str, str],
) -> None:
    training = assert_json("agent training", client.get(f"/agents/{sarah['id']}/training", headers=admin_headers), 200)
    assert training, "Training progress did not load."

    assert_status("further training locked", client.get(f"/agents/{sarah['id']}/further-training", headers=sarah_headers), 403)
    assert_json("further training unlocked", client.get(f"/agents/{david['id']}/further-training", headers=david_headers), 200)


def test_attendance(headers: dict[str, str], agent: dict[str, Any]) -> None:
    attendance = assert_json("attendance", client.get(f"/agents/{agent['id']}/attendance", headers=headers), 200)
    assert attendance, "Attendance records did not load."


def test_documents(admin_headers: dict[str, str], agent: dict[str, Any], agent_headers: dict[str, str]) -> None:
    document = assert_json(
        "document upload",
        client.post(
            f"/agents/{agent['id']}/documents",
            headers=agent_headers,
            json={
                "document_type": "Other",
                "file_name": "phase23-smoke-test.txt",
                "file_url": "https://example.com/phase23-smoke-test.txt",
                "notes": "Temporary smoke test document.",
            },
        ),
        201,
    )
    assert document["status"] == "Awaiting Review", "Uploaded document was not awaiting review."

    uploaded_document = assert_json(
        "document file upload",
        client.post(
            f"/agents/{agent['id']}/documents/upload",
            headers=agent_headers,
            json={
                "document_type": "Contractor Agreement",
                "file_name": "contractor-agreement.pdf",
                "file_content_base64": "JVBERi0xLjQgdGVzdCBjb250cmFjdA==",
                "content_type": "application/pdf",
                "requires_signature": True,
                "signed": False,
                "notes": "Temporary uploaded contract test.",
            },
        ),
        201,
    )
    assert uploaded_document["file_name"] == "contractor-agreement.pdf", "Uploaded file name was not stored."
    assert "/uploaded-files/documents/" in uploaded_document["file_url"], "Uploaded file URL was not created."
    assert_status("uploaded document file opens", client.get(uploaded_document["file_url"]), 200)

    verified = assert_json("document verify", client.post(f"/documents/{document['id']}/verify", headers=admin_headers), 200)
    assert verified["status"] == "Verified", "Document verification failed."


def test_compliance_policy_acceptance(agent_headers: dict[str, str]) -> None:
    policies = assert_json("compliance policies", client.get("/compliance/policies", headers=agent_headers), 200)
    assert policies, "Compliance policies did not load."
    acceptance = assert_json(
        "policy acceptance",
        client.post(
            f"/compliance/policies/{policies[0]['id']}/accept",
            headers=agent_headers,
            json={"notes": "Smoke test acceptance."},
        ),
        200,
    )
    assert acceptance["policy_id"] == policies[0]["id"], "Policy acceptance failed."


def test_final_approval(headers: dict[str, str], agent: dict[str, Any]) -> None:
    approval_status = assert_json("final approval status", client.get(f"/agents/{agent['id']}/final-approval", headers=headers), 200)
    assert approval_status["ready_for_approval"], "Emma should be ready for final approval in demo data."

    approved = assert_json("approve to trade", client.post(f"/agents/{agent['id']}/approve-to-trade", headers=headers), 200)
    assert approved["approved_to_trade"], "Approve to Trade did not complete."


def test_supplier_and_marketing_access(
    locked_headers: dict[str, str],
    approved_headers: dict[str, str],
    marketing_headers: dict[str, str],
) -> None:
    assert_status("supplier access locked", client.get("/supplier-access", headers=locked_headers), 403)
    assert_json("supplier access unlocked", client.get("/supplier-access", headers=approved_headers), 200)
    assert_json("marketing access unlocked", client.get("/marketing-assets", headers=marketing_headers), 200)


def test_audit_logs(headers: dict[str, str], agent: dict[str, Any]) -> None:
    logs = assert_json("agent audit logs", client.get(f"/agents/{agent['id']}/audit-logs", headers=headers), 200)
    assert any(log["action_type"] == "Agent approved to trade" for log in logs), "Approval audit log was missing."


def test_agent_csv_import(headers: dict[str, str]) -> None:
    csv_text = "\n".join(
        [
            "agent_id,organization_slug,first_name,last_name,login_email,personal_email,company_email,temporary_password,portal_access_enabled,phone,business_name,status,joining_date,address,postcode,commission_bank_name,commission_account_name,commission_sort_code,commission_account_number,membership_type,membership_status,payment_status,payment_method,setup_fee_amount,monthly_fee_amount,last_payment_date,next_payment_date,failed_payment_count,access_level,stripe_customer_id,stripe_subscription_id,internal_notes",
            "OTC-90001,,CSV,Import,csv.import@example.com,csv.personal@example.com,csv.import@onetravelclub.co.uk,,FALSE,07123 999999,CSV Travel,Live,15/01/2026,\"1 CSV Street, London\",SW1A 1AA,CSV Bank,CSV Import,11-22-33,87654321,Standard,active,past_due,Stripe,99.00,49.00,,15/02/2026,0,Onboarding,cus_csv_import,sub_csv_import,Imported during smoke test",
        ]
    )
    encoded_csv = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    result = assert_json(
        "agent CSV import",
        client.post(
            "/agents/import/csv",
            headers=headers,
            json={"file_name": "agents.csv", "file_content_base64": encoded_csv},
        ),
        200,
    )
    assert result["created"] == 1, "CSV import did not create an agent."
    assert result["errors"] == [], "CSV import returned row errors."
    assert result["next_agent_id"] == "OTC-90002", "Next agent ID was not calculated from imported IDs."

    agents = assert_json("agent list after CSV import", client.get("/agents", headers=headers), 200)
    imported_agent = find_agent(agents, "csv.import@example.com")
    assert imported_agent["agent_id"] == "OTC-90001", "Imported agent ID was not saved."
    assert imported_agent["status"] == "Active Agent", "Imported status alias was not translated."
    assert imported_agent["organization_id"], "Imported agent organisation was not saved."
    assert imported_agent["portal_access_enabled"] is False, "Imported portal access flag was not saved."
    assert imported_agent["company_email"] == "csv.import@onetravelclub.co.uk", "Imported company email was not saved."

    membership = assert_json(
        "imported membership",
        client.get(f"/agents/{imported_agent['id']}/membership", headers=headers),
        200,
    )
    assert membership["stripe_customer_id"] == "cus_csv_import", "Imported Stripe customer ID was not saved."
    assert membership["stripe_subscription_id"] == "sub_csv_import", "Imported Stripe subscription ID was not saved."
    assert membership["membership_status"] == "Active", "Imported membership status alias was not translated."
    assert membership["payment_status"] == "Overdue", "Imported payment status alias was not translated."


def test_admin_dashboard_reports(headers: dict[str, str]) -> None:
    assert_json("admin compliance dashboard", client.get("/admin/compliance-dashboard", headers=headers), 200)
    reports = assert_json("admin reports", client.get("/admin/reports", headers=headers), 200)
    assert reports["payment_status_report"], "Payment report was empty."


def find_agent(agents: list[dict[str, Any]], email: str) -> dict[str, Any]:
    for agent in agents:
        if agent["email"] == email:
            return agent
    raise AssertionError(f"Demo agent not found: {email}")


def assert_json(label: str, response, expected_status: int) -> Any:
    assert_status(label, response, expected_status)
    return response.json()


def assert_status(label: str, response, expected_status: int) -> None:
    assert response.status_code == expected_status, (
        f"{label} expected {expected_status}, got {response.status_code}: {response.text}"
    )


if __name__ == "__main__":
    main()
