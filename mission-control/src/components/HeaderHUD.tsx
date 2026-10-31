"use client";

import React, { useState } from "react";
import { telemetryClient } from "@/lib/telemetryClient";
import {
  Satellite,
  Wifi,
  WifiOff,
  Server,
  Settings,
  Clock,
  Shield,
  Laptop,
} from "lucide-react";

interface HeaderHUDProps {
  backendStatus: "connected_primary" | "connected_fallback" | "simulated" | "disconnected";
  activeUrl: string;
  rttMs: number;
  packetCount: number;
  utcTime: string;
}

export default function HeaderHUD({
  backendStatus,
  activeUrl,
  rttMs,
  packetCount,
  utcTime,
}: HeaderHUDProps) {
  const [showConfig, setShowConfig] = useState<boolean>(false);
  const [customIp, setCustomIp] = useState<string>(telemetryClient.getPrimaryUrl());
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleApplyIp = () => {
    telemetryClient.setBackendUrl(customIp);
    setShowConfig(false);
  };

  const handleTestPing = async () => {
    setTestResult("Pinging " + customIp + "...");
    try {
      const start = performance.now();
      const res = await fetch(`${customIp}/api/health`, {
        signal: AbortSignal.timeout(1500),
      });
      const dur = Math.round(performance.now() - start);
      if (res.ok) {
        setTestResult(`SUCCESS: GPU Node reachable in ${dur}ms (HTTP ${res.status})`);
      } else {
        setTestResult(`WARNING: HTTP ${res.status} returned in ${dur}ms`);
      }
    } catch (err: any) {
      setTestResult(`OFFLINE / UNREACHABLE: Using automated fallback`);
    }
  };

  return (
    <>
      <header className="w-full bg-[#161B22] border-b border-[#30363D] px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 shadow-2xl z-20 sticky top-0">
        {/* Left: Mission Title & Lead Operator Info */}
        <div className="flex items-center gap-3">
          <div className="p-1 bg-[#0D1117] rounded-lg border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.25)] flex items-center justify-center overflow-hidden h-11 w-11 shrink-0">
            <img src="/logo.png" alt="RadZero Emblem" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-mono text-sm md:text-base font-extrabold tracking-wider text-slate-100 uppercase">
                RADZERO // MISSION CONTROL HUD
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-semibold tracking-wide">
                AEROSPACE OBSIDIAN v2.4
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
              <span className="flex items-center gap-1 text-slate-300">
                <Laptop className="w-3 h-3 text-cyan-400" />
                Member 2 (Prachi): Frontend & UI Lead
              </span>
              <span className="text-[#30363D]">|</span>
              <span className="text-slate-400">Workstation: UI Dev Laptop</span>
            </div>
          </div>
        </div>

        {/* Right: Network Status, Mission Clock & Node Config */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Mission UTC Clock */}
          <div className="flex items-center gap-1.5 px-3 py-1 bg-[#0D1117] border border-[#30363D] rounded font-mono text-xs text-slate-300 shadow-sm">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-500 text-[10px]">UTC</span>
            <span className="font-bold text-slate-100">{utcTime || "00:00:00.000"}</span>
          </div>

          {/* Network Client Routing Indicator */}
          <div
            onClick={() => setShowConfig(true)}
            className="cursor-pointer group flex items-center gap-2 px-3 py-1 bg-[#0D1117] hover:bg-[#21262D] border border-[#30363D] hover:border-cyan-500 rounded font-mono text-xs transition-colors shadow-sm"
            title="Click to configure Aaditya's GPU Node IP and Network Fallback"
          >
            {backendStatus === "connected_primary" ? (
              <Wifi className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            ) : backendStatus === "connected_fallback" ? (
              <Server className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-cyan-400" />
            )}

            <div className="flex flex-col text-left">
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    backendStatus === "connected_primary"
                      ? "bg-emerald-400"
                      : backendStatus === "connected_fallback"
                      ? "bg-amber-400"
                      : "bg-cyan-400"
                  }`}
                />
                <span className="text-[10px] text-slate-400 font-semibold truncate max-w-[130px]">
                  {backendStatus === "connected_primary"
                    ? "AADITYA GPU NODE"
                    : backendStatus === "connected_fallback"
                    ? "FALLBACK LOCALHOST"
                    : "IN-SITU SIMULATOR"}
                </span>
              </div>
              <div className="text-[9px] text-slate-500 flex items-center gap-1">
                <span>RTT: {rttMs}ms</span>
                <span>•</span>
                <span>PKT: #{packetCount}</span>
              </div>
            </div>

            <Settings className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-400 transition-colors ml-1" />
          </div>
        </div>
      </header>

      {/* Dynamic Network Node Configuration Modal */}
      {showConfig && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#161B22] border border-[#30363D] rounded-xl max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#30363D] pb-3">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-cyan-400" />
                <h3 className="font-mono text-sm font-bold text-slate-100 uppercase">
                  LAN Routing & GPU Node Config
                </h3>
              </div>
              <button
                onClick={() => setShowConfig(false)}
                className="text-slate-400 hover:text-white font-mono text-sm px-2"
              >
                ✕
              </button>
            </div>

            <p className="text-xs font-mono text-slate-400 leading-relaxed">
              Connect the UI across the LAN to <strong>Aaditya’s GPU node IP</strong>{" "}
              (e.g., <code className="text-cyan-300">http://192.168.1.150:8000</code>).
              If unreachable, the client automatically falls back to{" "}
              <code className="text-amber-300">localhost:8000</code> and activates the
              internal physics simulator.
            </p>

            <div className="space-y-1.5 font-mono text-xs">
              <label className="text-slate-300 block">
                Primary Target (NEXT_PUBLIC_BACKEND_URL):
              </label>
              <input
                type="text"
                value={customIp}
                onChange={(e) => setCustomIp(e.target.value)}
                placeholder="http://<AADITYA_IP>:8000"
                className="w-full bg-[#0D1117] border border-[#30363D] focus:border-cyan-500 rounded p-2 text-slate-100 placeholder:text-slate-600 outline-none"
              />
            </div>

            {testResult && (
              <div className="p-2.5 rounded bg-[#0D1117] border border-[#30363D] text-[11px] font-mono text-slate-300">
                {testResult}
              </div>
            )}

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={handleTestPing}
                className="px-3 py-1.5 rounded bg-[#21262D] border border-[#30363D] text-slate-300 hover:text-white font-mono text-xs"
              >
                Test Connectivity
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowConfig(false)}
                  className="px-3 py-1.5 rounded bg-transparent text-slate-400 hover:text-white font-mono text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApplyIp}
                  className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold shadow-lg"
                >
                  Connect LAN Node
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
