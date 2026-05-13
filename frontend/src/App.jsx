import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute.jsx";
import RoleGuard from "./components/RoleGuard.jsx";
import DashboardLayout from "./layouts/DashboardLayout.jsx";
import DashboardHome from "./pages/DashboardHome.jsx";
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
          <Route path="/dashboard" element={<DashboardHome />} />
          <Route path="/profile" element={<PlaceholderPage title="My Profile" />} />
          <Route path="/membership" element={<PlaceholderPage title="Membership & Payments" />} />
          <Route path="/onboarding" element={<PlaceholderPage title="Onboarding Checklist" />} />
          <Route path="/training" element={<PlaceholderPage title="Training Academy" />} />
          <Route path="/further-training" element={<PlaceholderPage title="Further Training" />} />
          <Route path="/live-calls" element={<PlaceholderPage title="Live Training & Calls" />} />
          <Route path="/documents" element={<PlaceholderPage title="Documents & Agreements" />} />
          <Route path="/certificates" element={<PlaceholderPage title="Certificates" />} />
          <Route path="/supplier-access" element={<PlaceholderPage title="Supplier Access" />} />
          <Route path="/marketing" element={<PlaceholderPage title="Marketing Hub" />} />
          <Route path="/compliance" element={<PlaceholderPage title="Compliance Centre" />} />
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
