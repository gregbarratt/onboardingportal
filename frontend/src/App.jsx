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
import MarketingHubPage from "./pages/agent/MarketingHubPage.jsx";
import MembershipPaymentsPage from "./pages/agent/MembershipPaymentsPage.jsx";
import OnboardingChecklistPage from "./pages/agent/OnboardingChecklistPage.jsx";
import ProfilePage from "./pages/agent/ProfilePage.jsx";
import SupplierAccessPage from "./pages/agent/SupplierAccessPage.jsx";
import TrainingAcademyPage from "./pages/agent/TrainingAcademyPage.jsx";
import TrainingModuleDetailPage from "./pages/agent/TrainingModuleDetailPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";

const adminRoles = ["Super Admin", "Admin", "Training Manager", "Compliance Manager"];

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />

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
          <Route path="/certificates" element={<CertificatesPage />} />
          <Route path="/supplier-access" element={<SupplierAccessPage />} />
          <Route path="/marketing" element={<MarketingHubPage />} />
          <Route path="/compliance" element={<ComplianceCentrePage />} />
          <Route
            path="/admin"
            element={
              <RoleGuard allowedRoles={adminRoles}>
                <PlaceholderPage title="Admin Dashboard" eyebrow="Admin" />
              </RoleGuard>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
