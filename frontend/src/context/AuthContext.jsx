import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client.js";

const AuthContext = createContext(null);
const TOKEN_STORAGE_KEY = "travel_hub_access_token";
const USER_STORAGE_KEY = "travel_hub_current_user";

function readStoredUser() {
  try {
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);
    return storedUser ? JSON.parse(storedUser) : null;
  } catch (_error) {
    localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState(() => readStoredUser());
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const loadCurrentUser = useCallback(
    async (activeToken = token) => {
      if (!activeToken) {
        setLoading(false);
        return null;
      }

      try {
        const currentUser = await apiClient.get("/auth/me", activeToken);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(currentUser));
        setUser(currentUser);
        return currentUser;
      } catch (error) {
        if (error.status === 401 || error.status === 403) {
          clearSession();
        }
        return null;
      } finally {
        setLoading(false);
      }
    },
    [clearSession, token],
  );

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  async function login(email, password) {
    const response = await apiClient.post("/auth/login", { email, password });
    localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
    setToken(response.access_token);
    setLoading(true);
    return loadCurrentUser(response.access_token);
  }

  function logout() {
    clearSession();
  }

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
    }),
    [loading, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
