from datetime import date

from pydantic import BaseModel


class AgentsByStatusReportRow(BaseModel):
    id: str
    status: str
    total: int


class PaymentStatusReportRow(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    agent_status: str
    membership_status: str
    payment_status: str
    next_payment_date: date | None = None
    failed_payment_count: int


class TrainingCompletionReportRow(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    agent_status: str
    total_mandatory_modules: int
    completed_mandatory_modules: int
    failed_modules: int
    completion_percent: int


class OverdueTrainingReportRow(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    module_title: str
    due_date: date
    days_overdue: int
    progress_status: str


class AttendanceReportRow(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    session_title: str
    session_type: str
    session_date: date
    attendance_status: str
    follow_up_required: bool


class ComplianceExpiryReportRow(BaseModel):
    id: str
    agent_id: int
    agent_name: str
    item_type: str
    item_name: str
    expiry_date: date
    days_until_expiry: int
    status: str


class DocumentsAwaitingReviewReportRow(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    document_type: str
    file_name: str
    uploaded_date: date
    status: str


class FinalApprovalQueueReportRow(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    agent_status: str
    ready_for_approval: bool
    missing_requirements: list[str]


class AdminReportsRead(BaseModel):
    agents_by_status: list[AgentsByStatusReportRow]
    payment_status_report: list[PaymentStatusReportRow]
    training_completion_report: list[TrainingCompletionReportRow]
    overdue_training_report: list[OverdueTrainingReportRow]
    attendance_report: list[AttendanceReportRow]
    compliance_expiry_report: list[ComplianceExpiryReportRow]
    documents_awaiting_review: list[DocumentsAwaitingReviewReportRow]
    final_approval_queue: list[FinalApprovalQueueReportRow]
