import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute.jsx";
import RoleGuard from "./components/RoleGuard.jsx";
import DashboardLayout from "./layouts/DashboardLayout.jsx";
import AgentDashboardPage from "./pages/agent/AgentDashboardPage.jsx";
import CertificatesPage from "./pages/agent/CertificatesPage.jsx";
import ComplianceCentrePage from "./pages/agent/ComplianceCentrePage.jsx";
import DocumentsAgreementsPage from "./pages/agent/DocumentsAgreementsPage.jsx";
import FurtherTrainingPage from "./pages/agent/FurtherTrainingPage.jsx";
import LiveCallsPage from "./pages/agent/LiveCallsPage.jsx";
import MembershipPaymentsPage from "./pages/agent/MembershipPaymentsPage.jsx";
import MessagesPage from "./pages/agent/MessagesPage.jsx";
import OnboardingChecklistPage from "./pages/agent/OnboardingChecklistPage.jsx";
import ProfilePage from "./pages/agent/ProfilePage.jsx";
import SupplierAccessPage from "./pages/agent/SupplierAccessPage.jsx";
import TrainingAcademyPage from "./pages/agent/TrainingAcademyPage.jsx";
import TrainingModuleDetailPage from "./pages/agent/TrainingModuleDetailPage.jsx";
import AdminAgentDetailPage from "./pages/admin/AdminAgentDetailPage.jsx";
import AdminAgentListPage from "./pages/admin/AdminAgentListPage.jsx";
import AdminAttendanceLogsPage from "./pages/admin/AdminAttendanceLogsPage.jsx";
import AdminAuditLogsPage from "./pages/admin/AdminAuditLogsPage.jsx";
import AdminCertificatesPage from "./pages/admin/AdminCertificatesPage.jsx";
import AdminComplianceDashboardPage from "./pages/admin/AdminComplianceDashboardPage.jsx";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage.jsx";
import AdminDocumentReviewPage from "./pages/admin/AdminDocumentReviewPage.jsx";
import AdminLiveSessionDetailPage from "./pages/admin/AdminLiveSessionDetailPage.jsx";
import AdminLiveSessionsPage from "./pages/admin/AdminLiveSessionsPage.jsx";
import AdminMessagesPage from "./pages/admin/AdminMessagesPage.jsx";
import AdminMembershipPaymentsPage from "./pages/admin/AdminMembershipPaymentsPage.jsx";
import AdminOnboardingManagementPage from "./pages/admin/AdminOnboardingManagementPage.jsx";
import AdminReportsPage from "./pages/admin/AdminReportsPage.jsx";
import AdminSettingsPage from "./pages/admin/AdminSettingsPage.jsx";
import AdminSupplierAccessPage from "./pages/admin/AdminSupplierAccessPage.jsx";
import AdminTrainingModuleBuilderPage from "./pages/admin/AdminTrainingModuleBuilderPage.jsx";
import AdminTrainingModulesPage from "./pages/admin/AdminTrainingModulesPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import RegisterResultPage from "./pages/RegisterResultPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";

const adminRoles = ["Super Admin", "Organisation Admin", "Admin", "Training Manager", "Compliance Manager"];
const paymentAdminRoles = ["Super Admin", "Organisation Admin", "Admin"];

export default function App() {
  const adminPage = (element) => <RoleGuard allowedRoles={adminRoles}>{element}</RoleGuard>;
  const paymentAdminPage = (element) => <RoleGuard allowedRoles={paymentAdminRoles}>{element}</RoleGuard>;

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/register/success" element={<RegisterResultPage status="success" />} />
      <Route path="/register/cancel" element={<RegisterResultPage status="cancel" />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<AgentDashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/membership" element={<MembershipPaymentsPage />} />
          <Route path="/onboarding" element={<OnboardingChecklistPage />} />
          <Route path="/training" element={<TrainingAcademyPage />} />
          <Route path="/training/:moduleId" element={<TrainingModuleDetailPage />} />
          <Route path="/further-training" element={<FurtherTrainingPage />} />
          <Route path="/live-calls" element={<LiveCallsPage />} />
          <Route path="/documents" element={<DocumentsAgreementsPage />} />
          <Route path="/messages" element={<MessagesPage />} />
          <Route path="/certificates" element={<CertificatesPage />} />
          <Route path="/supplier-access" element={<SupplierAccessPage />} />
          <Route path="/compliance" element={<ComplianceCentrePage />} />
          <Route path="/admin" element={adminPage(<AdminDashboardPage />)} />
          <Route path="/admin/agents" element={adminPage(<AdminAgentListPage />)} />
          <Route path="/admin/agents/:agentId" element={adminPage(<AdminAgentDetailPage />)} />
          <Route path="/admin/membership" element={paymentAdminPage(<AdminMembershipPaymentsPage />)} />
          <Route path="/admin/agents/:agentId/membership" element={paymentAdminPage(<AdminMembershipPaymentsPage />)} />
          <Route path="/admin/onboarding" element={adminPage(<AdminOnboardingManagementPage />)} />
          <Route path="/admin/agents/:agentId/onboarding" element={adminPage(<AdminOnboardingManagementPage />)} />
          <Route path="/admin/training" element={adminPage(<AdminTrainingModulesPage />)} />
          <Route path="/admin/training/new" element={adminPage(<AdminTrainingModuleBuilderPage />)} />
          <Route path="/admin/training/:moduleId/edit" element={adminPage(<AdminTrainingModuleBuilderPage />)} />
          <Route path="/admin/live-sessions" element={adminPage(<AdminLiveSessionsPage />)} />
          <Route path="/admin/live-sessions/:sessionId" element={adminPage(<AdminLiveSessionDetailPage />)} />
          <Route path="/admin/attendance" element={adminPage(<AdminAttendanceLogsPage />)} />
          <Route path="/admin/documents" element={adminPage(<AdminDocumentReviewPage />)} />
          <Route path="/admin/messages" element={adminPage(<AdminMessagesPage />)} />
          <Route path="/admin/compliance" element={adminPage(<AdminComplianceDashboardPage />)} />
          <Route path="/admin/certificates" element={adminPage(<AdminCertificatesPage />)} />
          <Route path="/admin/supplier-access" element={adminPage(<AdminSupplierAccessPage />)} />
          <Route path="/admin/audit-logs" element={adminPage(<AdminAuditLogsPage />)} />
          <Route path="/admin/reports" element={adminPage(<AdminReportsPage />)} />
          <Route path="/admin/settings" element={adminPage(<AdminSettingsPage />)} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
