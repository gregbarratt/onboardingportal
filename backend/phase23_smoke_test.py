from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


def configure_temporary_database() -> tempfile.TemporaryDirectory[str]:
    temp_dir = tempfile.TemporaryDirectory(prefix="travel-hub-phase23-", ignore_cleanup_errors=True)
    db_path = Path(temp_dir.name) / "phase23_smoke_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["JWT_SECRET_KEY"] = "phase23-smoke-test-only"
    os.environ["FRONTEND_URL"] = "http://127.0.0.1:5173"
    os.environ["UPLOAD_DIR"] = str(Path(temp_dir.name) / "uploads")
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
    admin_token = login("admin@example.com", "Password123!")
    agent_token = login("david.smith@example.com", "Password123!")
    sarah_token = login("sarah.jones@example.com", "Password123!")
    mark_token = login("mark.evans@example.com", "Password123!")
    emma_token = login("emma.clarke@example.com", "Password123!")

    admin_headers = auth_headers(admin_token)
    agent_headers = auth_headers(agent_token)
    sarah_headers = auth_headers(sarah_token)
    mark_headers = auth_headers(mark_token)
    emma_headers = auth_headers(emma_token)

    assert_status("current admin user", client.get("/auth/me", headers=admin_headers), 200)
    assert_status("agent blocked from audit logs", client.get("/audit-logs", headers=agent_headers), 403)

    agents = assert_json("admin agent list", client.get("/agents", headers=admin_headers), 200)
    assert len(agents) >= 5, "Expected at least five demo agents."

    own_agent_list = assert_json("agent own profile list", client.get("/agents", headers=agent_headers), 200)
    assert len(own_agent_list) == 1, "Agent should only see their own profile."

    sarah = find_agent(agents, "sarah.jones@example.com")
    mark = find_agent(agents, "mark.evans@example.com")
    emma = find_agent(agents, "emma.clarke@example.com")
    david = find_agent(agents, "david.smith@example.com")

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


def test_agent_profile(headers: dict[str, str], agent: dict[str, Any]) -> None:
    profile = assert_json("agent profile", client.get(f"/agents/{agent['id']}", headers=headers), 200)
    assert profile["email"] == agent["email"], "Agent profile email did not match."


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
