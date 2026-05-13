COMPLIANCE_POLICY_TYPES = (
    "Customer Money Handling",
    "Advertising and Social Media",
    "Complaints Process",
    "Data Protection and GDPR",
    "Compliance Policy",
    "Membership Terms",
    "Other",
)

COMPLIANCE_POLICY_STATUSES = (
    "Draft",
    "Published",
    "Archived",
)

DEFAULT_COMPLIANCE_POLICY_STATUS = "Published"
DEFAULT_COMPLIANCE_POLICY_VERSION = "1.0"

REQUIRED_COMPLIANCE_DOCUMENT_TYPES = (
    "ID Document",
    "Proof of Address",
    "Contractor Agreement",
)

DEFAULT_COMPLIANCE_POLICIES = (
    {
        "title": "Customer Money Handling Rules",
        "policy_type": "Customer Money Handling",
        "content": "Agents must follow One Travel Club rules for customer payments, receipts, and protected travel money.",
        "version": DEFAULT_COMPLIANCE_POLICY_VERSION,
        "requires_acceptance": True,
        "published_status": DEFAULT_COMPLIANCE_POLICY_STATUS,
    },
    {
        "title": "Advertising and Social Media Rules",
        "policy_type": "Advertising and Social Media",
        "content": "Agents must use approved wording, compliant pricing, and approved advertising claims.",
        "version": DEFAULT_COMPLIANCE_POLICY_VERSION,
        "requires_acceptance": True,
        "published_status": DEFAULT_COMPLIANCE_POLICY_STATUS,
    },
    {
        "title": "Complaints Process",
        "policy_type": "Complaints Process",
        "content": "Agents must follow the One Travel Club complaints process and escalate customer issues promptly.",
        "version": DEFAULT_COMPLIANCE_POLICY_VERSION,
        "requires_acceptance": True,
        "published_status": DEFAULT_COMPLIANCE_POLICY_STATUS,
    },
    {
        "title": "Data Protection and GDPR Policy",
        "policy_type": "Data Protection and GDPR",
        "content": "Agents must protect customer data and follow GDPR responsibilities when handling personal information.",
        "version": DEFAULT_COMPLIANCE_POLICY_VERSION,
        "requires_acceptance": True,
        "published_status": DEFAULT_COMPLIANCE_POLICY_STATUS,
    },
    {
        "title": "General Compliance Policy",
        "policy_type": "Compliance Policy",
        "content": "Agents must complete required checks, training, documents, and policy acceptances before trading.",
        "version": DEFAULT_COMPLIANCE_POLICY_VERSION,
        "requires_acceptance": True,
        "published_status": DEFAULT_COMPLIANCE_POLICY_STATUS,
    },
)
