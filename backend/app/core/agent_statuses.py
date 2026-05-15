AGENT_STATUSES = (
    "Invited",
    "Registered",
    "Payment Pending",
    "Payment Active",
    "Onboarding In Progress",
    "Training In Progress",
    "Awaiting Final Approval",
    "Approved to Trade",
    "Active Agent",
    "Existing Agent",
    "Head Office / Admin Staff",
    "Suspended",
    "Payment Overdue",
    "Compliance Hold",
    "Terminated",
    "Archived",
)

DEFAULT_AGENT_STATUS = "Registered"

EXISTING_AGENT_STATUS = "Existing Agent"
HEAD_OFFICE_ADMIN_STATUS = "Head Office / Admin Staff"
ONBOARDING_TRACKING_EXEMPT_STATUSES = (
    EXISTING_AGENT_STATUS,
    HEAD_OFFICE_ADMIN_STATUS,
)


def is_onboarding_tracking_exempt(status: str | None) -> bool:
    return status in ONBOARDING_TRACKING_EXEMPT_STATUSES
