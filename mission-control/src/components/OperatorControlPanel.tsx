"use client";

import React, { useState } from "react";
import { telemetryClient } from "@/lib/telemetryClient";
import {
  Radiation,
  RefreshCw,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Radio,
  Zap,
} from "lucide-react";

interface OperatorControlPanelProps {
  pollingMode: "POLLING" | "STREAMING";
  onPollingModeChange: (mode: "POLLING" | "STREAMING") => void;
}

export default function OperatorControlPanel({
  pollingMode,
  onPollingModeChange,
}: OperatorControlPanelProps) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error" | "warning";
    message: string;
    timestamp: string;
  } | null>(null);

  const showFeedback = (
    type: "success" | "error" | "warning",
    message: string
  ) => {
    setFeedback({
      type,
      message,
      timestamp: new Date().toLocaleTimeString(),
    });
    setTimeout(() => {
      setFeedback(null);
    }, 4500);
  };

  const handleInjectSEU = async () => {
    setLoadingAction("SEU");
    try {
      const res = await telemetryClient.injectSEU();
      showFeedback(
        "error",
        `[SEU STRIKE EXECUTED]: Invariant breach triggered. Interlock clamped.`
      );
    } catch (err: any) {
      showFeedback("error", `Failed to execute SEU strike: ${err?.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleTriggerRecovery = async () => {
    setLoadingAction("RECOVERY");
    try {
      const res = await telemetryClient.triggerRecovery();
      showFeedback(
        "success",
        `[IN-SITU RECOVERY VERIFIED]: Tensor layers repaired. Rate damping engaged.`
      );
    } catch (err: any) {
      showFeedback("error", `Failed to trigger recovery: ${err?.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleEngageSafeHold = async () => {
    setLoadingAction("SAFEHOLD");
    try {
      const res = await telemetryClient.engageSafeHold();
      showFeedback(
        "warning",
        `[SAFE-HOLD ENGAGED]: B-Dot magnetorquers active. Sun-pointing locked.`
      );
    } catch (err: any) {
      showFeedback("error", `Failed to engage safe-hold: ${err?.message}`);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleTogglePolling = () => {
    const nextMode = pollingMode === "STREAMING" ? "POLLING" : "STREAMING";
    telemetryClient.setPollingMode(nextMode);
    onPollingModeChange(nextMode);
    showFeedback(
      "success",
      `Telemetry transport switched to ${nextMode} mode (${
        nextMode === "STREAMING" ? "50ms / 20Hz" : "250ms / 4Hz"
      }).`
    );
  };

  const handleResetNominal = () => {
    telemetryClient.resetToNominal();
    showFeedback("success", "System reset to celestial tracking NOMINAL state.");
  };

  return (
    <div className="w-full bg-[#161B22] border border-[#30363D] rounded-lg p-4 flex flex-col gap-3 shadow-xl">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-[#30363D] pb-2.5">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          <span className="font-mono text-xs font-bold tracking-wider text-slate-200">
            OPERATOR COMMAND & INJECTION CONSOLE
          </span>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0D1117] text-slate-400 border border-[#30363D]">
          AUTH: FLIGHT LEAD (PRACHI)
        </span>
      </div>

      {/* Primary Action Buttons Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* 1. Inject SEU Strike */}
        <button
          onClick={handleInjectSEU}
          disabled={loadingAction !== null}
          className="group relative flex flex-col items-center justify-center p-3 rounded-lg border border-red-600/70 bg-red-950/40 hover:bg-red-900/60 active:scale-95 transition-all text-red-200 shadow-[0_0_15px_rgba(239,68,68,0.2)] hover:shadow-[0_0_20px_rgba(239,68,68,0.4)] disabled:opacity-50"
        >
          <div className="p-2 rounded-full bg-red-900/60 mb-1.5 group-hover:scale-110 transition-transform">
            <Radiation className="w-5 h-5 text-red-400 animate-spin-slow" />
          </div>
          <span className="font-mono text-xs font-bold tracking-wide">
            INJECT SEU STRIKE
          </span>
          <span className="text-[9px] font-mono text-red-400/80 mt-0.5">
            Bitflip Radiation Hazard
          </span>
        </button>

        {/* 2. Trigger In-Situ Recovery */}
        <button
          onClick={handleTriggerRecovery}
          disabled={loadingAction !== null}
          className="group relative flex flex-col items-center justify-center p-3 rounded-lg border border-cyan-500/70 bg-cyan-950/40 hover:bg-cyan-900/60 active:scale-95 transition-all text-cyan-200 shadow-[0_0_15px_rgba(6,182,212,0.2)] hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:opacity-50"
        >
          <div className="p-2 rounded-full bg-cyan-900/60 mb-1.5 group-hover:scale-110 transition-transform">
            <RefreshCw className="w-5 h-5 text-cyan-300" />
          </div>
          <span className="font-mono text-xs font-bold tracking-wide">
            TRIGGER IN-SITU RECOVERY
          </span>
          <span className="text-[9px] font-mono text-cyan-400/80 mt-0.5">
            Self-Healing SVD Projection
          </span>
        </button>

        {/* 3. Engage Safe-Hold */}
        <button
          onClick={handleEngageSafeHold}
          disabled={loadingAction !== null}
          className="group relative flex flex-col items-center justify-center p-3 rounded-lg border border-amber-500/70 bg-amber-950/40 hover:bg-amber-900/60 active:scale-95 transition-all text-amber-200 shadow-[0_0_15px_rgba(245,158,11,0.2)] hover:shadow-[0_0_20px_rgba(245,158,11,0.4)] disabled:opacity-50"
        >
          <div className="p-2 rounded-full bg-amber-900/60 mb-1.5 group-hover:scale-110 transition-transform">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
          </div>
          <span className="font-mono text-xs font-bold tracking-wide">
            ENGAGE SAFE-HOLD
          </span>
          <span className="text-[9px] font-mono text-amber-400/80 mt-0.5">
            B-Dot Rate Damping & Sun-Lock
          </span>
        </button>

        {/* 4. Toggle Polling Mode */}
        <button
          onClick={handleTogglePolling}
          className="group relative flex flex-col items-center justify-center p-3 rounded-lg border border-sky-500/60 bg-sky-950/40 hover:bg-sky-900/60 active:scale-95 transition-all text-sky-200 shadow-[0_0_12px_rgba(56,189,248,0.2)]"
        >
          <div className="p-2 rounded-full bg-sky-900/60 mb-1.5 group-hover:scale-110 transition-transform">
            <Radio className="w-5 h-5 text-sky-400" />
          </div>
          <span className="font-mono text-xs font-bold tracking-wide">
            TOGGLE POLLING MODE
          </span>
          <span className="text-[9px] font-mono text-sky-300 font-semibold mt-0.5">
            Active: {pollingMode} ({pollingMode === "STREAMING" ? "20Hz" : "4Hz"})
          </span>
        </button>
      </div>

      {/* Auxiliary Quick Reset Button & Feedback Banner */}
      <div className="flex flex-wrap items-center justify-between pt-1 gap-2">
        <button
          onClick={handleResetNominal}
          className="px-3 py-1.5 rounded text-xs font-mono bg-[#0D1117] border border-emerald-500/40 hover:border-emerald-500 text-emerald-400 flex items-center gap-1.5 transition-colors"
        >
          <Zap className="w-3.5 h-3.5 text-emerald-400" />
          Quick Reset to Celestial Tracking Nominal
        </button>

        {/* Dynamic Command Feedback Notification */}
        {feedback && (
          <div
            className={`flex items-center gap-2 px-3 py-1 rounded text-xs font-mono border backdrop-blur animate-fade-in ${
              feedback.type === "success"
                ? "bg-emerald-950/80 border-emerald-500 text-emerald-300"
                : feedback.type === "warning"
                ? "bg-amber-950/80 border-amber-500 text-amber-300"
                : "bg-red-950/80 border-red-500 text-red-300"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
            <span>{feedback.message}</span>
            <span className="text-[10px] text-slate-400">({feedback.timestamp})</span>
          </div>
        )}
      </div>
    </div>
  );
}
