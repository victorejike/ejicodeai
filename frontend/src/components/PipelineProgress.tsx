'use client';

import { useRef } from 'react';
import { AlertCircle, Check, ChevronLeft, ChevronRight, Loader2, X } from 'lucide-react';
import { cx } from './ui/cx';
import type { AgentEvent } from './AgentEventFeed';

export interface PipelineStage {
  stage: string;
  index: number;
  label: string;
}

export type StageState = 'pending' | 'running' | 'done' | 'failed';

export interface StageProgress extends PipelineStage {
  state: StageState;
  /** List lengths the stage produced, e.g. `{opportunities: 24}`. */
  produced: Record<string, number>;
  /** List lengths it received from the stage before it. */
  received: Record<string, number>;
  effects: Record<string, unknown>;
}

export interface PipelineSnapshot {
  stages: StageProgress[];
  executionId: string | null;
  activeIndex: number;
  completedCount: number;
  percent: number;
  failed: { stage: string; message: string } | null;
  blockedReason: string | null;
  finished: boolean;
  started: boolean;
}

/**
 * Fold the `pipeline.*` events into a per-stage picture.
 *
 * The events are the source of truth here rather than a polled status endpoint:
 * they are what arrives while the run is happening, and each one carries the
 * counts in and out that prove the previous stage handed its work forward.
 */
export function readPipeline(
  declared: PipelineStage[],
  events: AgentEvent[]
): PipelineSnapshot {
  const stages: StageProgress[] = declared.map((s) => ({
    ...s,
    state: 'pending',
    produced: {},
    received: {},
    effects: {},
  }));
  const byName = new Map(stages.map((s) => [s.stage, s]));

  let executionId: string | null = null;
  let failed: PipelineSnapshot['failed'] = null;
  let blockedReason: string | null = null;
  let finished = false;
  let started = false;

  for (const event of events) {
    const p = (event.payload ?? {}) as Record<string, any>;
    if (p.execution_id) executionId = String(p.execution_id);

    switch (event.event_type) {
      case 'pipeline.started':
        started = true;
        failed = null;
        blockedReason = null;
        finished = false;
        // A fresh run supersedes whatever the previous one left on the strip.
        for (const stage of stages) {
          stage.state = 'pending';
          stage.produced = {};
          stage.received = {};
          stage.effects = {};
        }
        break;
      case 'pipeline.blocked':
        blockedReason = event.message;
        break;
      case 'pipeline.stage_started': {
        started = true;
        const stage = byName.get(p.stage);
        if (stage) {
          stage.state = 'running';
          stage.received = p.received ?? {};
        }
        break;
      }
      case 'pipeline.stage_completed': {
        const stage = byName.get(p.stage);
        if (stage) {
          stage.state = 'done';
          stage.produced = p.produced ?? {};
          stage.effects = p.effects ?? {};
        }
        break;
      }
      case 'pipeline.stage_failed': {
        const stage = byName.get(p.stage);
        if (stage) stage.state = 'failed';
        failed = { stage: String(p.stage ?? ''), message: event.message };
        break;
      }
      case 'pipeline.completed': {
        finished = true;
        const finishedStages = Array.isArray(p.stages) ? new Set(p.stages) : null;
        for (const stage of stages) {
          if (finishedStages) {
            if (finishedStages.has(stage.stage)) stage.state = 'done';
          } else if (stage.state !== 'failed') {
            stage.state = 'done';
          }
        }
        break;
      }
      default:
        break;
    }
  }

  // Linear pipeline inference: In a sequential pipeline, if stage K is running or done,
  // all prior stages 0..K-1 that were pending must have succeeded earlier in the run
  // (their start/complete events may have slid past the recent event buffer).
  let latestActiveIndex = -1;
  for (let i = stages.length - 1; i >= 0; i--) {
    if (stages[i].state === 'done' || stages[i].state === 'running') {
      latestActiveIndex = i;
      break;
    }
  }

  if (latestActiveIndex > 0 && !failed) {
    for (let i = 0; i < latestActiveIndex; i++) {
      if (stages[i].state === 'pending') {
        stages[i].state = 'done';
      }
    }
  }

  const completedCount = stages.filter((s) => s.state === 'done').length;
  const running = stages.findIndex((s) => s.state === 'running');
  const activeIndex = running >= 0 ? running : Math.min(completedCount, stages.length - 1);

  return {
    stages,
    executionId,
    activeIndex,
    completedCount,
    percent: stages.length ? Math.round((100 * completedCount) / stages.length) : 0,
    failed,
    blockedReason,
    finished: finished || (stages.length > 0 && completedCount === stages.length),
    started: started || completedCount > 0,
  };
}

const DOT_STATE: Record<StageState, string> = {
  pending: 'border-white/10 text-zinc-500 bg-zinc-900/80',
  running: 'border-blue-400 text-blue-400 bg-blue-500/10 shadow-[0_0_12px_rgba(59,130,246,0.3)] ring-2 ring-blue-500/20',
  done: 'border-emerald-500/60 text-emerald-400 bg-emerald-500/10 shadow-[0_0_8px_rgba(16,185,129,0.15)]',
  failed: 'border-red-500/60 text-red-400 bg-red-500/10 shadow-[0_0_8px_rgba(239,68,68,0.15)]',
};

function summarise(counts: Record<string, number>): { short: string; full: string } | null {
  const entries = Object.entries(counts).filter(([, v]) => typeof v === 'number' && v > 0);
  if (entries.length === 0) return null;

  const full = entries.map(([k, v]) => `${v} ${k.replace(/_/g, ' ')}`).join(', ');

  const formatKey = (k: string, v: number) => {
    const clean = k.replace(/_/g, ' ');
    if (clean === 'opportunities') return `${v} opps`;
    if (clean === 'domains searched') return `${v} domains`;
    if (clean === 'cvs saved') return `${v} CVs`;
    return `${v} ${clean}`;
  };

  const short =
    entries.length > 1
      ? `${formatKey(entries[0][0], entries[0][1])} (+${entries.length - 1})`
      : formatKey(entries[0][0], entries[0][1]);

  return { short, full };
}

/**
 * The ordered stage strip: which agent is working, which have handed off, and
 * how much data each one passed to the next.
 */
export default function PipelineProgress({
  stages,
  events,
  className,
}: {
  stages: PipelineStage[];
  events: AgentEvent[];
  className?: string;
}) {
  if (stages.length === 0) return null;
  const snapshot = readPipeline(stages, events);
  const olRef = useRef<HTMLOListElement>(null);

  const scrollLeft = () => {
    olRef.current?.scrollBy({ left: -260, behavior: 'smooth' });
  };

  const scrollRight = () => {
    olRef.current?.scrollBy({ left: 260, behavior: 'smooth' });
  };

  return (
    <div className={cx('space-y-3.5', className)}>
      {/* Header bar with stage count, status badge & metrics */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-[11px]">
        <div className="flex items-center gap-2">
          <span className="font-semibold uppercase tracking-wider text-zinc-400 font-mono text-[10px]">
            Agent Hand-Off Chain
          </span>
          <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-zinc-400 border border-white/10 font-mono">
            {snapshot.stages.length} Stages
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Scroll navigation arrows */}
          <div className="flex items-center gap-1 mr-1">
            <button
              type="button"
              onClick={scrollLeft}
              className="flex h-5 w-5 items-center justify-center rounded border border-white/10 bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white transition-colors"
              title="Scroll left"
            >
              <ChevronLeft size={12} />
            </button>
            <button
              type="button"
              onClick={scrollRight}
              className="flex h-5 w-5 items-center justify-center rounded border border-white/10 bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white transition-colors"
              title="Scroll right"
            >
              <ChevronRight size={12} />
            </button>
          </div>

          <span className="tabular-nums font-mono text-zinc-400 text-[11px]">
            {snapshot.completedCount}/{snapshot.stages.length} Completed
          </span>
          <span
            className={cx(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium border transition-colors',
              snapshot.finished
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                : snapshot.started
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/25'
                : 'bg-white/5 text-zinc-400 border-white/10'
            )}
          >
            <span
              className={cx(
                'h-1.5 w-1.5 rounded-full',
                snapshot.finished
                  ? 'bg-emerald-400'
                  : snapshot.started
                  ? 'bg-blue-400 animate-ping'
                  : 'bg-zinc-500'
              )}
            />
            {snapshot.finished ? 'Complete' : snapshot.started ? 'Running' : 'Idle'}
          </span>
        </div>
      </div>

      {/* Thin progress track */}
      <div className="h-1 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-400 transition-all duration-500 ease-out"
          style={{ width: `${snapshot.percent}%` }}
        />
      </div>

      {/* Stepper with horizontally aligned circles, connectors & labels */}
      <div className="relative">
        <ol
          ref={olRef}
          className="flex items-start overflow-x-auto pb-2 pt-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent scroll-smooth"
        >
          {snapshot.stages.map((stage, i) => {
            const summary = summarise(stage.produced);
            return (
              <li
                key={stage.stage}
                className="relative flex min-w-[110px] sm:min-w-[124px] flex-1 shrink-0 flex-col items-center group px-1"
              >
                {/* Connector line row with centered circle node */}
                <div className="relative flex w-full items-center justify-center">
                  {/* Left connector half */}
                  {i > 0 && (
                    <div
                      aria-hidden
                      className={cx(
                        'absolute top-1/2 right-1/2 h-[2px] w-1/2 -translate-y-1/2 transition-colors duration-300',
                        stage.state === 'done' || stage.state === 'running'
                          ? 'bg-emerald-500/70'
                          : 'bg-white/10'
                      )}
                    />
                  )}
                  {/* Right connector half */}
                  {i < snapshot.stages.length - 1 && (
                    <div
                      aria-hidden
                      className={cx(
                        'absolute top-1/2 left-1/2 h-[2px] w-1/2 -translate-y-1/2 transition-colors duration-300',
                        stage.state === 'done'
                          ? 'bg-emerald-500/70'
                          : 'bg-white/10'
                      )}
                    />
                  )}

                  {/* Circle Indicator */}
                  <span
                    className={cx(
                      'relative z-10 flex h-7 w-7 items-center justify-center rounded-full border text-[10px] font-bold transition-all shadow-sm',
                      DOT_STATE[stage.state]
                    )}
                    title={`${stage.label} — ${stage.state}`}
                  >
                    {stage.state === 'done' ? (
                      <Check size={13} className="stroke-[2.5]" />
                    ) : stage.state === 'failed' ? (
                      <X size={13} className="stroke-[2.5]" />
                    ) : stage.state === 'running' ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      i + 1
                    )}
                  </span>
                </div>

                {/* Stage Title and Hand-off output badge */}
                <div className="mt-2.5 flex w-full flex-col items-center gap-1 text-center">
                  <span
                    className={cx(
                      'text-[10px] font-medium leading-tight h-7 flex items-center justify-center line-clamp-2 px-1 text-center break-words',
                      stage.state === 'done'
                        ? 'text-zinc-200'
                        : stage.state === 'running'
                        ? 'text-blue-400 font-semibold'
                        : 'text-zinc-400'
                    )}
                    title={stage.label}
                  >
                    {stage.label}
                  </span>

                  {summary ? (
                    <span
                      className="inline-flex max-w-full items-center truncate rounded-full border border-emerald-500/25 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-300 cursor-help"
                      title={`Handed to next agent: ${summary.full}`}
                    >
                      → {summary.short}
                    </span>
                  ) : (
                    <span className="h-4" />
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      {snapshot.blockedReason && (
        <div className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-300 flex items-center gap-2">
          <AlertCircle size={14} className="shrink-0 text-amber-400" />
          <span>{snapshot.blockedReason}</span>
        </div>
      )}
      {snapshot.failed && (
        <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-2 text-[11px] text-red-300 flex items-center gap-2">
          <AlertCircle size={14} className="shrink-0 text-red-400" />
          <span>{snapshot.failed.message}</span>
        </div>
      )}
    </div>
  );
}
