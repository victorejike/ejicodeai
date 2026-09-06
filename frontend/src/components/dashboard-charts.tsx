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

const COLORS = ['#0e639c', '#4ec9b0', '#569cd6', '#c586c0', '#dcdcaa', '#f44747'];

export function OpportunityDiscoveryChart({ data }: { data: Array<{ range: string; count: number; label: string }> }) {
  return (
    <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-vscode-text">Opportunity Discovery Graph</h3>
          <p className="text-xs text-vscode-muted">Scored lead distribution by fit bucket</p>
        </div>
        <span className="text-xs font-mono bg-vscode-surface px-2 py-0.5 rounded text-vscode-green">Live Model</span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3e3e42" opacity={0.5} />
            <XAxis dataKey="range" stroke="#858585" fontSize={11} />
            <YAxis stroke="#858585" fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#252526', borderColor: '#3e3e42', borderRadius: '4px', fontSize: '12px' }}
              formatter={(value: any, name: any) => [`${value} Leads`, 'Count']}
            />
            <Bar dataKey="count" fill="#0e639c" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function CompanyGrowthChart({ data }: { data: Array<{ stage: string; companies: number }> }) {
  return (
    <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-vscode-text">Company Growth Graph</h3>
          <p className="text-xs text-vscode-muted">Pipeline advancement from discovery to client</p>
        </div>
        <span className="text-xs font-mono bg-vscode-surface px-2 py-0.5 rounded text-vscode-blue">Funnel</span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="growthGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4ec9b0" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#4ec9b0" stopOpacity={0.0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#3e3e42" opacity={0.5} />
            <XAxis dataKey="stage" stroke="#858585" fontSize={11} />
            <YAxis stroke="#858585" fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#252526', borderColor: '#3e3e42', borderRadius: '4px', fontSize: '12px' }}
            />
            <Area type="monotone" dataKey="companies" stroke="#4ec9b0" strokeWidth={2} fillOpacity={1} fill="url(#growthGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function AgentPerformanceChart({ data }: { data: Array<{ agent: string; runs: number; success_rate: number; avg_seconds: number }> }) {
  return (
    <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-vscode-text">Agent Performance Graph</h3>
          <p className="text-xs text-vscode-muted">Reliability rate & run latency by agent type</p>
        </div>
        <span className="text-xs font-mono bg-vscode-surface px-2 py-0.5 rounded text-vscode-yellow">Execution Metrics</span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3e3e42" opacity={0.5} />
            <XAxis dataKey="agent" stroke="#858585" fontSize={10} />
            <YAxis stroke="#858585" fontSize={11} unit="%" />
            <Tooltip
              contentStyle={{ backgroundColor: '#252526', borderColor: '#3e3e42', borderRadius: '4px', fontSize: '12px' }}
              formatter={(value: any, name: any) => [`${value}%`, 'Success Rate']}
            />
            <Bar dataKey="success_rate" fill="#569cd6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function OutreachSuccessChart({ data }: { data: Array<{ metric: string; value: number; fill: string }> }) {
  return (
    <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-vscode-text">Outreach Success Graph</h3>
          <p className="text-xs text-vscode-muted">Delivery, open, and response conversion rates</p>
        </div>
        <span className="text-xs font-mono bg-vscode-surface px-2 py-0.5 rounded text-emerald-400">Conversion</span>
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
            <Tooltip contentStyle={{ backgroundColor: '#252526', borderColor: '#3e3e42', borderRadius: '4px', fontSize: '12px' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function RevenuePipelineChart({ data }: { data: Array<{ stage: string; value: number; deals: number }> }) {
  return (
    <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-vscode-text">Revenue Pipeline Graph</h3>
          <p className="text-xs text-vscode-muted">Estimated contract volume across active deal stages</p>
        </div>
        <span className="text-xs font-mono bg-vscode-surface px-2 py-0.5 rounded text-purple-400">Forecast</span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3e3e42" opacity={0.5} />
            <XAxis dataKey="stage" stroke="#858585" fontSize={10} />
            <YAxis stroke="#858585" fontSize={11} tickFormatter={(val) => `$${val / 1000}k`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#252526', borderColor: '#3e3e42', borderRadius: '4px', fontSize: '12px' }}
              formatter={(value: any) => [`$${value.toLocaleString()}`, 'Pipeline Value']}
            />
            <Bar dataKey="value" fill="#c586c0" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ContactAcquisitionChart({ data }: { data: Array<{ category: string; count: number }> }) {
  return (
    <div className="bg-vscode-sidebar border border-vscode-border rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-vscode-text">Contact Acquisition Graph</h3>
          <p className="text-xs text-vscode-muted">Decision-maker discovery & verification health</p>
        </div>
        <span className="text-xs font-mono bg-vscode-surface px-2 py-0.5 rounded text-blue-400">Leads</span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart layout="vertical" data={data || []} margin={{ top: 10, right: 20, left: 30, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3e3e42" opacity={0.5} />
            <XAxis type="number" stroke="#858585" fontSize={11} />
            <YAxis dataKey="category" type="category" stroke="#858585" fontSize={11} />
            <Tooltip
              contentStyle={{ backgroundColor: '#252526', borderColor: '#3e3e42', borderRadius: '4px', fontSize: '12px' }}
            />
            <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
