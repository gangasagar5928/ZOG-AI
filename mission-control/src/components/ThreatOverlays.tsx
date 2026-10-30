"use client";

import React from "react";
import { OperationalState } from "@/types/telemetry";
import {
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
  RefreshCw,
  Activity,
  Cpu,
  Radio,
} from "lucide-react";

interface ThreatOverlaysProps {
  state: OperationalState;
  tensorHealth: number;
  radiationFlux: number;
  seuStrikes: number;
  recoveryCycles: number;
}

export default function ThreatOverlays({
  state,
  tensorHealth,
  radiationFlux,
  seuStrikes,
  recoveryCycles,
}: ThreatOverlaysProps) {
  // Operational Badges definitions
  const badges: {
    key: OperationalState;
    label: string;
    sublabel: string;
    badgeStyle: string;
    icon: React.ReactNode;
    isActive: boolean;
  }[] = [
    {
      key: "NOMINAL",
      label: "NOMINAL",
      sublabel: "Lyapunov Basin Stable",
      badgeStyle:
        "border-emerald-500 text-emerald-400 bg-emerald-950/60 shadow-[0_0_15px_rgba(16,185,129,0.3)]",
      icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
      isActive: state === "NOMINAL",
    },
    {
      key: "INLINE_INVARIANT_BREACH",
      label: "INLINE INVARIANT BREACH",
      sublabel: "Tensor Safety Violation",
      badgeStyle:
        "border-red-500 text-red-300 bg-red-950/80 shadow-[0_0_20px_rgba(239,68,68,0.5)] animate-pulse",
      icon: <AlertOctagon className="w-5 h-5 text-red-400 animate-spin-slow" />,
      isActive: state === "INLINE_INVARIANT_BREACH",
    },
    {
      key: "ACTUATOR_INHIBITED",
      label: "ACTUATOR INHIBITED",
      sublabel: "Barrier Interlock Clamped",
      badgeStyle:
        "border-amber-500 text-amber-300 bg-amber-950/70 shadow-[0_0_15px_rgba(245,158,11,0.35)]",
      icon: <AlertTriangle className="w-5 h-5 text-amber-400 animate-bounce" />,
      isActive: state === "ACTUATOR_INHIBITED" || state === "INLINE_INVARIANT_BREACH",
    },
    {
      key: "RECOVERY_VERIFIED",
      label: "IN-SITU RECOVERY VERIFIED",
      sublabel: "Manifold Re-projected",
      badgeStyle:
        "border-cyan-400 text-cyan-300 bg-cyan-950/70 shadow-[0_0_18px_rgba(6,182,212,0.4)]",
      icon: <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin-slow" />,
      isActive: state === "RECOVERY_VERIFIED",
    },
  ];

  return (
    <div className="w-full flex flex-col gap-3">
      {/* 4 Prominent Aerospace Operational Badges Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2.5">
        {badges.map((b) => (
          <div
            key={b.key}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 ${
              b.isActive
                ? `${b.badgeStyle} ring-1 ring-white/10`
                : "bg-[#161B22]/50 border-[#30363D]/60 text-slate-500 opacity-50"
            }`}
          >
            <div
              className={`p-2 rounded-md ${
                b.isActive ? "bg-[#0D1117]/80" : "bg-[#0D1117]/40"
              }`}
            >
              {b.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <div className="font-mono text-xs font-bold tracking-wider truncate">
                  {b.label}
                </div>
                {b.isActive && (
                  <span className="w-2 h-2 rounded-full bg-current animate-ping" />
                )}
              </div>
              <div className="text-[10px] font-mono text-slate-400 truncate">
                {b.sublabel}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Auxiliary Threat & System Telemetry Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        {/* Tensor Health Metric */}
        <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              Tensor Health
            </span>
            <span
              className={`font-mono font-bold ${
                tensorHealth > 0.8
                  ? "text-emerald-400"
                  : tensorHealth > 0.5
                  ? "text-amber-400"
                  : "text-red-400"
              }`}
            >
              {(tensorHealth * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-[#0D1117] h-1.5 rounded-full overflow-hidden border border-[#30363D]">
            <div
              className={`h-full transition-all duration-300 ${
                tensorHealth > 0.8
                  ? "bg-emerald-500"
                  : tensorHealth > 0.5
                  ? "bg-amber-500"
                  : "bg-red-500"
              }`}
              style={{ width: `${Math.min(100, Math.max(0, tensorHealth * 100))}%` }}
            />
          </div>
        </div>

        {/* Radiation Flux Gauge */}
        <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-amber-400" />
              Radiation Flux
            </span>
            <span
              className={`font-mono font-bold ${
                radiationFlux > 100 ? "text-red-400" : "text-slate-300"
              }`}
            >
              {radiationFlux.toFixed(1)} krad
            </span>
          </div>
          <div className="text-[10px] font-mono text-slate-500">
            {radiationFlux > 100 ? "WARNING: Solar Flux Spike" : "Nominal LEO Background"}
          </div>
        </div>

        {/* SEU Strikes Accumulated */}
        <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <AlertOctagon className="w-3.5 h-3.5 text-red-400" />
              SEU Strikes
            </span>
            <span className="font-mono font-bold text-red-400">{seuStrikes}</span>
          </div>
          <div className="text-[10px] font-mono text-slate-500">
            Total Radiation Bitflips
          </div>
        </div>

        {/* Recovery Cycles */}
        <div className="bg-[#161B22] border border-[#30363D] rounded-lg p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-cyan-400" />
              Recoveries
            </span>
            <span className="font-mono font-bold text-cyan-400">{recoveryCycles}</span>
          </div>
          <div className="text-[10px] font-mono text-slate-500">
            In-Situ Restorations Completed
          </div>
        </div>
      </div>
    </div>
  );
}
