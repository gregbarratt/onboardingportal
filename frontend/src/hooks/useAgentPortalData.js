import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { normaliseProfileValues } from "../utils/profileCompletion.js";

function friendlyError(error, fallback) {
  if (!error) return fallback;
  if (typeof error.detail === "string") return error.detail;
  if (Array.isArray(error.detail)) return error.detail.map((item) => item.msg).join(" ");
  if (error.message) return error.message;
  return fallback;
}

export function useAgentProfile() {
  const { token, user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProfile = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setError("");

    try {
      const profiles = await apiClient.get("/agents", token);
      setProfile(profiles?.[0] || null);
    } catch (err) {
      setError(friendlyError(err, "We could not load the agent profile."));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  return { profile, setProfile, user, loading, error, refreshProfile: loadProfile };
}

export function useApiResource(path, options = {}) {
  const { token } = useAuth();
  const { enabled = true, fallbackError = "We could not load this information." } = options;
  const initialData = useRef(options.initialData || null);
  const [data, setData] = useState(initialData.current);
  const [loading, setLoading] = useState(Boolean(enabled && path));
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token || !path || !enabled) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await apiClient.get(path, token);
      setData(result);
    } catch (err) {
      setError(friendlyError(err, fallbackError));
      setData(initialData.current);
    } finally {
      setLoading(false);
    }
  }, [enabled, fallbackError, path, token]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, setData, loading, error, reload: load };
}

export function useAgentResource(profile, pathBuilder, options = {}) {
  const path = profile ? pathBuilder(profile.id) : "";

  return useApiResource(path, {
    ...options,
    enabled: Boolean(profile && (options.enabled ?? true)),
  });
}

export async function saveAgentProfile({ token, profile, values }) {
  const normalisedValues = normaliseProfileValues(values);
  const payload = {
    ...normalisedValues,
    joining_date: normalisedValues.joining_date || null,
  };

  if (profile?.id) {
    return apiClient.put(`/agents/${profile.id}`, payload, token);
  }

  return apiClient.post("/agents", payload, token);
}

export function getFriendlyError(error, fallback = "Something went wrong.") {
  return friendlyError(error, fallback);
}
