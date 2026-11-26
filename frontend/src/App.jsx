import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchHealth,
  fetchProjects,
  fetchSessions,
  sendChat,
  updateProjectTodo,
} from "./api";
import AiCommandPanel from "./components/AiCommandPanel";
import ContextHandoffPanel from "./components/ContextHandoffPanel";
import HeaderBar from "./components/HeaderBar";
import ProjectSwitcher from "./components/ProjectSwitcher";

function timestampNow() {
  return new Date().toLocaleTimeString([], {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function App() {
  const [projects, setProjects] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [mcpConnected, setMcpConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [openBrowser, setOpenBrowser] = useState(true);
  const [errorBanner, setErrorBanner] = useState(null);
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [mcpLogs, setMcpLogs] = useState([]);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      actionTaken: "ready",
      text: "SWITCHBOARD orchestrator online. Pick a project card, click a quick prompt, or tell me where you want to pick up.",
    },
  ]);

  const appendLogs = useCallback((lines) => {
    if (!lines || lines.length === 0) return;
    const now = timestampNow();
    setMcpLogs((prev) => [
      ...prev,
      ...lines.map((line) => ({ time: now, line })),
    ]);
  }, []);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    try {
      const [healthRes, projectsRes, sessionsRes] = await Promise.all([
        fetchHealth(),
        fetchProjects(),
        fetchSessions(25),
      ]);
      setMcpConnected(healthRes?.status === "ok");
      setProjects(projectsRes.projects || []);
      setSessions(sessionsRes.sessions || projectsRes.recent_sessions || []);
      setErrorBanner(null);
    } catch (err) {
      setMcpConnected(false);
      setErrorBanner(
        `Backend unreachable (${err.message}). Start FastAPI with: uvicorn backend.main:app --reload --port 8000`
      );
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  const activeProject = useMemo(
    () => projects.find((p) => p.is_active) || projects[0] || null,
    [projects]
  );

  const runChatCommand = async (message, confirmed = false) => {
    if (!confirmed) {
      setMessages((prev) => [...prev, { role: "user", text: message }]);
    }
    setBusy(true);
    setErrorBanner(null);

    try {
      const res = await sendChat({
        message,
        confirmed,
        openBrowser,
      });

      appendLogs(res.mcp_logs || []);

      if (res.requires_confirmation) {
        setPendingConfirmation({
          originalMessage: message,
          prompt: res.confirmation_prompt || res.reply,
        });
      } else {
        setPendingConfirmation(null);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          actionTaken: res.action_taken,
          text: res.reply,
        },
      ]);

      await refreshAll();
    } catch (err) {
      setErrorBanner(`Command failed: ${err.message}`);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          actionTaken: "error",
          text: `Failed to execute command: ${err.message}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const handleSwitchProject = (project) => {
    runChatCommand(`Switch to ${project.name}`, false);
  };

  const handleToggleTodo = async (projectId, index) => {
    try {
      await updateProjectTodo(projectId, { action: "toggle", index });
      await refreshAll();
    } catch (err) {
      setErrorBanner(`Failed to toggle TODO: ${err.message}`);
    }
  };

  const handleAddTodo = async (projectId, text) => {
    try {
      await updateProjectTodo(projectId, { action: "add", text });
      await refreshAll();
    } catch (err) {
      setErrorBanner(`Failed to add TODO: ${err.message}`);
    }
  };

  const handleDeleteTodo = async (projectId, index) => {
    try {
      await updateProjectTodo(projectId, { action: "delete", index });
      await refreshAll();
    } catch (err) {
      setErrorBanner(`Failed to delete TODO: ${err.message}`);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-[#0B0F19] text-slate-100 lg:h-screen lg:overflow-hidden">
      <HeaderBar
        mcpConnected={mcpConnected}
        refreshing={refreshing}
        onRefresh={refreshAll}
      />

      {errorBanner && (
        <div className="shrink-0 border-b border-rose-500/40 bg-rose-500/10 px-4 py-1.5 font-mono text-xs text-rose-300">
          {errorBanner}
        </div>
      )}

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-[minmax(0,35fr)_minmax(0,35fr)_minmax(0,30fr)]">
        <ProjectSwitcher
          projects={projects}
          busy={busy}
          onSwitchProject={handleSwitchProject}
        />

        <ContextHandoffPanel
          activeProject={activeProject}
          sessions={sessions}
          onToggleTodo={handleToggleTodo}
          onAddTodo={handleAddTodo}
          onDeleteTodo={handleDeleteTodo}
        />

        <AiCommandPanel
          messages={messages}
          mcpLogs={mcpLogs}
          busy={busy}
          openBrowser={openBrowser}
          onToggleOpenBrowser={() => setOpenBrowser((prev) => !prev)}
          pendingConfirmation={pendingConfirmation}
          onSendMessage={(msg) => runChatCommand(msg, false)}
          onConfirmAction={() => {
            if (pendingConfirmation) {
              runChatCommand(pendingConfirmation.originalMessage, true);
            }
          }}
          onCancelConfirmation={() => setPendingConfirmation(null)}
          onClearLogs={() => setMcpLogs([])}
        />
      </main>
    </div>
  );
}
