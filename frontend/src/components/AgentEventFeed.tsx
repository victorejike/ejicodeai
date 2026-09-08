'use client';

import { useState, useEffect, useRef } from 'react';
import {
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Radio,
  Sparkles,
  Terminal,
} from 'lucide-react';
import PipelineProgress, { PipelineStage } from './PipelineProgress';
import { cx } from './ui/cx';

export interface AgentEvent {
  id: string;
  event_type: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  message: string;
  payload?: any;
  timestamp: string;
}

const MAX_EVENTS = 60;

export default function AgentEventFeed({
  orgId,
  title = 'Autonomous AI Agent Activity',
  /** Declared pipeline stages; pass them to show the ordered hand-off strip. */
  stages,
  /** Notified whenever the buffered event list changes. */
  onEvents,
  className,
}: {
  /** Accepted for call-site compatibility; the stream is scoped by the token. */
  userId?: string;
  orgId?: string;
  title?: string;
  stages?: PipelineStage[];
  onEvents?: (events: AgentEvent[]) => void;
  className?: string;
}) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const onEventsRef = useRef(onEvents);
  onEventsRef.current = onEvents;

  useEffect(() => {
    // EventSource cannot set an Authorization header, so the token travels as a
    // query param and the proxy route turns it back into a header. Without it the
    // backend has no way to know whose run to stream.
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const params = new URLSearchParams();
    if (token) params.set('access_token', token);
    if (orgId) params.set('organization_id', orgId);

    let es: EventSource | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let closed = false;
    let attempt = 0;

    const connect = () => {
      if (closed) return;
      try {
        es = new EventSource(`/api/events/stream?${params.toString()}`);
        eventSourceRef.current = es;

        es.onopen = () => {
          attempt = 0;
          setIsConnected(true);
        };

        es.onmessage = (e) => {
          try {
            const parsed = JSON.parse(e.data);
            if (!parsed?.message) return;
            setEvents((prev) => {
              if (parsed.id && prev.some((item) => item.id === parsed.id)) return prev;
              return [...prev, parsed].slice(-MAX_EVENTS);
            });
          } catch {
            // keepalive frame or malformed payload - nothing to show
          }
        };

        es.onerror = () => {
          setIsConnected(false);
          es?.close();
          if (closed) return;
          // Back off instead of hammering a backend that is restarting.
          attempt += 1;
          const delay = Math.min(1000 * 2 ** (attempt - 1), 30000);
          retry = setTimeout(connect, delay);
        };
      } catch (err) {
        console.warn('Could not initialize EventSource:', err);
      }
    };

    connect();

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      eventSourceRef.current?.close();
    };
  }, [orgId]);

  useEffect(() => {
    onEventsRef.current?.(events);
  }, [events]);

  useEffect(() => {
    if (isExpanded && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [events, isExpanded]);

  const badgeStyle = (type: string, severity: string) => {
    if (severity === 'error') return 'border-[var(--border-red)] text-[var(--red)] bg-[var(--accent-light)]';
    if (severity === 'warning') return 'border-[var(--border)] text-[var(--yellow)]';
    if (severity === 'success') return 'border-[var(--border)] text-[var(--green)]';
    if (type.startsWith('pipeline.')) return 'border-[var(--border)] text-[var(--purple)]';
    if (type.startsWith('cv.')) return 'border-[var(--border)] text-[var(--purple)]';
    if (type.startsWith('agent.')) return 'border-[var(--border)] text-[var(--blue)]';
    return 'border-[var(--border)] text-[var(--text-muted)]';
  };

  // Labels for what the user is actually watching happen. Anything unmapped
  // falls back to the raw event type rather than a made-up name.
  const LABELS: Record<string, string> = {
    'pipeline.started': 'Pipeline start',
    'pipeline.stage_started': 'Stage start',
    'pipeline.stage_completed': 'Stage done',
    'pipeline.stage_failed': 'Stage failed',
    'pipeline.completed': 'Pipeline done',
    'pipeline.blocked': 'Blocked',
    'agent.started': 'Agent start',
    'agent.progress': 'Progress',
    'agent.completed': 'Agent done',
    'agent.failed': 'Agent failed',
    'cv.built': 'ATS CV built',
    'cv.uploaded': 'CV ingestion',
    'cv.extracted': 'CV parsed',
    'opportunities.matched': '6-factor match',
    'system.connected': 'Connected',
  };

  const formatEventType = (type: string) =>
    LABELS[type] ?? type.replace(/[._]/g, ' ').toUpperCase();

  const renderPayload = (payload: any) => {
    if (!payload || typeof payload !== 'object') return null;
    const entries = Object.entries(payload).filter(([, v]) => {
      if (v === null || v === undefined || v === '') return false;
      if (Array.isArray(v)) return v.length > 0;
      if (typeof v === 'object') return Object.keys(v as object).length > 0;
      return true;
    });
    if (entries.length === 0) return null;

    return (
      <div className="flex flex-wrap items-center gap-1.5 pt-0.5 text-[10px]">
        {entries.slice(0, 8).map(([k, v]) => (
          <span
            key={k}
            className="rounded border border-[var(--border)] bg-[var(--glass-subtle-bg)] px-1.5 py-0.5"
          >
            <span className="text-[var(--text-muted)]">{k.replace(/_/g, ' ')}:</span>{' '}
            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div
      className={cx(
        'overflow-hidden rounded-2xl apple-glass-subtle transition-all',
        className
      )}
    >
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex cursor-pointer items-center justify-between border-b border-[var(--border)] px-4 py-3 transition-colors hover:bg-[var(--glass-hover-bg)]"
      >
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span
              className={cx(
                'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
                isConnected ? 'bg-[var(--green)]' : 'bg-[var(--yellow)]'
              )}
            />
            <span
              className={cx(
                'relative inline-flex h-2 w-2 rounded-full',
                isConnected ? 'bg-[var(--green)]' : 'bg-[var(--yellow)]'
              )}
            />
          </span>
          <span className="flex items-center gap-2 text-xs font-semibold tracking-wide text-[var(--text)]">
            <Terminal className="h-3.5 w-3.5 text-[var(--accent)]" />
            {title}
          </span>
          <span className="rounded-full border border-[var(--border)] px-2 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
            {isConnected ? 'LIVE FEED' : 'RECONNECTING'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-[var(--text-muted)]">
            {events.length} {events.length === 1 ? 'event' : 'events'}
          </span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-[var(--text-muted)]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[var(--text-muted)]" />
          )}
        </div>
      </div>

      {stages && stages.length > 0 && (
        <div className="border-b border-[var(--border)] px-4 py-4">
          <PipelineProgress stages={stages} events={events} />
        </div>
      )}

      {isExpanded && (
        <div className="max-h-64 space-y-2 overflow-y-auto p-3 font-mono text-xs">
          {events.length === 0 ? (
            <div className="flex flex-col items-center gap-1.5 py-6 text-center text-[11px] text-[var(--text-muted)]">
              <Radio className="h-4 w-4 animate-pulse" />
              <span>No agent activity yet. Run the agents and each stage reports here.</span>
            </div>
          ) : (
            events.map((ev, i) => (
              <div
                key={ev.id || i}
                className="flex items-start gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--glass-subtle-bg)] p-2.5 transition-colors hover:border-[var(--border-red)]"
              >
                <span className="mt-0.5">
                  {ev.severity === 'success' ? (
                    <CheckCircle className="h-3.5 w-3.5 text-[var(--green)]" />
                  ) : ev.severity === 'error' ? (
                    <AlertCircle className="h-3.5 w-3.5 text-[var(--red)]" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5 text-[var(--accent)]" />
                  )}
                </span>

                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cx(
                        'rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider',
                        badgeStyle(ev.event_type, ev.severity)
                      )}
                    >
                      {formatEventType(ev.event_type)}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)]">
                      {ev.timestamp
                        ? new Date(ev.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })
                        : 'Just now'}
                    </span>
                  </div>

                  <p className="break-words text-[11px] leading-relaxed text-[var(--text)]">
                    {ev.message}
                  </p>

                  {renderPayload(ev.payload)}
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
