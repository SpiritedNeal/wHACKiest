import { useState } from "react";
import {
  Bookmark,
  Check,
  CheckSquare,
  Clock,
  Copy,
  ExternalLink,
  FolderOpen,
  History,
  ListTodo,
  Plus,
  Square,
  Trash2,
} from "lucide-react";

function normalizeTodo(item) {
  if (typeof item === "object" && item !== null) {
    return { text: String(item.text || ""), done: Boolean(item.done) };
  }
  const str = String(item || "");
  const done = str.startsWith("[x] ") || str.startsWith("[X] ");
  return { text: done ? str.slice(4) : str, done };
}

function formatTimestamp(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ContextHandoffPanel({
  activeProject,
  sessions,
  onToggleTodo,
  onAddTodo,
  onDeleteTodo,
}) {
  const [newTodoText, setNewTodoText] = useState("");
  const [copiedPath, setCopiedPath] = useState(false);

  const handleCopyPath = async () => {
    if (!activeProject?.repo_path) return;
    try {
      await navigator.clipboard.writeText(activeProject.repo_path);
      setCopiedPath(true);
      setTimeout(() => setCopiedPath(false), 1500);
    } catch {
      // Clipboard API unavailable in non-HTTPS contexts
    }
  };

  const handleAddSubmit = (e) => {
    e.preventDefault();
    const trimmed = newTodoText.trim();
    if (!trimmed || !activeProject) return;
    onAddTodo(activeProject.id, trimmed);
    setNewTodoText("");
  };

  const todos = (activeProject?.todos || []).map(normalizeTodo);

  return (
    <section className="flex min-h-0 flex-col gap-3">
      {/* Active Workspace Handoff Card */}
      <div className="shrink-0 rounded-xl border border-slate-800/90 bg-slate-900/60 p-3.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Bookmark className="h-4 w-4 text-cyan-400" />
            <h2 className="font-mono text-xs font-semibold tracking-wider text-slate-200 uppercase">
              Where You Left Off
            </h2>
          </div>
          {activeProject && (
            <span className="truncate rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] text-cyan-300">
              {activeProject.id}
            </span>
          )}
        </div>

        {activeProject ? (
          <div className="mt-2.5 space-y-2.5">
            <div className="rounded-lg border border-indigo-500/30 bg-indigo-950/30 p-3">
              <p className="text-xs font-medium text-indigo-200">{activeProject.name}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-200">
                {activeProject.last_handoff_note || "No handoff note captured yet."}
              </p>
            </div>

            <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/70 px-2.5 py-1.5">
              <div className="flex min-w-0 items-center gap-2">
                <FolderOpen className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                <span className="truncate font-mono text-[11px] text-slate-300" title={activeProject.repo_path}>
                  {activeProject.repo_path}
                </span>
              </div>
              <button
                type="button"
                onClick={handleCopyPath}
                className="inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[10px] text-slate-400 transition hover:bg-slate-800 hover:text-slate-200"
                title="Copy local path"
              >
                {copiedPath ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>

            {activeProject.reference_urls?.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {activeProject.reference_urls.map((url) => {
                  let host = url;
                  try {
                    host = new URL(url).hostname.replace(/^www\./, "");
                  } catch {
                    // Keep raw URL fallback
                  }
                  return (
                    <a
                      key={url}
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-md border border-slate-700/80 bg-slate-950 px-2 py-1 font-mono text-[11px] text-slate-300 transition hover:border-cyan-500/50 hover:text-cyan-300"
                    >
                      <span>{host}</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400">Select or switch to a project to view its handoff context.</p>
        )}
      </div>

      {/* Interactive Pending TODOs */}
      <div className="flex min-h-0 flex-1 flex-col rounded-xl border border-slate-800/90 bg-slate-900/50">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800/80 px-3.5 py-2">
          <div className="flex items-center gap-2">
            <ListTodo className="h-4 w-4 text-emerald-400" />
            <h3 className="font-mono text-xs font-semibold tracking-wider text-slate-200 uppercase">
              Pending TODOs
            </h3>
          </div>
          <span className="font-mono text-[11px] text-slate-400">
            {todos.filter((t) => !t.done).length} open
          </span>
        </div>

        <div className="flex-1 space-y-1.5 overflow-y-auto p-3">
          {todos.length === 0 ? (
            <p className="text-xs text-slate-500">No TODOs recorded for this workspace.</p>
          ) : (
            todos.map((todo, idx) => (
              <div
                key={`${idx}-${todo.text}`}
                className="group flex items-start justify-between gap-2 rounded-lg border border-slate-800/70 bg-slate-950/60 px-2.5 py-1.5 hover:border-slate-700"
              >
                <button
                  type="button"
                  onClick={() => activeProject && onToggleTodo(activeProject.id, idx)}
                  className="flex min-w-0 flex-1 items-start gap-2 text-left"
                >
                  {todo.done ? (
                    <CheckSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                  ) : (
                    <Square className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400 group-hover:text-indigo-400" />
                  )}
                  <span
                    className={`text-xs leading-snug ${
                      todo.done ? "text-slate-500 line-through" : "text-slate-200"
                    }`}
                  >
                    {todo.text}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => activeProject && onDeleteTodo(activeProject.id, idx)}
                  className="shrink-0 rounded p-0.5 text-slate-600 opacity-0 transition hover:bg-slate-800 hover:text-rose-400 group-hover:opacity-100"
                  title="Remove TODO"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))
          )}
        </div>

        <form onSubmit={handleAddSubmit} className="shrink-0 border-t border-slate-800/80 p-2.5">
          <div className="flex gap-2">
            <input
              type="text"
              value={newTodoText}
              onChange={(e) => setNewTodoText(e.target.value)}
              placeholder="Add a TODO live during demo..."
              disabled={!activeProject}
              className="min-w-0 flex-1 rounded-lg border border-slate-700/80 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!activeProject || !newTodoText.trim()}
              className="inline-flex items-center gap-1 rounded-lg border border-indigo-500/40 bg-indigo-500/15 px-2.5 py-1.5 text-xs font-medium text-indigo-200 transition hover:bg-indigo-500/25 disabled:cursor-not-allowed disabled:opacity-45"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add</span>
            </button>
          </div>
        </form>
      </div>

      {/* Session Timeline */}
      <div className="flex h-48 shrink-0 flex-col rounded-xl border border-slate-800/90 bg-slate-900/50">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800/80 px-3.5 py-2">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-amber-400" />
            <h3 className="font-mono text-xs font-semibold tracking-wider text-slate-200 uppercase">
              Session Timeline
            </h3>
          </div>
          <span className="font-mono text-[11px] text-slate-400">{sessions.length} snapshots</span>
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto p-3">
          {sessions.length === 0 ? (
            <p className="text-xs text-slate-500">No session snapshots saved yet.</p>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className="rounded-lg border border-slate-800/80 bg-slate-950/60 px-2.5 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[11px] font-semibold text-indigo-300">
                    {session.project_id}
                    {session.git_branch ? ` @ ${session.git_branch}` : ""}
                  </span>
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-500">
                    <Clock className="h-2.5 w-2.5" />
                    {formatTimestamp(session.timestamp)}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-slate-300">
                  {session.handoff_note || session.git_summary}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
