import {
  Award,
  BookOpen,
  BriefcaseBusiness,
  CalendarCheck,
  CheckSquare,
  ClipboardList,
  FileCheck2,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  ShieldCheck,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

const navItems = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "My Profile", to: "/profile", icon: UserRound },
  { label: "Membership", to: "/membership", icon: BriefcaseBusiness },
  { label: "Onboarding", to: "/onboarding", icon: CheckSquare },
  { label: "Training", to: "/training", icon: GraduationCap },
  { label: "Further Training", to: "/further-training", icon: BookOpen },
  { label: "Live Calls", to: "/live-calls", icon: CalendarCheck },
  { label: "Documents", to: "/documents", icon: FileCheck2 },
  { label: "Certificates", to: "/certificates", icon: Award },
  { label: "Supplier Access", to: "/supplier-access", icon: ClipboardList },
  { label: "Marketing Hub", to: "/marketing", icon: Megaphone },
  { label: "Compliance", to: "/compliance", icon: ShieldCheck },
];

const adminRoles = ["Super Admin", "Admin", "Training Manager", "Compliance Manager"];

const adminNavItems = [
  { label: "Admin Dashboard", to: "/admin", icon: UsersRound, end: true },
  { label: "Agent List", to: "/admin/agents", icon: UsersRound },
  { label: "Payments Admin", to: "/admin/membership", icon: BriefcaseBusiness },
  { label: "Onboarding Admin", to: "/admin/onboarding", icon: CheckSquare },
  { label: "Training Admin", to: "/admin/training", icon: GraduationCap },
  { label: "Live Sessions", to: "/admin/live-sessions", icon: CalendarCheck },
  { label: "Attendance Logs", to: "/admin/attendance", icon: ClipboardList },
  { label: "Document Review", to: "/admin/documents", icon: FileCheck2 },
  { label: "Compliance Admin", to: "/admin/compliance", icon: ShieldCheck },
  { label: "Certificates Admin", to: "/admin/certificates", icon: Award },
  { label: "Audit Logs", to: "/admin/audit-logs", icon: ClipboardList },
  { label: "Settings", to: "/admin/settings", icon: ClipboardList },
];

export default function DashboardLayout() {
  const { logout, user } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const roleName = user?.role?.name || "User";
  const showAdmin = adminRoles.includes(roleName);

  return (
    <div className="min-h-screen bg-slate-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sea text-sm font-bold text-white">
            OTC
          </div>
          <div>
            <p className="text-sm font-semibold text-ink">One Travel Club</p>
            <p className="text-xs text-slate-500">Onboarding Hub</p>
          </div>
        </div>
        <nav className="flex h-[calc(100vh-4rem)] flex-col gap-1 overflow-y-auto px-3 py-4">
          <NavigationLinks showAdmin={showAdmin} />
        </nav>
      </aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-30 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-slate-950/40"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside className="relative flex h-full w-80 max-w-[86vw] flex-col border-r border-slate-200 bg-white shadow-soft">
            <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
              <div>
                <p className="text-sm font-semibold text-ink">One Travel Club</p>
                <p className="text-xs text-slate-500">Onboarding Hub</p>
              </div>
              <button
                type="button"
                className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-600"
                aria-label="Close navigation"
                title="Close navigation"
                onClick={() => setMobileNavOpen(false)}
              >
                <X size={20} />
              </button>
            </div>
            <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
              <NavigationLinks showAdmin={showAdmin} onNavigate={() => setMobileNavOpen(false)} />
            </nav>
          </aside>
        </div>
      )}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-600 lg:hidden"
              aria-label="Open navigation"
              title="Open navigation"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu size={20} />
            </button>
            <div>
              <p className="text-sm font-semibold text-ink">Travel Agent Onboarding Hub</p>
              <p className="text-xs text-slate-500">{roleName}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <LogOut size={17} />
            Sign out
          </button>
        </header>

        <main className="px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavigationLinks({ showAdmin, onNavigate }) {
  return (
    <>
      {navItems.map((item) => (
        <SidebarLink key={item.to} item={item} onNavigate={onNavigate} />
      ))}
      {showAdmin ? (
        <>
          <div className="mt-4 border-t border-slate-200 pt-4">
            <p className="px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Admin</p>
          </div>
          {adminNavItems.map((item) => (
            <SidebarLink key={item.to} item={item} onNavigate={onNavigate} />
          ))}
        </>
      ) : null}
    </>
  );
}

function SidebarLink({ item, onNavigate }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        [
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition",
          isActive ? "bg-sea text-white" : "text-slate-600 hover:bg-slate-100 hover:text-ink",
        ].join(" ")
      }
    >
      <Icon size={18} />
      <span>{item.label}</span>
    </NavLink>
  );
}
