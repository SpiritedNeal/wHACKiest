import {
  ArrowRightLeft,
  CheckCircle2,
  FolderGit2,
  GitBranch,
  GitCommitHorizontal,
  Play,
  Sparkles,
} from "lucide-react";

export default function ProjectSwitcher({ projects, busy, onSwitchProject }) {
  return (
    <section className="flex min-h-0 flex-col rounded-xl border border-slate-800/90 bg-slate-900/50">
      <div className="flex shrink-0 items-center justify-between border-b border-slate-800/80 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <FolderGit2 className="h-4 w-4 text-indigo-400" />
          <h2 className="font-mono text-xs font-semibold tracking-wider text-slate-200 uppercase">
            Project Workspaces
          </h2>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 font-mono text-[11px] text-slate-300">
          {projects.length} Registered
        </span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {projects.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-800 p-6 text-center text-xs text-slate-400">
            No projects loaded. Start the FastAPI backend on port 8000 and click Refresh Git State.
          </div>
        ) : (
          projects.map((project) => {
            const isActive = Boolean(project.is_active);
            const dirtyCount =
              (project.modified_files?.length || 0) + (project.untracked_files?.length || 0);
            const isClean = Boolean(project.is_clean) && dirtyCount === 0;
            const serviceRunning = Boolean(project.service_status?.running);

            return (
              <article
                key={project.id}
                className={`rounded-xl border p-3.5 transition-all ${
                  isActive
                    ? "border-emerald-500/50 bg-slate-900/95 shadow-[0_0_24px_-6px_rgba(16,185,129,0.28)]"
                    : "border-slate-800 bg-slate-950/65 hover:border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      {isActive && (
                        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]">
                          <Sparkles className="h-2.5 w-2.5" />
                          ACTIVE WORKSPACE
                        </span>
                      )}
                      <span className="font-mono text-[11px] text-slate-500">{project.id}</span>
                    </div>
                    <h3 className="mt-1 truncate text-sm font-semibold text-slate-100">
                      {project.name}
                    </h3>
                  </div>
                </div>

                <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-slate-400">
                  {project.description}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-md border border-slate-700/80 bg-slate-900 px-2 py-0.5 font-mono text-[11px] text-cyan-300">
                    <GitBranch className="h-3 w-3" />
                    {project.branch || "main"}
                  </span>

                  {isClean ? (
                    <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/35 bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
                      <CheckCircle2 className="h-3 w-3" />
                      Clean
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 font-mono text-[11px] text-amber-300">
                      <GitCommitHorizontal className="h-3 w-3" />
                      Dirty ({dirtyCount} modified)
                    </span>
                  )}

                  {serviceRunning && (
                    <span className="inline-flex items-center gap-1 rounded-md border border-indigo-500/40 bg-indigo-500/10 px-2 py-0.5 font-mono text-[11px] text-indigo-300">
                      <Play className="h-3 w-3" />
                      PID {project.service_status.pid}
                    </span>
                  )}
                </div>

                <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-800/80 pt-2.5">
                  <span className="truncate font-mono text-[11px] text-slate-500" title={project.repo_path}>
                    {project.startup_cmd ? `$ ${project.startup_cmd}` : "No background daemon"}
                  </span>

                  <button
                    type="button"
                    disabled={busy || isActive}
                    onClick={() => onSwitchProject(project)}
                    className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                      isActive
                        ? "cursor-default border border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border border-indigo-500/40 bg-indigo-500/15 text-indigo-200 hover:border-indigo-400 hover:bg-indigo-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                    }`}
                  >
                    <ArrowRightLeft className="h-3 w-3" />
                    <span>{isActive ? "Current" : "Switch Here"}</span>
                  </button>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
