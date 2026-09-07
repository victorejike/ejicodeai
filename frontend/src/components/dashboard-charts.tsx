'use client';

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

interface DashboardChartsProps {
  analytics: {
    opportunity_discovery?: Array<{ range: string; count: number; label: string }>;
    company_growth?: Array<{ stage: string; companies: number }>;
    agent_performance?: Array<{ agent: string; runs: number; success_rate: number; avg_seconds: number }>;
    outreach_success?: Array<{ metric: string; value: number; fill: string }>;
    revenue_pipeline?: Array<{ stage: string; value: number; deals: number }>;
    contact_acquisition?: Array<{ category: string; count: number }>;
  };
}

const COLORS = ['#ef4444', '#dc2626', '#f87171', '#22c55e', '#a855f7', '#3b82f6'];

export function OpportunityDiscoveryChart({ data }: { data: Array<{ range: string; count: number; label: string }> }) {
  return (
    <div className="bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/30 backdrop-blur-2xl rounded-3xl p-6 shadow-xl transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Opportunity Discovery Distribution</h3>
          <p className="text-xs text-[#9ca3af]">Lead count by candidate alignment bucket</p>
        </div>
        <span className="text-[10px] font-mono bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full text-red-400 font-bold">
          8 Channels Active
        </span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="range" stroke="#71717a" fontSize={11} />
            <YAxis stroke="#71717a" fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#08080a', borderColor: 'rgba(239, 68, 68, 0.3)', borderRadius: '1rem', fontSize: '12px', color: '#fff' }}
              formatter={(value: any) => [`${value} Opportunities`, 'Count']}
            />
            <Bar dataKey="count" fill="#ef4444" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function CompanyGrowthChart({ data }: { data: Array<{ stage: string; companies: number }> }) {
  return (
    <div className="bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/30 backdrop-blur-2xl rounded-3xl p-6 shadow-xl transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Company Pipeline Advancement</h3>
          <p className="text-xs text-[#9ca3af]">Progress across proactive and inbound stages</p>
        </div>
        <span className="text-[10px] font-mono bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full text-red-400 font-bold">
          Funnel Flow
        </span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="growthGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.45}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="stage" stroke="#71717a" fontSize={11} />
            <YAxis stroke="#71717a" fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#08080a', borderColor: 'rgba(239, 68, 68, 0.3)', borderRadius: '1rem', fontSize: '12px', color: '#fff' }}
            />
            <Area type="monotone" dataKey="companies" stroke="#ef4444" strokeWidth={2.5} fillOpacity={1} fill="url(#growthGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function AgentPerformanceChart({ data }: { data: Array<{ agent: string; runs: number; success_rate: number; avg_seconds: number }> }) {
  return (
    <div className="bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/30 backdrop-blur-2xl rounded-3xl p-6 shadow-xl transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Agent Fleet Performance</h3>
          <p className="text-xs text-[#9ca3af]">Reliability &amp; latency metrics per agent</p>
        </div>
        <span className="text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full text-emerald-400 font-bold">
          DAG Fleet
        </span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="agent" stroke="#71717a" fontSize={10} />
            <YAxis stroke="#71717a" fontSize={11} unit="%" />
            <Tooltip
              contentStyle={{ backgroundColor: '#08080a', borderColor: 'rgba(239, 68, 68, 0.3)', borderRadius: '1rem', fontSize: '12px', color: '#fff' }}
              formatter={(value: any) => [`${value}%`, 'Success Rate']}
            />
            <Bar dataKey="success_rate" fill="#f87171" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function OutreachSuccessChart({ data }: { data: Array<{ metric: string; value: number; fill: string }> }) {
  return (
    <div className="bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/30 backdrop-blur-2xl rounded-3xl p-6 shadow-xl transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Outreach &amp; Application Conversion</h3>
          <p className="text-xs text-[#9ca3af]">Delivery, open, reply, and interview rates</p>
        </div>
        <span className="text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full text-emerald-400 font-bold">
          Conversion
        </span>
      </div>
      <div className="h-60 w-full flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data || []}
              dataKey="value"
              nameKey="metric"
              cx="50%"
              cy="50%"
              outerRadius={80}
              innerRadius={48}
              paddingAngle={4}
              label={({ metric, value }) => `${metric}: ${value}`}
            >
              {(data || []).map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill || COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: '#08080a', borderColor: 'rgba(239, 68, 68, 0.3)', borderRadius: '1rem', fontSize: '12px', color: '#fff' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function RevenuePipelineChart({ data }: { data: Array<{ stage: string; value: number; deals: number }> }) {
  return (
    <div className="bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/30 backdrop-blur-2xl rounded-3xl p-6 shadow-xl transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Contract Pipeline Forecast</h3>
          <p className="text-xs text-[#9ca3af]">Estimated volume across active client milestones</p>
        </div>
        <span className="text-[10px] font-mono bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-full text-purple-400 font-bold">
          Forecast
        </span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="stage" stroke="#71717a" fontSize={10} />
            <YAxis stroke="#71717a" fontSize={11} tickFormatter={(val) => `$${val / 1000}k`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#08080a', borderColor: 'rgba(239, 68, 68, 0.3)', borderRadius: '1rem', fontSize: '12px', color: '#fff' }}
              formatter={(value: any) => [`$${value.toLocaleString()}`, 'Pipeline Value']}
            />
            <Bar dataKey="value" fill="#ef4444" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ContactAcquisitionChart({ data }: { data: Array<{ category: string; count: number }> }) {
  return (
    <div className="bg-[#0e0e14]/80 border border-white/[0.08] hover:border-red-500/30 backdrop-blur-2xl rounded-3xl p-6 shadow-xl transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white">Decision-Maker Discovery Health</h3>
          <p className="text-xs text-[#9ca3af]">Verified engineering leaders &amp; recruiters found</p>
        </div>
        <span className="text-[10px] font-mono bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full text-red-400 font-bold">
          Contacts
        </span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart layout="vertical" data={data || []} margin={{ top: 10, right: 20, left: 30, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis type="number" stroke="#71717a" fontSize={11} />
            <YAxis dataKey="category" type="category" stroke="#71717a" fontSize={11} />
            <Tooltip
              contentStyle={{ backgroundColor: '#08080a', borderColor: 'rgba(239, 68, 68, 0.3)', borderRadius: '1rem', fontSize: '12px', color: '#fff' }}
            />
            <Bar dataKey="count" fill="#dc2626" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
