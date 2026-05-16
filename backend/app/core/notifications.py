AGENT_NOTIFICATION_TYPES = (
    "Welcome email",
    "Payment setup reminder",
    "Payment failed alert",
    "Training assigned",
    "Training overdue",
    "Call booked",
    "Call reminder",
    "Missed call alert",
    "Document required",
    "Document rejected",
    "Approved to trade",
    "Certificate expiring",
    "Message reply",
    "Message status changed",
)

ADMIN_NOTIFICATION_TYPES = (
    "New agent registered",
    "Payment failed",
    "ID uploaded",
    "Document awaiting review",
    "Training failed",
    "Call missed",
    "Final approval ready",
    "Compliance training expired",
    "Agent suspended",
    "Agent message",
)

NOTIFICATION_TYPES = AGENT_NOTIFICATION_TYPES + ADMIN_NOTIFICATION_TYPES
