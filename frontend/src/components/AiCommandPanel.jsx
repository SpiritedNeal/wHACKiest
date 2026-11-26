import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  Globe,
  Send,
  Terminal,
  Trash2,
  User,
} from "lucide-react";

const DEMO_CHIPS = [
  "Save my SIH progress",
  "Switch to my IEEE paper",
  "What was unfinished in IEEE paper?",
  "Take me back to SIH",
];

function colorizeMcpLog(line) {
  if (line.includes("error=")) return "text-rose-400";
  if (line.includes("open_vscode_workspace")) return "text-cyan-300";
  if (line.includes("open_project_references")) return "text-indigo-300";
  if (line.includes("inspect_git_status")) return "text-emerald-300";
  if (line.includes("check_or_start_service")) return "text-amber-300";
  return "text-slate-300";
}

export default function AiCommandPanel({
  messages,
  mcpLogs,
  busy,
  openBrowser,
  onToggleOpenBrowser,
  pendingConfirmation,
  onSendMessage,
  onConfirmAction,
  onCancelConfirmation,
  onClearLogs,
}) {
  const [input, setInput] = useState("");
  const chatEndRef = useRef(null);
  const logEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingConfirmation]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mcpLogs]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || busy) return;
    onSendMessage(trimmed);
    setInput("");
  };

  return (
    <section className="flex min-h-0 flex-col gap-3">
      {/* AI Command Chat */}
      <div className="flex min-h-0 flex-[3] flex-col rounded-xl border border-slate-800/90 bg-slate-900/50">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800/80 px-3.5 py-2">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-indigo-400" />
            <h2 className="font-mono text-xs font-semibold tracking-wider text-slate-200 uppercase">
              AI Command Center
            </h2>
          </div>

          <button
            type="button"
            onClick={onToggleOpenBrowser}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition ${
              openBrowser
                ? "border-cyan-500/45 bg-cyan-500/15 text-cyan-300"
                : "border-slate-700 bg-slate-900 text-slate-400"
            }`}
            title="Toggle opening saved project reference URLs during switches"
          >
            <Globe className="h-3 w-3" />
            <span>Open Browser Tabs: {openBrowser ? "ON" : "OFF"}</span>
          </button>
        </div>

        {/* Message History */}
        <div className="flex-1 space-y-2.5 overflow-y-auto p-3">
          {messages.map((msg, index) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={index}
                className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-indigo-500/40 bg-indigo-500/15 text-indigo-300">
                    <Bot className="h-3.5 w-3.5" />
                  </div>
                )}

                <div
                  className={`max-w-[88%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                    isUser
                      ? "border border-indigo-500/40 bg-indigo-600/25 text-slate-100"
                      : "border border-slate-800 bg-slate-950/85 text-slate-200"
                  }`}
                >
                  {msg.actionTaken && (
                    <div className="mb-1 flex items-center gap-1.5">
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                        {msg.actionTaken}
                      </span>
                    </div>
                  )}
                  <div className="whitespace-pre-wrap">{msg.text}</div>
                </div>

                {isUser && (
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-700 bg-slate-800 text-slate-300">
                    <User className="h-3.5 w-3.5" />
                  </div>
                )}
              </div>
            );
          })}

          {busy && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
              <span className="font-mono">Orchestrating MCP tools...</span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Safety Confirmation Banner */}
        {pendingConfirmation && (
          <div className="mx-3 mb-2 shrink-0 rounded-xl border border-amber-500/60 bg-amber-500/15 p-3 shadow-[0_0_20px_-6px_rgba(245,158,11,0.4)]">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <div className="min-w-0 flex-1">
                <p className="font-mono text-[11px] font-semibold tracking-wider text-amber-300 uppercase">
                  Safety Confirmation Required
                </p>
                <p className="mt-1 text-xs leading-snug text-amber-100">
                  {pendingConfirmation.prompt}
                </p>
                <div className="mt-2.5 flex items-center gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={onConfirmAction}
                    className="rounded-lg border border-amber-400/60 bg-amber-500 px-2.5 py-1 text-xs font-semibold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50"
                  >
                    Confirm &amp; Proceed
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={onCancelConfirmation}
                    className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-300 transition hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Quick Demo Chips + Chat Input */}
        <div className="shrink-0 space-y-2 border-t border-slate-800/80 p-2.5">
          <div className="flex flex-wrap gap-1.5">
            {DEMO_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                disabled={busy}
                onClick={() => onSendMessage(chip)}
                className="rounded-full border border-slate-700/90 bg-slate-950/90 px-2.5 py-1 text-[11px] text-slate-300 transition hover:border-indigo-500/60 hover:bg-indigo-500/15 hover:text-indigo-200 disabled:opacity-50"
              >
                {chip}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='Ask SWITCHBOARD (e.g. "Switch to IEEE paper")...'
              className="min-w-0 flex-1 rounded-lg border border-slate-700/80 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="inline-flex items-center gap-1 rounded-lg border border-indigo-500/50 bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-45"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </form>
        </div>
      </div>

      {/* Live MCP Tool Execution Log */}
      <div className="flex min-h-0 flex-[2] flex-col rounded-xl border border-slate-800/90 bg-[#060911]">
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800/80 px-3.5 py-2">
          <div className="flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5 text-emerald-400" />
            <h3 className="font-mono text-[11px] font-semibold tracking-wider text-slate-200 uppercase">
              Live MCP Execution Log
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-slate-500">
              {mcpLogs.length} events
            </span>
            {mcpLogs.length > 0 && (
              <button
                type="button"
                onClick={onClearLogs}
                className="rounded p-0.5 text-slate-500 transition hover:bg-slate-800 hover:text-slate-300"
                title="Clear MCP log"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 space-y-1 overflow-y-auto p-3 font-mono text-[11px]">
          {mcpLogs.length === 0 ? (
            <p className="text-slate-600">
              &gt; Waiting for MCP tool invocations (inspect_git_status, open_vscode_workspace, open_project_references, check_or_start_service)...
            </p>
          ) : (
            mcpLogs.map((entry, idx) => (
              <div key={idx} className="leading-relaxed break-words">
                <span className="mr-1.5 text-slate-600">[{entry.time}]</span>
                <span className={colorizeMcpLog(entry.line)}>{entry.line}</span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </section>
  );
}
