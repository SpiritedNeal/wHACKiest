export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errData = await response.json();
      detail = errData.detail || detail;
    } catch {
      // Ignore non-JSON error bodies
    }
    throw new Error(detail);
  }

  return response.json();
}

export function fetchHealth() {
  return requestJson("/api/health");
}

export function fetchProjects() {
  return requestJson("/api/projects");
}

export function fetchSessions(limit = 30) {
  return requestJson(`/api/sessions?limit=${limit}`);
}

export function sendChat({ message, confirmed = false, openBrowser = true }) {
  return requestJson("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      confirmed,
      open_browser: openBrowser,
    }),
  });
}

export function updateProjectTodo(projectId, payload) {
  return requestJson(`/api/projects/${encodeURIComponent(projectId)}/todos`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
