"use client";

import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";
import { LatencyMetric, KinematicMetric } from "@/types/telemetry";
import { Activity, Clock, Zap } from "lucide-react";

interface LatencyKinematicsChartsProps {
  latencyHistory: LatencyMetric[];
  kinematicHistory: KinematicMetric[];
}

export default function LatencyKinematicsCharts({
  latencyHistory,
  kinematicHistory,
}: LatencyKinematicsChartsProps) {
  const latestLatency = latencyHistory[latencyHistory.length - 1] || {
    p50: 3.8,
    p95: 8.2,
    rawLatencyMs: 4.1,
  };

  const latestKinematic = kinematicHistory[kinematicHistory.length - 1] || {
    ax: 0,
    ay: 0,
    az: 0.98,
    alphaTotal: 0.02,
    angularRateMag: 0.45,
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 w-full">
      {/* 1. Recovery Latency Distribution Chart (P50, P95) */}
      <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-3.5 flex flex-col shadow-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <div>
              <div className="font-mono text-xs font-bold tracking-wider text-slate-200">
                RECOVERY LATENCY DISTRIBUTION (P₅₀, P₉₅)
              </div>
              <div className="text-[10px] font-mono text-slate-400">
                In-situ self-healing cycle benchmark & network transit
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-2 py-0.5 rounded bg-[#0D1117] border border-[#30363D] text-cyan-400">
              P₅₀: <strong className="text-white">{latestLatency.p50} ms</strong>
            </span>
            <span className="px-2 py-0.5 rounded bg-[#0D1117] border border-[#30363D] text-amber-400">
              P₉₅: <strong className="text-white">{latestLatency.p95} ms</strong>
            </span>
          </div>
        </div>

        {/* Recharts Area/Line Chart */}
        <div className="h-48 w-full mt-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={latencyHistory}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                <linearGradient id="p50Gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06B6D4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="p95Gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262D" />
              <XAxis
                dataKey="timestamp"
                stroke="#6E7681"
                tick={{ fontSize: 9, fontFamily: "monospace" }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#6E7681"
                tick={{ fontSize: 9, fontFamily: "monospace" }}
                domain={[0, "auto"]}
                unit="ms"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as LatencyMetric;
                    return (
                      <div className="bg-[#0D1117]/95 border border-[#30363D] p-2 rounded shadow-2xl font-mono text-xs">
                        <div className="text-[10px] text-slate-400 mb-1 border-b border-[#30363D] pb-1">
                          {data.timestamp}
                        </div>
                        <div className="text-cyan-400">P₅₀ (Median): {data.p50} ms</div>
                        <div className="text-amber-400">P₉₅ (95th %): {data.p95} ms</div>
                        <div className="text-slate-400 text-[10px]">
                          Raw Latency: {data.rawLatencyMs} ms
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={25} stroke="#EF4444" strokeDasharray="4 4" label="" />
              <Area
                type="monotone"
                dataKey="p95"
                stroke="#F59E0B"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#p95Gradient)"
                name="P95 Latency"
              />
              <Area
                type="monotone"
                dataKey="p50"
                stroke="#06B6D4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#p50Gradient)"
                name="P50 Latency"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Kinematic Acceleration Trends Chart */}
      <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-3.5 flex flex-col shadow-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <div>
              <div className="font-mono text-xs font-bold tracking-wider text-slate-200">
                KINEMATIC ACCELERATION & RATE TRENDS
              </div>
              <div className="text-[10px] font-mono text-slate-400">
                Linear accelerations [ax, ay, az] & angular acceleration α_total
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-2 py-0.5 rounded bg-[#0D1117] border border-[#30363D] text-emerald-400">
              |α|: <strong className="text-white">{latestKinematic.alphaTotal} rad/s²</strong>
            </span>
          </div>
        </div>

        {/* Recharts Kinematics Multi-Line Chart */}
        <div className="h-48 w-full mt-1">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={kinematicHistory}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#21262D" />
              <XAxis
                dataKey="timestamp"
                stroke="#6E7681"
                tick={{ fontSize: 9, fontFamily: "monospace" }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#6E7681"
                tick={{ fontSize: 9, fontFamily: "monospace" }}
                unit="m/s²"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as KinematicMetric;
                    return (
                      <div className="bg-[#0D1117]/95 border border-[#30363D] p-2 rounded shadow-2xl font-mono text-xs">
                        <div className="text-[10px] text-slate-400 mb-1 border-b border-[#30363D] pb-1">
                          {data.timestamp}
                        </div>
                        <div className="text-cyan-400">ax: {data.ax} m/s²</div>
                        <div className="text-sky-400">ay: {data.ay} m/s²</div>
                        <div className="text-purple-400">az: {data.az} m/s²</div>
                        <div className="text-amber-400 border-t border-[#30363D] mt-1 pt-0.5">
                          Total α: {data.alphaTotal} rad/s²
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line
                type="monotone"
                dataKey="ax"
                stroke="#06B6D4"
                strokeWidth={1.5}
                dot={false}
                name="ax"
              />
              <Line
                type="monotone"
                dataKey="ay"
                stroke="#38BDF8"
                strokeWidth={1.5}
                dot={false}
                name="ay"
              />
              <Line
                type="monotone"
                dataKey="az"
                stroke="#A855F7"
                strokeWidth={1.5}
                dot={false}
                name="az"
              />
              <Line
                type="monotone"
                dataKey="alphaTotal"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
                name="alphaTotal"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
