import {
  Award,
  BarChart3,
  Bell,
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
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { apiClient } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateTime } from "../utils/formatters.js";
import { isProfileComplete } from "../utils/profileCompletion.js";

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

const adminRoles = ["Super Admin", "Organisation Admin", "Admin", "Training Manager", "Compliance Manager"];

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
  { label: "Reports", to: "/admin/reports", icon: BarChart3 },
  { label: "Settings", to: "/admin/settings", icon: ClipboardList },
];

export default function DashboardLayout() {
  const { logout, token, user } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const roleName = user?.role?.name || "User";
  const showAdmin = adminRoles.includes(roleName);

  return (
    <div className="min-h-screen bg-[#edf8fc]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-[#00496b] bg-[#005A83] lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-[#00496b] px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#E83F6F] text-sm font-bold text-white shadow-sm ring-1 ring-white/20">
            OTC
          </div>
          <div>
            <p className="text-sm font-semibold text-white">One Travel Club</p>
            <p className="text-xs text-white/75">Onboarding Hub</p>
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
          <aside className="relative flex h-full w-80 max-w-[86vw] flex-col border-r border-[#00496b] bg-[#005A83] shadow-soft">
            <div className="flex h-16 items-center justify-between border-b border-[#00496b] px-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#E83F6F] text-sm font-bold text-white shadow-sm ring-1 ring-white/20">
                  OTC
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">One Travel Club</p>
                  <p className="text-xs text-white/75">Onboarding Hub</p>
                </div>
              </div>
              <button
                type="button"
                className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/20 text-slate-200"
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
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-[#00496b] bg-[#005A83] px-4 text-white shadow-sm lg:px-8">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/20 text-slate-200 lg:hidden"
              aria-label="Open navigation"
              title="Open navigation"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu size={20} />
            </button>
            <div>
              <p className="text-sm font-semibold text-white">Travel Agent Onboarding Hub</p>
              <p className="text-xs text-white/75">{roleName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <AlertsButton token={token} />
            <button
              type="button"
              onClick={logout}
              className="focus-ring inline-flex items-center gap-2 rounded-lg border border-[#FFBF00] px-3 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              <LogOut size={17} />
              Sign out
            </button>
          </div>
        </header>

        <main className="px-4 py-6 lg:px-8">
          <ProfileCompletionGate token={token} showAdmin={showAdmin}>
            <Outlet />
          </ProfileCompletionGate>
        </main>
      </div>
    </div>
  );
}

function ProfileCompletionGate({ token, showAdmin, children }) {
  const location = useLocation();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(!showAdmin);
  const [error, setError] = useState("");
  const [checkedPath, setCheckedPath] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      if (showAdmin || !token) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const profiles = await apiClient.get("/agents", token);
        if (active) setProfile(profiles?.[0] || null);
      } catch (err) {
        if (active) setError(err?.message || "We could not check your profile.");
      } finally {
        if (active) {
          setCheckedPath(location.pathname);
          setLoading(false);
        }
      }
    }

    void loadProfile();
    return () => {
      active = false;
    };
  }, [location.pathname, showAdmin, token]);

  if (showAdmin || location.pathname === "/profile") {
    return children;
  }

  if (loading || checkedPath !== location.pathname) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm font-medium text-slate-700 shadow-sm">
        Checking your profile details...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-5 text-sm font-medium text-rose-700">
        {error}
      </div>
    );
  }

  if (!profile || !isProfileComplete(profile)) {
    return <Navigate to="/profile" replace state={{ from: location }} />;
  }

  return children;
}

function AlertsButton({ token }) {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const unreadCount = useMemo(() => notifications.filter((notification) => !notification.read).length, [notifications]);
  const visibleNotifications = useMemo(() => notifications.slice(0, 8), [notifications]);

  const loadNotifications = useCallback(
    async (silent = false) => {
      if (!token) return;
      if (!silent) setLoading(true);
      setError("");

      try {
        const result = await apiClient.get("/notifications", token);
        setNotifications(Array.isArray(result) ? result : []);
      } catch (err) {
        setError(err?.message || "Alerts could not be loaded.");
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    loadNotifications();
    const refreshTimer = window.setInterval(() => loadNotifications(true), 60000);
    return () => window.clearInterval(refreshTimer);
  }, [loadNotifications]);

  async function markAsRead(notification) {
    if (notification.read) return;

    try {
      const updated = await apiClient.post(`/notifications/${notification.id}/read`, {}, token);
      setNotifications((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setError(err?.message || "This alert could not be marked as read.");
    }
  }

  async function markAllRead() {
    const unreadNotifications = notifications.filter((notification) => !notification.read);
    if (!unreadNotifications.length) return;

    try {
      const updatedNotifications = await Promise.all(
        unreadNotifications.map((notification) => apiClient.post(`/notifications/${notification.id}/read`, {}, token)),
      );
      const updatedById = new Map(updatedNotifications.map((notification) => [notification.id, notification]));
      setNotifications((current) => current.map((item) => updatedById.get(item.id) || item));
    } catch (err) {
      setError(err?.message || "Alerts could not be marked as read.");
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="focus-ring relative inline-flex items-center gap-2 rounded-lg border border-[#FFBF00] px-3 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
      >
        <Bell size={16} />
        <span className="hidden sm:inline">Alerts</span>
        {unreadCount ? (
          <span className="absolute -right-2 -top-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#E83F6F] px-1 text-xs font-bold text-white ring-2 ring-[#005A83]">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 top-full z-30 mt-2 w-96 max-w-[calc(100vw-2rem)] overflow-hidden rounded-lg border border-slate-200 bg-white text-slate-900 shadow-2xl">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-950">Portal alerts</p>
              <p className="text-xs text-slate-500">{unreadCount ? `${unreadCount} unread alert${unreadCount === 1 ? "" : "s"}` : "No unread alerts"}</p>
            </div>
            <button
              type="button"
              onClick={markAllRead}
              disabled={!unreadCount}
              className="rounded-md px-2 py-1 text-xs font-semibold text-[#005A83] transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              Mark all read
            </button>
          </div>

          <div className="max-h-[70vh] overflow-y-auto">
            {loading ? (
              <div className="p-4 text-sm text-slate-600">Loading alerts...</div>
            ) : error ? (
              <div className="m-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
            ) : visibleNotifications.length ? (
              <div className="divide-y divide-slate-100">
                {visibleNotifications.map((notification) => (
                  <AlertItem
                    key={notification.id}
                    notification={notification}
                    onOpen={() => {
                      void markAsRead(notification);
                      setOpen(false);
                    }}
                    onMarkRead={() => markAsRead(notification)}
                  />
                ))}
              </div>
            ) : (
              <div className="p-5 text-sm text-slate-600">
                <p className="font-semibold text-slate-900">No alerts yet</p>
                <p className="mt-1">Payment issues, training reminders, document reviews, calls, compliance items, and approval notices will appear here.</p>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AlertItem({ notification, onOpen, onMarkRead }) {
  const content = (
    <div className={`block w-full px-4 py-3 text-left transition ${notification.read ? "bg-white hover:bg-slate-50" : "bg-amber-50/70 hover:bg-amber-50"}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-1 h-2.5 w-2.5 rounded-full ${notification.read ? "bg-slate-300" : "bg-[#E83F6F]"}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-semibold text-slate-950">{notification.title}</p>
            <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
              {notification.notification_type}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600">{notification.message}</p>
          <p className="mt-2 text-xs text-slate-400">{formatDateTime(notification.created_at)}</p>
        </div>
      </div>
    </div>
  );

  if (notification.link_url?.startsWith("/")) {
    return (
      <Link to={notification.link_url} onClick={onOpen}>
        {content}
      </Link>
    );
  }

  if (notification.link_url) {
    return (
      <a href={notification.link_url} onClick={onOpen}>
        {content}
      </a>
    );
  }

  return (
    <button type="button" onClick={onMarkRead} className="block w-full">
      {content}
    </button>
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
          <div className="mt-4 border-t border-white/10 pt-4">
            <p className="px-3 text-xs font-semibold uppercase tracking-wide text-white/65">Admin</p>
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
          isActive ? "bg-[#32936F] text-white shadow-sm" : "text-white/85 hover:bg-white/10 hover:text-white",
        ].join(" ")
      }
    >
      <Icon size={18} />
      <span>{item.label}</span>
    </NavLink>
  );
}
