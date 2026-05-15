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

PAYMENT_ADMIN_ROLE_NAMES = {
    "Super Admin",
    "Organisation Admin",
    "Admin",
}

USER_LEVEL_ADMIN_ROLE_NAMES = {
    "Super Admin",
    "Organisation Admin",
    "Admin",
}

ORGANIZATION_ASSIGNABLE_ROLE_NAMES = {
    "Agent",
    "Training Manager",
    "Admin",
}

SUPER_ADMIN_ASSIGNABLE_ROLE_NAMES = {
    "Agent",
    "Training Manager",
    "Admin",
    "Super Admin",
}

ROLE_ALIASES = {
    "Trainer": "Training Manager",
}


def canonical_role_name(role_name: str) -> str:
    cleaned = role_name.strip()
    return ROLE_ALIASES.get(cleaned, cleaned)
