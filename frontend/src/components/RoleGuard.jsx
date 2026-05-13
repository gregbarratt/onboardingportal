import UnauthorizedPage from "../pages/UnauthorizedPage.jsx";
import { useAuth } from "../context/AuthContext.jsx";

export default function RoleGuard({ allowedRoles, children }) {
  const { user } = useAuth();
  const roleName = user?.role?.name;

  if (!roleName || !allowedRoles.includes(roleName)) {
    return <UnauthorizedPage />;
  }

  return children;
}
