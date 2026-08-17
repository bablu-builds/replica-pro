import { useEffect, useMemo, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Ban,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Clock3,
  Code2,
  Copy,
  ExternalLink,
  FileCode2,
  GitPullRequest,
  Info,
  Layers3,
  Menu,
  MoreHorizontal,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  StopCircle,
  Terminal,
  Timer,
  Workflow,
  X,
} from 'lucide-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { Route, Switch, useLocation, Router as WouterRouter } from 'wouter';

const queryClient = new QueryClient();

type Mode = 'mock' | 'dry-run';
type TaskStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
type RunStatus = 'queued' | 'running' | 'completed' | 'partial' | 'cancelled' | 'failed';

type Task = {
  id: string;
  name: string;
  description: string;
  status: TaskStatus;
  worker: string;
  duration: string;
  dependencies: string[];
  outputFiles: string[];
};

type Run = {
  id: string;
  request: string;
  mode: Mode;
  status: RunStatus;
  startedAt: string;
  duration: string;
  progress: number;
  tasks: Task[];
  warnings: string[];
  errors: string[];
};

type Result = {
  summary: string;
  repository: string;
  pullRequests: string[];
  warnings: string[];
  errors: string[];
};

const taskBlueprints = [
  ['Parse request', 'Turn the project brief into constraints and acceptance criteria.', 'Planner'],
  ['Draft execution plan', 'Sequence work into independently observable agent tasks.', 'Planner'],
  ['Scaffold workspace', 'Prepare the proposed file tree and local configuration changes.', 'Builder'],
  ['Implement core path', 'Build the smallest safe vertical slice against the plan.', 'Builder'],
  ['Run quality checks', 'Review types, tests, and boundary conditions before handoff.', 'Verifier'],
  ['Prepare handoff', 'Summarize changes and produce a review-ready result.', 'Verifier'],
  ['Sanitize output', 'Remove credentials, local paths, and unsafe command fragments.', 'Sentinel'],
  ['Package evidence', 'Collect outputs into a compact, inspectable run record.', 'Sentinel'],
];

const makeTask = (index: number, status: TaskStatus = 'queued'): Task => {
  const [name, description, worker] = taskBlueprints[index % taskBlueprints.length];
  return {
    id: `task-${index + 1}`,
    name,
    description,
    status,
    worker,
    duration: status === 'completed' ? `${8 + index * 3}.${index + 2}s` : '—',
    dependencies: index === 0 ? [] : [`task-${index}`],
    outputFiles: index % 2 === 0 ? [`notes/${index + 1}-brief.md`] : [`plan/${index + 1}-execution.json`],
  };
};

const sampleRun: Run = {
  id: 'rmao-042',
  request: 'Add a quiet mode to the CLI and document the new flag.',
  mode: 'mock',
  status: 'completed',
  startedAt: 'Today, 09:42',
  duration: '01m 48s',
  progress: 100,
  tasks: Array.from({ length: 6 }, (_, index) => makeTask(index, 'completed')),
  warnings: ['Provider is simulated. No repository was changed.'],
  errors: [],
};

const partialRun: Run = {
  id: 'rmao-041',
  request: 'Add request tracing to the dashboard worker.',
  mode: 'dry-run',
  status: 'partial',
  startedAt: 'Yesterday, 16:18',
  duration: '02m 12s',
  progress: 83,
  tasks: [
    makeTask(0, 'completed'),
    makeTask(1, 'completed'),
    makeTask(2, 'completed'),
    { ...makeTask(3), status: 'failed', duration: '19.2s' },
    makeTask(4, 'completed'),
    makeTask(5, 'queued'),
  ],
  warnings: ['One worker stopped before producing an output file.'],
  errors: ['Verifier could not access the simulated trace fixture.'],
};

function SignalMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`relative inline-flex items-center justify-center ${small ? 'size-7' : 'size-9'}`} aria-hidden="true">
      <span className="absolute inset-0 rotate-45 rounded-[9px] border border-primary/70 bg-primary/10" />
      <span className={`${small ? 'size-2' : 'size-2.5'} relative rounded-full bg-primary shadow-[0_0_0_4px_hsl(var(--primary)/.15)]`} />
    </span>
  );
}

function StatusPill({ status }: { status: RunStatus | TaskStatus }) {
  const config: Record<string, { label: string; classes: string; icon: typeof Check }> = {
    completed: { label: 'Completed', classes: 'bg-secondary text-secondary-foreground', icon: Check },
    running: { label: 'Running', classes: 'bg-primary/15 text-primary', icon: Activity },
    queued: { label: 'Queued', classes: 'bg-muted text-muted-foreground', icon: Clock3 },
    partial: { label: 'Partial', classes: 'bg-accent/35 text-accent-foreground', icon: AlertTriangle },
    failed: { label: 'Failed', classes: 'bg-destructive/12 text-destructive', icon: AlertTriangle },
    cancelled: { label: 'Cancelled', classes: 'bg-muted text-muted-foreground', icon: Ban },
  };
  const item = config[status] ?? config.queued;
  const Icon = item.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide ${item.classes}`} data-testid={`status-${status}`}>
      <Icon className="size-3" strokeWidth={2.2} />
      {item.label}
    </span>
  );
}

function TaskRow({ task, index }: { task: Task; index: number }) {
  const icon = task.status === 'completed' ? <Check className="size-3.5" /> : task.status === 'running' ? <Activity className="size-3.5 animate-signal" /> : task.status === 'failed' ? <X className="size-3.5" /> : <span className="size-1.5 rounded-full bg-current" />;
  const iconClass = task.status === 'completed' ? 'bg-secondary text-secondary-foreground' : task.status === 'running' ? 'bg-primary text-primary-foreground' : task.status === 'failed' ? 'bg-destructive text-destructive-foreground' : 'bg-muted text-muted-foreground';
  return (
    <div className={`group grid grid-cols-[28px_1fr_auto] items-start gap-3 border-b border-border/70 px-4 py-3.5 last:border-b-0 ${task.status === 'running' ? 'bg-primary/[.035]' : ''}`} data-testid={`row-task-${task.id}`}>
      <div className="relative flex justify-center">
        <span className={`mt-0.5 flex size-6 items-center justify-center rounded-full ${iconClass}`}>{icon}</span>
        {index < 7 && <span className="absolute top-7 h-6 w-px bg-border group-last:hidden" />}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-semibold text-foreground">{task.name}</p>
          {task.status === 'running' && <span className="font-mono text-[10px] uppercase tracking-[.15em] text-primary">active</span>}
        </div>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{task.description}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[10px] text-muted-foreground">
          <span className="rounded bg-muted px-1.5 py-0.5">{task.worker}</span>
          <span>{task.duration}</span>
          {task.outputFiles[0] && <span className="hidden items-center gap-1 sm:flex"><FileCode2 className="size-3" />{task.outputFiles[0]}</span>}
        </div>
      </div>
      <StatusPill status={task.status} />
    </div>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const jumpTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setMobileOpen(false);
  };
  return (
    <div className="grain min-h-[100dvh] bg-background text-foreground">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[258px] flex-col bg-sidebar text-sidebar-foreground transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-[76px] items-center gap-3 border-b border-sidebar-border px-6">
          <SignalMark />
          <div>
            <p className="font-semibold tracking-[-.03em]">RMAO</p>
            <p className="font-mono text-[9px] uppercase tracking-[.22em] text-sidebar-foreground/55">run / make / observe</p>
          </div>
          <button className="ml-auto rounded-lg p-1.5 text-sidebar-foreground/55 hover:bg-sidebar-accent hover:text-sidebar-foreground lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation" data-testid="button-close-navigation"><X className="size-4" /></button>
        </div>
        <div className="px-4 py-6">
          <p className="px-2 text-[10px] font-semibold uppercase tracking-[.2em] text-sidebar-foreground/45">Control room</p>
          <nav className="mt-3 space-y-1">
            <button onClick={() => jumpTo('new-run')} className="flex w-full items-center gap-3 rounded-xl bg-sidebar-primary/15 px-3 py-2.5 text-left text-sm font-medium text-sidebar-foreground" data-testid="button-nav-overview"><Activity className="size-4 text-sidebar-primary" />Overview<span className="ml-auto size-1.5 rounded-full bg-sidebar-primary" /></button>
            <button onClick={() => jumpTo('run-history')} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-sidebar-foreground/65 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground" data-testid="button-nav-history"><Clock3 className="size-4" />Run history</button>
            <button onClick={() => jumpTo('system-health')} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-sidebar-foreground/65 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground" data-testid="button-nav-health"><ShieldCheck className="size-4" />System health</button>
          </nav>
        </div>
        <div className="mt-auto border-t border-sidebar-border p-5">
          <div className="rounded-2xl border border-sidebar-border bg-sidebar-accent/55 p-4">
            <div className="flex items-center gap-2 text-xs font-medium"><span className="size-2 rounded-full bg-secondary shadow-[0_0_0_3px_hsl(var(--secondary)/.13)]" />Simulated provider</div>
            <p className="mt-2 text-[11px] leading-relaxed text-sidebar-foreground/55">Safe by default. Nothing leaves this browser in the demo.</p>
            <div className="mt-4 flex items-center justify-between font-mono text-[9px] uppercase tracking-[.14em] text-sidebar-foreground/40"><span>build</span><span>local / 0.8.4</span></div>
          </div>
        </div>
      </aside>
      {mobileOpen && <button className="fixed inset-0 z-30 bg-sidebar/30 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" data-testid="button-navigation-overlay" />}
      <div className="lg:pl-[258px]">
        <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-border/80 bg-background/90 px-4 backdrop-blur-md sm:px-8">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="rounded-xl border border-border bg-card p-2 lg:hidden" aria-label="Open navigation" data-testid="button-open-navigation"><Menu className="size-4" /></button>
            <div className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex"><span>Workspace</span><ChevronDown className="size-3" /><span className="font-medium text-foreground">Local control room</span></div>
            <div className="flex items-center gap-2 sm:hidden"><SignalMark small /><span className="font-semibold">RMAO</span></div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-[11px] text-muted-foreground md:flex"><span className="size-1.5 animate-signal rounded-full bg-secondary" />All systems nominal</div>
            <div className="flex size-8 items-center justify-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground" title="Local operator" data-testid="avatar-local-operator">LO</div>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}

function Home() {
  const [request, setRequest] = useState('');
  const [mode, setMode] = useState<Mode>('mock');
  const [taskCount, setTaskCount] = useState(6);
  const [runs, setRuns] = useState<Run[]>([sampleRun, partialRun]);
  const [selectedId, setSelectedId] = useState(sampleRun.id);
  const [filter, setFilter] = useState<'all' | TaskStatus>('all');
  const [showPlan, setShowPlan] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [notice, setNotice] = useState<{ type: 'info' | 'error'; text: string } | null>(null);

  const selectedRun = runs.find((run) => run.id === selectedId) ?? runs[0];
  const filteredTasks = useMemo(() => selectedRun?.tasks.filter((task) => filter === 'all' || task.status === filter) ?? [], [selectedRun, filter]);
  const activeRun = runs.find((run) => run.status === 'running');
  const completedCount = selectedRun?.tasks.filter((task) => task.status === 'completed').length ?? 0;
  const failedCount = selectedRun?.tasks.filter((task) => task.status === 'failed').length ?? 0;

  useEffect(() => {
    if (!activeRun) return;
    const timer = window.setInterval(() => {
      setRuns((current) => current.map((run) => {
        if (run.id !== activeRun.id || run.status !== 'running') return run;
        const nextTasks = run.tasks.map((task) => ({ ...task }));
        const runningIndex = nextTasks.findIndex((task) => task.status === 'running');
        const queuedIndex = nextTasks.findIndex((task) => task.status === 'queued');
        const shouldFail = run.request.toLowerCase().includes('failure') || run.request.toLowerCase().includes('provider');
        if (runningIndex >= 0) {
          nextTasks[runningIndex].status = shouldFail && runningIndex === Math.floor(nextTasks.length / 2) ? 'failed' : 'completed';
          nextTasks[runningIndex].duration = `${9 + runningIndex * 2}.8s`;
          if (queuedIndex >= 0) nextTasks[queuedIndex].status = 'running';
        } else if (queuedIndex >= 0) {
          nextTasks[queuedIndex].status = 'running';
        }
        const completed = nextTasks.filter((task) => task.status === 'completed').length;
        const failed = nextTasks.filter((task) => task.status === 'failed').length;
        const allSettled = nextTasks.every((task) => task.status === 'completed' || task.status === 'failed');
        return {
          ...run,
          tasks: nextTasks,
          progress: allSettled ? 100 : Math.min(96, Math.round(((completed + (nextTasks.some((task) => task.status === 'running') ? 0.45 : 0)) / nextTasks.length) * 100)),
          status: allSettled ? (failed > 0 ? 'partial' : 'completed') : 'running',
          duration: allSettled ? '00m 42s' : 'in progress',
          warnings: shouldFail && failed > 0 ? ['One worker returned an incomplete result. Review the task log before handoff.'] : run.warnings,
          errors: shouldFail && failed > 0 ? ['Simulated provider fixture rejected the verification step.'] : run.errors,
        };
      }));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [activeRun]);

  const startRun = () => {
    if (!request.trim()) {
      setNotice({ type: 'error', text: 'Add a project request before starting the run.' });
      return;
    }
    setNotice(null);
    setIsStarting(true);
    window.setTimeout(() => {
      const id = `rmao-${String(Math.floor(Math.random() * 900) + 100)}`;
      const run: Run = {
        id,
        request: request.trim(),
        mode,
        status: 'running',
        startedAt: 'Just now',
        duration: 'in progress',
        progress: 0,
        tasks: Array.from({ length: taskCount }, (_, index) => makeTask(index)),
        warnings: mode === 'mock' ? ['Provider is simulated. No repository will be changed.'] : ['Dry-run mode: proposed writes are blocked.'],
        errors: [],
      };
      setRuns((current) => [run, ...current]);
      setSelectedId(id);
      setIsStarting(false);
      setNotice({ type: 'info', text: `${id} is live. Task progress will update as workers report back.` });
    }, 520);
  };

  const cancelRun = () => {
    if (!activeRun) return;
    setRuns((current) => current.map((run) => run.id === activeRun.id ? { ...run, status: 'cancelled', duration: '00m 06s', tasks: run.tasks.map((task) => task.status === 'completed' ? task : { ...task, status: 'cancelled' }) } : run));
    setNotice({ type: 'info', text: `${activeRun.id} cancelled safely. Completed outputs remain available for inspection.` });
  };

  const retryRun = () => {
    if (!selectedRun) return;
    setRequest(selectedRun.request);
    setMode(selectedRun.mode);
    setNotice({ type: 'info', text: 'Request restored to the composer. Review it, then start a fresh run.' });
    document.getElementById('new-run')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const resultFor = (run: Run): Result => ({
    summary: run.status === 'partial' ? 'Plan completed with one verification gap. The result is safe to review, not safe to merge.' : run.status === 'completed' ? 'A sanitized execution record was produced. No external repository was modified in this simulation.' : 'The run is still gathering worker outputs. Final result will appear after the plan settles.',
    repository: run.status === 'completed' || run.status === 'partial' ? 'local/simulated-project' : 'pending',
    pullRequests: run.status === 'completed' ? ['PR preview · Add quiet mode documentation'] : [],
    warnings: run.warnings,
    errors: run.errors,
  });
  const result = selectedRun ? resultFor(selectedRun) : null;

  return (
    <main className="paper-grid min-h-[calc(100dvh-76px)] px-4 py-7 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-[1440px]">
        <section className="animate-rise-in flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <div className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[.22em] text-primary"><span className="size-1.5 rounded-full bg-primary" />Operations console</div>
            <h1 className="max-w-3xl text-3xl font-semibold tracking-[-.055em] text-foreground sm:text-4xl">Turn an idea into a <span className="text-primary">safe run.</span></h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">Orchestrate a plan, watch every worker, and inspect what came back — without losing the plot.</p>
          </div>
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-card px-3 py-2 text-xs text-muted-foreground shadow-sm" data-testid="text-provider-notice"><ShieldCheck className="size-4 text-secondary-foreground" /><span>Local simulation</span><span className="size-1 rounded-full bg-secondary" /><span className="font-mono text-[10px]">no writes</span></div>
        </section>

        <section className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Run metrics">
          {[
            ['Runs today', String(runs.filter((run) => run.startedAt.includes('Today') || run.startedAt === 'Just now').length), Activity, 'hsl(var(--primary))'],
            ['Success rate', '86%', CheckCircle2, 'hsl(var(--chart-2))'],
            ['Tasks observed', String(runs.reduce((sum, run) => sum + run.tasks.length, 0)), Layers3, 'hsl(var(--chart-4))'],
            ['Trust mode', 'ENFORCED', ShieldCheck, 'hsl(var(--accent-foreground))'],
          ].map(([label, value, Icon, color], index) => (
            <div className="animate-rise-in rounded-2xl border border-border bg-card p-4 shadow-sm" style={{ animationDelay: `${index * 60}ms` }} key={label as string} data-testid={`metric-${String(label).toLowerCase().replaceAll(' ', '-')}`}>
              <div className="flex items-center justify-between"><span className="text-xs text-muted-foreground">{label as string}</span><Icon className="size-4" style={{ color: color as string }} /></div>
              <p className="mt-3 font-mono text-xl font-medium tracking-[-.04em] text-foreground">{value as string}</p>
            </div>
          ))}
        </section>

        {notice && <div className={`mt-5 flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${notice.type === 'error' ? 'border-destructive/30 bg-destructive/8 text-destructive' : 'border-primary/20 bg-primary/7 text-foreground'}`} role="status" data-testid={`status-notice-${notice.type}`}><Info className="mt-0.5 size-4 shrink-0" /><span className="flex-1">{notice.text}</span><button onClick={() => setNotice(null)} className="rounded p-0.5 opacity-60 hover:opacity-100" aria-label="Dismiss notice" data-testid="button-dismiss-notice"><X className="size-4" /></button></div>}

        <section id="new-run" className="mt-5 grid scroll-mt-24 gap-5 xl:grid-cols-[minmax(0,.86fr)_minmax(0,1.14fr)]">
          <div className="rounded-[22px] border border-border bg-card shadow-sm">
            <div className="flex items-start justify-between border-b border-border px-5 py-5 sm:px-6">
              <div><div className="flex items-center gap-2"><Sparkles className="size-4 text-primary" /><h2 className="font-semibold tracking-[-.025em]">Start a new run</h2></div><p className="mt-1.5 text-xs text-muted-foreground">Describe the outcome, not the implementation.</p></div>
              <span className="font-mono text-[10px] uppercase tracking-[.16em] text-muted-foreground">step 01 / 02</span>
            </div>
            <div className="space-y-5 p-5 sm:p-6">
              <div>
                <label htmlFor="request" className="mb-2 flex items-center justify-between text-xs font-semibold"><span>Project request</span><span className="font-mono font-normal text-muted-foreground">{request.length}/240</span></label>
                <textarea id="request" maxLength={240} value={request} onChange={(event) => setRequest(event.target.value)} placeholder="e.g. Add a status endpoint and document how operators can check it." className="min-h-[112px] w-full resize-none rounded-xl border border-input bg-background px-3.5 py-3 text-sm leading-relaxed outline-none transition-colors placeholder:text-muted-foreground/65 focus:border-primary focus:ring-2 focus:ring-primary/15" data-testid="input-project-request" />
              </div>
              <div className="grid gap-4 sm:grid-cols-[1.2fr_.8fr]">
                <div>
                  <p className="mb-2 text-xs font-semibold">Execution mode</p>
                  <div className="grid grid-cols-2 gap-2 rounded-xl bg-muted p-1">
                    {(['mock', 'dry-run'] as Mode[]).map((item) => <button key={item} onClick={() => setMode(item)} className={`rounded-lg px-3 py-2 text-left text-xs font-semibold transition-colors ${mode === item ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`} data-testid={`button-mode-${item}`}><span className="flex items-center gap-2">{item === 'mock' ? <Terminal className="size-3.5" /> : <ShieldCheck className="size-3.5" />}{item === 'mock' ? 'Mock provider' : 'Dry-run'}</span><span className="mt-1 block text-[10px] font-normal text-muted-foreground">{item === 'mock' ? 'fast, no writes' : 'plan + checks only'}</span></button>)}
                  </div>
                </div>
                <div>
                  <label htmlFor="task-count" className="mb-2 block text-xs font-semibold">Task budget</label>
                  <div className="relative"><select id="task-count" value={taskCount} onChange={(event) => setTaskCount(Number(event.target.value))} className="w-full appearance-none rounded-xl border border-input bg-background px-3.5 py-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" data-testid="select-task-count">{[4, 5, 6, 7, 8].map((count) => <option value={count} key={count}>{count} tasks</option>)}</select><ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4 text-muted-foreground" /></div>
                  <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">More tasks add coverage, not access.</p>
                </div>
              </div>
              <div className="flex flex-col gap-3 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="size-4 text-secondary-foreground" />Sanitizer is always on</div>
                <button onClick={startRun} disabled={isStarting || Boolean(activeRun)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60" data-testid="button-start-run">{isStarting ? <><span className="size-3.5 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />Preparing plan</> : <><Play className="size-4" fill="currentColor" />Start safe run<ArrowRight className="size-4" /></>}</button>
              </div>
            </div>
          </div>

          <div className="rounded-[22px] border border-border bg-card shadow-sm" data-testid="panel-active-run">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-5 sm:px-6">
              <div><div className="flex items-center gap-2"><Workflow className="size-4 text-primary" /><h2 className="font-semibold tracking-[-.025em]">{activeRun ? 'Live run' : 'Selected run'}</h2>{activeRun && <span className="size-2 animate-signal rounded-full bg-primary" />}</div><p className="mt-1.5 max-w-md truncate text-xs text-muted-foreground">{selectedRun?.request}</p></div>
              {selectedRun && <div className="flex items-center gap-2"><StatusPill status={selectedRun.status} /><button className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground" aria-label="Run actions" data-testid="button-run-actions"><MoreHorizontal className="size-4" /></button></div>}
            </div>
            {isStarting ? <div className="space-y-4 p-6"><div className="h-4 w-2/5 animate-pulse rounded bg-muted" /><div className="h-3 w-4/5 animate-pulse rounded bg-muted" /><div className="h-24 animate-pulse rounded-xl bg-muted" /></div> : selectedRun ? <div className="p-5 sm:p-6">
              <div className="flex items-end justify-between"><div><p className="font-mono text-3xl tracking-[-.07em] text-foreground">{selectedRun.progress}<span className="text-lg text-muted-foreground">%</span></p><p className="mt-1 text-xs text-muted-foreground">plan progress</p></div><div className="text-right font-mono text-[10px] text-muted-foreground"><p>{selectedRun.id}</p><p className="mt-1">{selectedRun.duration}</p></div></div>
              <div className="mt-5 h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full transition-[width] duration-700 ${selectedRun.status === 'running' ? 'progress-active' : selectedRun.status === 'partial' ? 'bg-accent' : selectedRun.status === 'failed' ? 'bg-destructive' : 'bg-secondary'}`} style={{ width: `${selectedRun.progress}%` }} /></div>
              <div className="mt-5 grid grid-cols-3 divide-x divide-border rounded-xl border border-border bg-background/60 py-3"><div className="px-3 text-center"><p className="font-mono text-sm">{completedCount}</p><p className="mt-1 text-[10px] text-muted-foreground">completed</p></div><div className="px-3 text-center"><p className="font-mono text-sm">{selectedRun.tasks.filter((task) => task.status === 'running').length}</p><p className="mt-1 text-[10px] text-muted-foreground">active</p></div><div className="px-3 text-center"><p className="font-mono text-sm text-destructive">{failedCount}</p><p className="mt-1 text-[10px] text-muted-foreground">attention</p></div></div>
              {activeRun ? <div className="mt-5 flex gap-2"><button onClick={cancelRun} className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-destructive/30 bg-destructive/8 px-3 py-2.5 text-xs font-semibold text-destructive hover:bg-destructive/12" data-testid="button-cancel-run"><StopCircle className="size-4" />Cancel active run</button><button onClick={() => setShowPlan(true)} className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-3 py-2.5 text-xs font-semibold hover:bg-muted" data-testid="button-inspect-plan-active"><Search className="size-4" />Inspect plan</button></div> : <div className="mt-5 flex gap-2"><button onClick={() => setShowPlan(true)} className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-foreground px-3 py-2.5 text-xs font-semibold text-background hover:opacity-90" data-testid="button-inspect-plan"><Search className="size-4" />Inspect plan</button>{selectedRun.status === 'partial' || selectedRun.status === 'failed' || selectedRun.status === 'cancelled' ? <button onClick={retryRun} className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-3 py-2.5 text-xs font-semibold hover:bg-muted" data-testid="button-retry-run"><RotateCcw className="size-4" />Retry</button> : null}</div>}
            </div> : <div className="flex min-h-[300px] flex-col items-center justify-center p-8 text-center"><div className="mb-4 rounded-2xl bg-muted p-4"><Workflow className="size-7 text-muted-foreground" /></div><p className="font-semibold">No run selected</p><p className="mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">Start with a small request and this panel will become your live control surface.</p></div>}
          </div>
        </section>

        {selectedRun && <section className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.24fr)_minmax(310px,.76fr)]">
          <div className="rounded-[22px] border border-border bg-card shadow-sm" data-testid="panel-task-stream">
            <div className="flex flex-col gap-4 border-b border-border px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div><div className="flex items-center gap-2"><Layers3 className="size-4 text-primary" /><h2 className="font-semibold tracking-[-.025em]">Task stream</h2><span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-foreground">{selectedRun.tasks.length}</span></div><p className="mt-1.5 text-xs text-muted-foreground">Worker outputs, sanitized before they land here.</p></div>
              <div className="flex items-center gap-1 overflow-x-auto rounded-lg bg-muted p-1"><button onClick={() => setFilter('all')} className={`shrink-0 rounded-md px-2.5 py-1.5 text-[11px] font-semibold ${filter === 'all' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`} data-testid="button-filter-all">All</button>{(['running', 'completed', 'failed', 'queued'] as TaskStatus[]).map((status) => <button key={status} onClick={() => setFilter(status)} className={`shrink-0 rounded-md px-2.5 py-1.5 text-[11px] font-semibold capitalize ${filter === status ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`} data-testid={`button-filter-${status}`}>{status}</button>)}</div>
            </div>
            <div>{filteredTasks.length ? filteredTasks.map((task, index) => <TaskRow task={task} index={index} key={task.id} />) : <div className="flex min-h-[190px] flex-col items-center justify-center p-8 text-center"><Search className="size-6 text-muted-foreground" /><p className="mt-3 text-sm font-semibold">No {filter} tasks</p><p className="mt-1 text-xs text-muted-foreground">Try another status filter while the plan moves.</p><button onClick={() => setFilter('all')} className="mt-4 text-xs font-semibold text-primary hover:underline" data-testid="button-clear-task-filter">Show all tasks</button></div>}</div>
          </div>
          <div className="rounded-[22px] border border-border bg-card shadow-sm" data-testid="panel-final-result">
            <div className="border-b border-border px-5 py-5 sm:px-6"><div className="flex items-center gap-2"><Code2 className="size-4 text-primary" /><h2 className="font-semibold tracking-[-.025em]">Sanitized result</h2></div><p className="mt-1.5 text-xs text-muted-foreground">A safe handoff, not a raw worker transcript.</p></div>
            {result && (selectedRun.status === 'completed' || selectedRun.status === 'partial') ? <div className="space-y-5 p-5 sm:p-6"><div className={`rounded-xl border p-4 ${selectedRun.status === 'partial' ? 'border-accent/50 bg-accent/12' : 'border-secondary/60 bg-secondary/15'}`}><div className="flex items-start gap-3"><div className={`mt-0.5 rounded-full p-1 ${selectedRun.status === 'partial' ? 'bg-accent text-accent-foreground' : 'bg-secondary text-secondary-foreground'}`}>{selectedRun.status === 'partial' ? <AlertTriangle className="size-3.5" /> : <Check className="size-3.5" />}</div><p className="text-xs leading-relaxed text-foreground">{result.summary}</p></div></div><div><p className="mb-2 text-[10px] font-semibold uppercase tracking-[.15em] text-muted-foreground">Repository</p><div className="flex items-center justify-between rounded-xl border border-border bg-background px-3 py-2.5"><span className="font-mono text-xs">{result.repository}</span><button onClick={() => { void navigator.clipboard?.writeText(result.repository); setNotice({ type: 'info', text: 'Repository path copied.' }); }} className="text-muted-foreground hover:text-foreground" aria-label="Copy repository path" data-testid="button-copy-repository"><Copy className="size-3.5" /></button></div></div>{result.pullRequests.length > 0 && <div><p className="mb-2 text-[10px] font-semibold uppercase tracking-[.15em] text-muted-foreground">Pull request previews</p>{result.pullRequests.map((pullRequest) => <div className="flex items-center gap-2 rounded-xl border border-border px-3 py-2.5 text-xs" key={pullRequest}><GitPullRequest className="size-3.5 text-secondary-foreground" />{pullRequest}<ExternalLink className="ml-auto size-3 text-muted-foreground" /></div>)}</div>}{result.warnings.length > 0 && <div className="space-y-2">{result.warnings.map((warning) => <div className="flex gap-2 text-[11px] leading-relaxed text-muted-foreground" key={warning}><AlertTriangle className="mt-0.5 size-3 shrink-0 text-accent-foreground" />{warning}</div>)}</div>}{result.errors.length > 0 && <div className="space-y-2 border-t border-border pt-4">{result.errors.map((error) => <div className="flex gap-2 text-[11px] leading-relaxed text-destructive" key={error}><AlertTriangle className="mt-0.5 size-3 shrink-0" />{error}</div>)}</div>}</div> : <div className="flex min-h-[292px] flex-col items-center justify-center p-8 text-center"><div className="mb-4 rounded-2xl bg-muted p-4"><FileCode2 className="size-6 text-muted-foreground" /></div><p className="text-sm font-semibold">Result is still sealed</p><p className="mt-1 max-w-[230px] text-xs leading-relaxed text-muted-foreground">We will show only sanitized outputs once every worker has settled.</p><div className="mt-4 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[.14em] text-muted-foreground"><span className="size-1.5 animate-signal rounded-full bg-primary" />observing</div></div>}
          </div>
        </section>}

        <section id="run-history" className="mt-5 scroll-mt-24 rounded-[22px] border border-border bg-card shadow-sm">
          <div className="flex flex-col gap-3 border-b border-border px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div><div className="flex items-center gap-2"><Clock3 className="size-4 text-primary" /><h2 className="font-semibold tracking-[-.025em]">Recent runs</h2></div><p className="mt-1.5 text-xs text-muted-foreground">A short memory of what the control room has seen.</p></div><div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground"><span>{runs.length} records</span><button className="rounded-lg border border-border p-1.5 hover:bg-muted" aria-label="Search run history" data-testid="button-search-history"><Search className="size-3.5" /></button></div></div>
          <div className="divide-y divide-border">{runs.map((run) => <button onClick={() => { setSelectedId(run.id); setFilter('all'); }} className={`grid w-full grid-cols-[1fr_auto] gap-3 px-5 py-4 text-left transition-colors hover:bg-muted/50 sm:grid-cols-[1.1fr_.65fr_.45fr_auto] sm:items-center sm:px-6 ${run.id === selectedId ? 'bg-primary/[.035]' : ''}`} key={run.id} data-testid={`button-select-run-${run.id}`}><div className="min-w-0"><div className="flex items-center gap-2"><span className="font-mono text-[10px] text-muted-foreground">{run.id}</span>{run.mode === 'mock' && <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-muted-foreground">mock</span>}</div><p className="mt-1 truncate text-sm font-medium">{run.request}</p></div><span className="hidden text-xs text-muted-foreground sm:block">{run.startedAt}</span><span className="hidden font-mono text-xs text-muted-foreground sm:block">{run.duration}</span><StatusPill status={run.status} /></button>)}</div>
        </section>

        <section id="system-health" className="mt-5 mb-10 grid scroll-mt-24 gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-border bg-card p-4"><div className="flex items-center gap-2 text-xs font-semibold"><span className="size-2 rounded-full bg-secondary" />Orchestrator</div><p className="mt-2 text-[11px] text-muted-foreground">Plan sequencing responding normally.</p></div>
          <div className="rounded-2xl border border-border bg-card p-4"><div className="flex items-center gap-2 text-xs font-semibold"><span className="size-2 rounded-full bg-secondary" />Sanitizer</div><p className="mt-2 text-[11px] text-muted-foreground">Output boundary checks enforced.</p></div>
          <div className="rounded-2xl border border-border bg-card p-4"><div className="flex items-center gap-2 text-xs font-semibold"><span className="size-2 rounded-full bg-secondary" />Worker pool</div><p className="mt-2 text-[11px] text-muted-foreground">4 simulated workers available.</p></div>
        </section>
      </div>

      {showPlan && selectedRun && <div className="fixed inset-0 z-50 flex items-end justify-center bg-sidebar/35 p-0 backdrop-blur-sm sm:items-center sm:p-6" role="dialog" aria-modal="true" aria-label="Execution plan" data-testid="dialog-execution-plan"><div className="max-h-[88dvh] w-full max-w-2xl overflow-auto rounded-t-[26px] border border-border bg-card shadow-2xl sm:rounded-[26px]"><div className="sticky top-0 flex items-start justify-between border-b border-border bg-card/95 px-5 py-5 backdrop-blur sm:px-6"><div><div className="flex items-center gap-2"><Workflow className="size-4 text-primary" /><h2 className="font-semibold">Execution plan</h2></div><p className="mt-1 text-xs text-muted-foreground">{selectedRun.id} · dependency-aware task sequence</p></div><button onClick={() => setShowPlan(false)} className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Close execution plan" data-testid="button-close-plan"><X className="size-4" /></button></div><div className="p-5 sm:p-6"><div className="mb-5 rounded-xl border border-primary/20 bg-primary/7 p-4 text-xs leading-relaxed text-muted-foreground"><span className="font-semibold text-foreground">Plan boundary:</span> workers can propose files and checks in this simulation. Nothing is written to a repository or sent to a provider.</div><div className="space-y-2">{selectedRun.tasks.map((task, index) => <div className="flex items-center gap-3 rounded-xl border border-border bg-background/50 px-3 py-3" key={task.id}><span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted font-mono text-[10px] text-muted-foreground">{String(index + 1).padStart(2, '0')}</span><div className="min-w-0 flex-1"><p className="text-xs font-semibold">{task.name}</p><p className="mt-1 font-mono text-[10px] text-muted-foreground">{task.dependencies.length ? `after ${task.dependencies.join(', ')}` : 'no dependencies'}</p></div><StatusPill status={task.status} /></div>)}</div></div></div></div>}
    </main>
  );
}

function Router() {
  return (
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/" component={() => <AppShell><Home /></AppShell>} />
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
