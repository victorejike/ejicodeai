'use client';

import { Check, Loader2, X } from 'lucide-react';
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
      case 'pipeline.completed':
        finished = true;
        for (const stage of stages) {
          if (stage.state === 'running') stage.state = 'done';
        }
        break;
      default:
        break;
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
    finished,
    started,
  };
}

const DOT_STATE: Record<StageState, string> = {
  pending: 'border-[var(--border)] text-[var(--text-muted)]',
  running: 'border-[var(--accent)] text-[var(--accent)] bg-[var(--accent-light)]',
  done: 'border-[var(--green)] text-[var(--green)]',
  failed: 'border-[var(--red)] text-[var(--red)] bg-[var(--accent-light)]',
};

function summarise(counts: Record<string, number>): string | null {
  const entries = Object.entries(counts).filter(([, v]) => typeof v === 'number' && v > 0);
  if (entries.length === 0) return null;
  return entries
    .slice(0, 3)
    .map(([k, v]) => `${v} ${k.replace(/_/g, ' ')}`)
    .join(', ');
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

  return (
    <div className={cx('space-y-3', className)}>
      <div className="flex items-center justify-between gap-3 text-[11px]">
        <span className="font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Agent hand-off chain
        </span>
        <span className="tabular-nums text-[var(--text-muted)]">
          {snapshot.completedCount}/{snapshot.stages.length} stages
          {snapshot.finished ? ' · complete' : snapshot.started ? ' · running' : ' · idle'}
        </span>
      </div>

      <ol className="flex items-stretch gap-1 overflow-x-auto pb-1">
        {snapshot.stages.map((stage, i) => {
          const handed = summarise(stage.produced);
          return (
            <li key={stage.stage} className="flex min-w-0 flex-1 items-center gap-1">
              <div className="flex min-w-[92px] flex-col items-center gap-1.5 text-center">
                <span
                  className={cx(
                    'flex h-6 w-6 items-center justify-center rounded-full border text-[10px] font-bold transition-colors',
                    DOT_STATE[stage.state]
                  )}
                  title={`${stage.label} — ${stage.state}`}
                >
                  {stage.state === 'done' ? (
                    <Check size={12} />
                  ) : stage.state === 'failed' ? (
                    <X size={12} />
                  ) : stage.state === 'running' ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    i + 1
                  )}
                </span>
                <span
                  className={cx(
                    'text-[10px] leading-tight',
                    stage.state === 'pending'
                      ? 'text-[var(--text-muted)]'
                      : 'text-[var(--text)]'
                  )}
                >
                  {stage.label}
                </span>
                {handed && (
                  <span className="text-[9px] text-[var(--text-muted)]" title="Handed to the next agent">
                    → {handed}
                  </span>
                )}
              </div>
              {i < snapshot.stages.length - 1 && (
                <span
                  aria-hidden
                  className={cx(
                    'mb-6 h-px flex-1 min-w-[8px]',
                    stage.state === 'done' ? 'bg-[var(--green)]' : 'bg-[var(--border)]'
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>

      {snapshot.blockedReason && (
        <p className="text-[11px] text-[var(--yellow)]">{snapshot.blockedReason}</p>
      )}
      {snapshot.failed && (
        <p className="text-[11px] text-[var(--red)]">{snapshot.failed.message}</p>
      )}
    </div>
  );
}
