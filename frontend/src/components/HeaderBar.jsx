import { Cpu, Layers, RefreshCw, WifiOff } from "lucide-react";

export default function HeaderBar({ mcpConnected, refreshing, onRefresh }) {
  return (
    <header className="shrink-0 border-b border-slate-800/90 bg-slate-950/90 px-4 py-2.5 backdrop-blur-md">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-indigo-500/40 bg-indigo-500/15 text-indigo-400 shadow-[0_0_20px_-4px_rgba(99,102,241,0.45)]">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-sm font-bold tracking-[0.18em] text-slate-50">
                SWITCHBOARD
              </h1>
              <span className="rounded border border-indigo-500/30 bg-indigo-500/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-indigo-300">
                v1.0 MCP
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Your work, remembered. Your workspace, restored.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div
            className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
              mcpConnected
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-rose-500/40 bg-rose-500/10 text-rose-300"
            }`}
          >
            {mcpConnected ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                </span>
                <Cpu className="h-3.5 w-3.5" />
                <span className="font-mono">MCP Server: Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3.5 w-3.5" />
                <span className="font-mono">MCP Server: Offline</span>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-indigo-500/60 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin text-indigo-400" : "text-slate-400"}`} />
            <span>Refresh Git State</span>
          </button>
        </div>
      </div>
    </header>
  );
}
