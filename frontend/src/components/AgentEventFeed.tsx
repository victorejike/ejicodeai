'use client';

import { useState, useEffect, useRef } from 'react';
import { Activity, Radio, CheckCircle, AlertCircle, Sparkles, Terminal, ChevronDown, ChevronUp } from 'lucide-react';

export interface AgentEvent {
  id: string;
  event_type: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  message: string;
  payload?: any;
  timestamp: string;
}

export default function AgentEventFeed({
  userId,
  orgId,
  title = "Autonomous AI Agent Activity",
}: {
  userId?: string;
  orgId?: string;
  title?: string;
}) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Build SSE URL
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (orgId) params.append('organization_id', orgId);

    const streamUrl = `/api/events/stream?${params.toString()}`;
    let es: EventSource;

    try {
      es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
      };

      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          if (parsed && parsed.message) {
            setEvents((prev) => {
              // Avoid duplicates
              if (prev.some((item) => item.id === parsed.id)) return prev;
              const next = [...prev, parsed];
              return next.slice(-40); // Keep last 40 events
            });
          }
        } catch (err) {
          // ignore keepalive or parse error
        }
      };

      es.onerror = () => {
        setIsConnected(false);
      };
    } catch (err) {
      console.warn('Could not initialize EventSource:', err);
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [userId, orgId]);

  useEffect(() => {
    if (isExpanded && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, isExpanded]);

  const getBadgeStyle = (type: string, severity: string) => {
    if (severity === 'error') return 'border-red-500/30 text-red-400 bg-red-500/10';
    if (severity === 'success') return 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10';
    if (type.startsWith('cv.')) return 'border-purple-500/30 text-purple-400 bg-purple-500/10';
    if (type.startsWith('opportunities.') || type.startsWith('talent.')) return 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10';
    return 'border-white/10 text-zinc-300 bg-white/5';
  };

  const formatEventType = (type: string) => {
    if (type.startsWith('cv.uploaded')) return 'CV Ingestion';
    if (type.startsWith('cv.extracted')) return 'Factual Intelligence';
    if (type.startsWith('opportunities.matched')) return '6-Factor Match';
    if (type.startsWith('talent.discovered')) return 'Live Headhunter';
    if (type.startsWith('candidate.invited')) return 'Direct Outreach';
    if (type.startsWith('requirement.')) return 'Requirement Engine';
    return type.replace('.', ' ').toUpperCase();
  };

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#0c0c12]/90 backdrop-blur-2xl overflow-hidden shadow-2xl transition-all">
      {/* Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="px-4 py-3 bg-white/[0.02] border-b border-white/[0.06] flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isConnected ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isConnected ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-white">
            <Terminal className="w-3.5 h-3.5 text-red-400" />
            <span>{title}</span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded-full border border-white/[0.08] bg-white/[0.02] text-zinc-400 font-mono">
            {isConnected ? 'LIVE FEED' : 'CONNECTING'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] text-zinc-500 font-mono">
            {events.length} {events.length === 1 ? 'event' : 'events'}
          </span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-zinc-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-zinc-400" />
          )}
        </div>
      </div>

      {/* Events Body */}
      {isExpanded && (
        <div className="p-3 max-h-56 overflow-y-auto space-y-2 font-mono text-xs scrollbar-thin scrollbar-thumb-white/10">
          {events.length === 0 ? (
            <div className="py-6 text-center text-zinc-500 text-[11px] flex flex-col items-center gap-1.5">
              <Radio className="w-4 h-4 animate-pulse text-zinc-600" />
              <span>Awaiting agent workflow triggers…</span>
            </div>
          ) : (
            events.map((ev, i) => (
              <div
                key={ev.id || i}
                className="p-2.5 rounded-xl bg-black/40 border border-white/[0.04] flex items-start gap-2.5 hover:border-white/10 transition-colors"
              >
                <div className="mt-0.5">
                  {ev.severity === 'success' ? (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  ) : ev.severity === 'error' ? (
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-red-400" />
                  )}
                </div>

                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${getBadgeStyle(
                        ev.event_type,
                        ev.severity
                      )}`}
                    >
                      {formatEventType(ev.event_type)}
                    </span>
                    <span className="text-[10px] text-zinc-500">
                      {ev.timestamp
                        ? new Date(ev.timestamp).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })
                        : 'Just now'}
                    </span>
                  </div>

                  <p className="text-zinc-200 text-[11px] leading-relaxed break-words">
                    {ev.message}
                  </p>

                  {ev.payload && Object.keys(ev.payload).length > 0 && (
                    <div className="text-[10px] text-zinc-400 flex items-center gap-2 flex-wrap pt-0.5">
                      {Object.entries(ev.payload).map(([k, v]) => (
                        <span key={k} className="bg-white/[0.03] px-1.5 py-0.2 rounded border border-white/[0.05]">
                          <span className="text-zinc-500">{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                        </span>
                      ))}
                    </div>
                  )}
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
