"use client";

import React from "react";
import { ActuatorBusState } from "@/types/telemetry";
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  Gauge,
  Flame,
  Disc,
  Compass,
} from "lucide-react";

interface ActuatorGatingPanelProps {
  busState: ActuatorBusState | null;
}

export default function ActuatorGatingPanel({ busState }: ActuatorGatingPanelProps) {
  const isPermitted = busState?.gatingPermitted ?? true;
  const latchReason =
    busState?.latchReason || "Permitted - Lyapunov Safe Invariant Satisfied";

  const rw = busState?.reactionWheels || {
    xRpm: 1200,
    yRpm: -850,
    zRpm: 420,
    saturationPct: 20,
    inhibited: false,
  };

  const rcs = busState?.rcsThrusters || {
    enabled: true,
    firingRateHz: 4.2,
    thrustOutputN: 12.5,
  };

  const mag = busState?.magnetorquers || {
    bDotActive: false,
    dipoleCurrentA: 0.05,
  };

  const gimbal = busState?.gimbalServos || {
    pitchDeg: 0,
    yawDeg: 0,
    locked: false,
  };

  return (
    <div className="w-full bg-[#161B22] border border-[#30363D] rounded-lg p-4 flex flex-col gap-3.5 shadow-xl">
      {/* Header with Title and Barrier Latch Status */}
      <div className="flex items-center justify-between border-b border-[#30363D] pb-3">
        <div className="flex items-center gap-2">
          <div
            className={`p-1.5 rounded ${
              isPermitted
                ? "bg-emerald-950/80 text-emerald-400 border border-emerald-500/50"
                : "bg-red-950/80 text-red-400 border border-red-500/50 animate-pulse"
            }`}
          >
            {isPermitted ? (
              <ShieldCheck className="w-4 h-4" />
            ) : (
              <ShieldAlert className="w-4 h-4" />
            )}
          </div>
          <div>
            <div className="text-xs font-mono font-bold tracking-wider text-slate-200">
              ACTUATOR GATING BARRIER
            </div>
            <div className="text-[10px] font-mono text-slate-400">
              Hardware Bus Interlock & Command Validation Gate
            </div>
          </div>
        </div>

        {/* Big Permitted / Inhibited Visual Status Pill */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-mono font-bold tracking-widest ${
            isPermitted
              ? "bg-emerald-950/90 border-emerald-500 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]"
              : "bg-amber-950/90 border-amber-500 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.4)] animate-pulse"
          }`}
        >
          {isPermitted ? (
            <>
              <Unlock className="w-3.5 h-3.5 text-emerald-400" />
              <span>COMMANDS PERMITTED</span>
            </>
          ) : (
            <>
              <Lock className="w-3.5 h-3.5 text-amber-400" />
              <span>ACTUATOR INHIBITED</span>
            </>
          )}
        </div>
      </div>

      {/* Interlock Gating Barrier Banner */}
      <div
        className={`px-3 py-2 rounded border text-xs font-mono flex items-start gap-2.5 ${
          isPermitted
            ? "bg-[#0D1117] border-emerald-500/30 text-emerald-400/90"
            : "bg-amber-950/40 border-amber-500/50 text-amber-300"
        }`}
      >
        <span className="font-bold text-[11px] uppercase tracking-wider min-w-[95px] text-slate-400">
          INTERLOCK LATCH:
        </span>
        <span className="text-[11px] leading-relaxed break-all">{latchReason}</span>
      </div>

      {/* Hardware Bus Subsystem Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5">
        {/* 1. Reaction Wheel Array */}
        <div className="bg-[#0D1117] border border-[#30363D] rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1 text-slate-300 font-semibold">
              <Disc className="w-3.5 h-3.5 text-cyan-400" />
              Reaction Wheels
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                rw.inhibited
                  ? "bg-red-950 text-red-400 border border-red-800"
                  : "bg-emerald-950 text-emerald-400 border border-emerald-800"
              }`}
            >
              {rw.inhibited ? "INHIBITED" : "ONLINE"}
            </span>
          </div>
          <div className="space-y-0.5 text-[10px] font-mono text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">RW-X:</span>
              <span>{rw.xRpm} RPM</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">RW-Y:</span>
              <span>{rw.yRpm} RPM</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">RW-Z:</span>
              <span>{rw.zRpm} RPM</span>
            </div>
          </div>
          <div className="mt-2">
            <div className="flex justify-between text-[9px] font-mono text-slate-400 mb-0.5">
              <span>Saturation</span>
              <span className={rw.saturationPct > 80 ? "text-red-400" : "text-slate-300"}>
                {rw.saturationPct}%
              </span>
            </div>
            <div className="w-full bg-[#161B22] h-1 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  rw.saturationPct > 80
                    ? "bg-red-500"
                    : rw.saturationPct > 60
                    ? "bg-amber-500"
                    : "bg-cyan-500"
                }`}
                style={{ width: `${rw.saturationPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* 2. Reaction Control System (RCS) */}
        <div className="bg-[#0D1117] border border-[#30363D] rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1 text-slate-300 font-semibold">
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              RCS Thrusters
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                !rcs.enabled
                  ? "bg-red-950 text-red-400 border border-red-800"
                  : "bg-emerald-950 text-emerald-400 border border-emerald-800"
              }`}
            >
              {!rcs.enabled ? "GATED OFF" : "ARMED"}
            </span>
          </div>
          <div className="space-y-1 text-[10px] font-mono text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Firing Frequency:</span>
              <span>{rcs.firingRateHz.toFixed(1)} Hz</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Thrust Output:</span>
              <span>{rcs.thrustOutputN.toFixed(1)} N</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Feed Pressure:</span>
              <span className="text-emerald-400">22.4 bar</span>
            </div>
          </div>
          <div className="text-[9px] font-mono text-slate-500 mt-2">
            Nozzle Clusters: 4x Quads Active
          </div>
        </div>

        {/* 3. Magnetorquer B-Dot Damping */}
        <div className="bg-[#0D1117] border border-[#30363D] rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1 text-slate-300 font-semibold">
              <Compass className="w-3.5 h-3.5 text-emerald-400" />
              Magnetorquers
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                mag.bDotActive
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-800"
                  : "bg-slate-900 text-slate-400 border border-slate-700"
              }`}
            >
              {mag.bDotActive ? "B-DOT DAMPING" : "STANDBY"}
            </span>
          </div>
          <div className="space-y-1 text-[10px] font-mono text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Dipole Current:</span>
              <span className="text-cyan-300">{mag.dipoleCurrentA.toFixed(2)} A</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Magnetic Moment:</span>
              <span>15.2 A·m²</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Rate-Damping Loop:</span>
              <span className={mag.bDotActive ? "text-cyan-400 font-bold" : "text-slate-400"}>
                {mag.bDotActive ? "ENGAGED" : "PASSIVE"}
              </span>
            </div>
          </div>
          <div className="text-[9px] font-mono text-slate-500 mt-2">
            Earth Magnetic Vector Tracked
          </div>
        </div>

        {/* 4. Antenna / Gimbal Servos */}
        <div className="bg-[#0D1117] border border-[#30363D] rounded p-2.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
            <span className="flex items-center gap-1 text-slate-300 font-semibold">
              <Gauge className="w-3.5 h-3.5 text-purple-400" />
              Gimbal Servos
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                gimbal.locked
                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                  : "bg-emerald-950 text-emerald-400 border border-emerald-800"
              }`}
            >
              {gimbal.locked ? "LOCKED" : "TRACKING"}
            </span>
          </div>
          <div className="space-y-1 text-[10px] font-mono text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Azimuth Angle:</span>
              <span>{gimbal.yawDeg.toFixed(1)}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Elevation Angle:</span>
              <span>{gimbal.pitchDeg.toFixed(1)}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Backlash Compensator:</span>
              <span className="text-emerald-400">ACTIVE</span>
            </div>
          </div>
          <div className="text-[9px] font-mono text-slate-500 mt-2">
            Target: Deep Space Optical Network
          </div>
        </div>
      </div>
    </div>
  );
}
