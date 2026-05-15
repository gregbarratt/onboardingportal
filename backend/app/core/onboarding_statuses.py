ONBOARDING_STATUSES = (
    "Not Started",
    "In Progress",
    "Awaiting Review",
    "Complete",
    "Rejected",
    "Overdue",
)

DEFAULT_ONBOARDING_STATUS = "Not Started"

REMOVED_DEFAULT_ONBOARDING_STEP_TITLES = (
    "Create account",
    "Pay setup fee",
    "Set up recurring membership payment",
    "Attend welcome call",
    "Attend compliance call",
    "Complete compliance training",
    "Complete CRM training",
    "Complete supplier training",
    "Accept social media and advertising policy",
)

DEFAULT_ONBOARDING_STEPS = (
    {
        "sort_order": 2,
        "title": "Complete personal profile",
        "description": "Agent completes their contact, business, address, and bank details.",
        "required": True,
        "approval_required": False,
    },
    {
        "sort_order": 3,
        "title": "Upload ID document",
        "description": "Agent uploads a valid ID document for review.",
        "required": True,
        "approval_required": True,
    },
    {
        "sort_order": 4,
        "title": "Upload proof of address",
        "description": "Agent uploads proof of address for review.",
        "required": True,
        "approval_required": True,
    },
    {
        "sort_order": 5,
        "title": "Add bank details for commission payments",
        "description": "Agent adds bank details so commission payments can be processed later.",
        "required": True,
        "approval_required": True,
    },
    {
        "sort_order": 6,
        "title": "Sign contractor agreement",
        "description": "Agent signs the contractor agreement.",
        "required": True,
        "approval_required": True,
    },
    {
        "sort_order": 7,
        "title": "Accept membership terms",
        "description": "Agent accepts the membership terms.",
        "required": True,
        "approval_required": False,
    },
    {
        "sort_order": 16,
        "title": "Complete final assessment",
        "description": "Agent completes the final assessment.",
        "required": True,
        "approval_required": True,
    },
    {
        "sort_order": 17,
        "title": "Admin final approval",
        "description": "Admin gives final approval before the agent can trade.",
        "required": True,
        "approval_required": True,
    },
)
