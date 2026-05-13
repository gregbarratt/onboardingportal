import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { getFriendlyError, useApiResource } from "./useAgentPortalData.js";

const resourcePathBuilders = {
  membership: (agentId) => `/agents/${agentId}/membership`,
  payments: (agentId) => `/agents/${agentId}/payments`,
  onboarding: (agentId) => `/agents/${agentId}/onboarding`,
  training: (agentId) => `/agents/${agentId}/training`,
  attendance: (agentId) => `/agents/${agentId}/attendance`,
  documents: (agentId) => `/agents/${agentId}/documents`,
  certificates: (agentId) => `/agents/${agentId}/certificates`,
  auditLogs: (agentId) => `/agents/${agentId}/audit-logs`,
};

export function useAgents() {
  return useApiResource("/agents", {
    initialData: [],
    fallbackError: "We could not load the agent list.",
  });
}

export function useAgent(agentId) {
  return useApiResource(agentId ? `/agents/${agentId}` : "", {
    enabled: Boolean(agentId),
    fallbackError: "We could not load this agent.",
  });
}

export function useAdminAgentRecords(agents, resourceName) {
  const { token } = useAuth();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshIndex, setRefreshIndex] = useState(0);

  const agentList = useMemo(() => agents || [], [agents]);

  useEffect(() => {
    let active = true;
    const buildPath = resourcePathBuilders[resourceName];

    async function loadRecords() {
      if (!token || !buildPath || !agentList.length) {
        setRecords([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const results = await Promise.all(
          agentList.map(async (agent) => {
            try {
              const result = await apiClient.get(buildPath(agent.id), token);
              const items = Array.isArray(result) ? result : result ? [result] : [];
              return items.map((item) => ({ ...item, agent }));
            } catch (_err) {
              return [];
            }
          }),
        );

        if (active) {
          setRecords(results.flat());
        }
      } catch (err) {
        if (active) {
          setError(getFriendlyError(err, "We could not load admin records."));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadRecords();

    return () => {
      active = false;
    };
  }, [agentList, refreshIndex, resourceName, token]);

  return { records, loading, error, reload: () => setRefreshIndex((current) => current + 1) };
}

export function buildAgentName(agent) {
  if (!agent) return "Agent";
  return [agent.first_name, agent.last_name].filter(Boolean).join(" ") || agent.email || `Agent ${agent.id}`;
}
