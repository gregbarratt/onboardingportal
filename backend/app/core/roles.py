DEFAULT_ROLES = (
    ("Super Admin", "Full access to the whole system."),
    ("Organisation Admin", "Can manage one organisation and its agents."),
    ("Admin", "Can manage agents, onboarding, payments, and approvals."),
    ("Training Manager", "Can manage training modules and training progress."),
    ("Compliance Manager", "Can manage compliance checks, policies, and documents."),
    ("Agent", "Independent travel agent portal access."),
)

ADMIN_ROLE_NAMES = {
    "Super Admin",
    "Organisation Admin",
    "Admin",
    "Training Manager",
    "Compliance Manager",
}
