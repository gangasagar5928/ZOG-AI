"use client";

import React, { useState, useEffect } from "react";
import HeaderHUD from "@/components/HeaderHUD";
import ThreatOverlays from "@/components/ThreatOverlays";
import AttitudeVisualizer from "@/components/AttitudeVisualizer";
import ActuatorGatingPanel from "@/components/ActuatorGatingPanel";
import OperatorControlPanel from "@/components/OperatorControlPanel";
import EventStream from "@/components/EventStream";
import LatencyKinematicsCharts from "@/components/LatencyKinematicsCharts";
import { telemetryClient } from "@/lib/telemetryClient";
import { initAnalytics } from "@/lib/firebase";
import {
  SpacecraftTelemetry,
  TelemetryEvent,
  LatencyMetric,
  KinematicMetric,
} from "@/types/telemetry";

export default function MissionControlDashboard() {
  const [telemetry, setTelemetry] = useState<SpacecraftTelemetry | null>(null);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [latencyHistory, setLatencyHistory] = useState<LatencyMetric[]>([]);
  const [kinematicHistory, setKinematicHistory] = useState<KinematicMetric[]>([]);
  const [pollingMode, setPollingMode] = useState<"POLLING" | "STREAMING">("STREAMING");
  const [utcTime, setUtcTime] = useState<string>("");

  useEffect(() => {
    // Initialize Firebase Analytics
    initAnalytics().catch(() => {});

    // 1. Initialize initial event list
    const initialEvents: TelemetryEvent[] = [
      {
        id: "EVT-BOOT-001",
        timestamp: new Date().toISOString(),
        epochMs: Date.now() - 4000,
        severity: "info",
        affectedTensorLayer: "All Layers Verified",
        faultClassification: "System Initialization",
        message: "Mission Control UI Lead (Prachi) initialized. Telemetry client bound to backend routing.",
      },
      {
        id: "EVT-ACT-002",
        timestamp: new Date().toISOString(),
        epochMs: Date.now() - 2500,
        severity: "info",
        affectedTensorLayer: "actuator_gating.barrier_rail",
        faultClassification: "Nominal Safety Gate",
        message: "Actuator Gating Barrier armed. Control command channels clear.",
      },
    ];
    setEvents(initialEvents);

    // 2. Subscribe to Telemetry Stream
    const unsubscribeTelemetry = telemetryClient.subscribe((data) => {
      setTelemetry(data);
      setLatencyHistory([...telemetryClient.getLatencyHistory()]);
      setKinematicHistory([...telemetryClient.getKinematicHistory()]);
    });

    // 3. Subscribe to Real-time Event Stream
    const unsubscribeEvents = telemetryClient.subscribeEvents((newEvent) => {
      setEvents((prev) => [...prev.slice(-99), newEvent]);
    });

    // 4. Start Telemetry Engine
    telemetryClient.start();

    // 5. UTC Clock Timer
    const clockInterval = setInterval(() => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 23));
    }, 50);

    return () => {
      unsubscribeTelemetry();
      unsubscribeEvents();
      telemetryClient.stop();
      clearInterval(clockInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0D1117] text-[#C9D1D9] flex flex-col aerospace-grid-bg">
      {/* 1. Header HUD with LAN IP Config & Mission Status */}
      <HeaderHUD
        backendStatus={telemetry?.network.backendStatus || "simulated"}
        activeUrl={telemetry?.network.activeUrl || "Aaditya GPU Node LAN"}
        rttMs={telemetry?.network.rttMs || 2.4}
        packetCount={telemetry?.network.packetCount || 0}
        utcTime={utcTime}
      />

      {/* Main Mission Control Grid Container */}
      <main className="flex-1 p-3 md:p-5 max-w-[1800px] w-full mx-auto flex flex-col gap-4">
        {/* 2. Threat Overlays & Operational Badges */}
        <ThreatOverlays
          state={telemetry?.state || "NOMINAL"}
          tensorHealth={telemetry?.tensorHealthIndex ?? 1.0}
          radiationFlux={telemetry?.radiationFluxKrad ?? 28.4}
          seuStrikes={telemetry?.seuStrikesTotal ?? 0}
          recoveryCycles={telemetry?.recoveryCyclesTotal ?? 0}
        />

        {/* 3. Center Section: 3D Attitude Visualizer & Actuator Gating Barrier */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
          {/* Central 3D Spacecraft Attitude Visualizer (7 Columns on XL) */}
          <div className="xl:col-span-7 h-[460px] md:h-[500px]">
            <AttitudeVisualizer telemetry={telemetry} />
          </div>

          {/* Right Column: Actuator Gating Barrier & Operator Commands (5 Columns on XL) */}
          <div className="xl:col-span-5 flex flex-col gap-4">
            {/* Actuator Gating Barrier Panel */}
            <ActuatorGatingPanel busState={telemetry?.actuatorBus || null} />

            {/* Operator Control Panel */}
            <OperatorControlPanel
              pollingMode={pollingMode}
              onPollingModeChange={setPollingMode}
            />
          </div>
        </div>

        {/* 4. Telemetry Feeds & Latency Distribution Charts */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
          {/* Latency (P50, P95) & Kinematics Charts (7 Columns on XL) */}
          <div className="xl:col-span-7">
            <LatencyKinematicsCharts
              latencyHistory={latencyHistory}
              kinematicHistory={kinematicHistory}
            />
          </div>

          {/* Real-time Scrolling Event Stream (5 Columns on XL) */}
          <div className="xl:col-span-5 h-[340px]">
            <EventStream
              events={events}
              onClear={() => setEvents([])}
            />
          </div>
        </div>
      </main>

      {/* Footer Status Bar */}
      <footer className="w-full bg-[#161B22] border-t border-[#30363D] px-4 py-2 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-500">
        <div className="flex items-center gap-3">
          <span className="text-emerald-400 font-semibold">● TELEMETRY STREAM ONLINE</span>
          <span>Buffer: 60Hz Quaternion Kinematics</span>
          <span className="hidden sm:inline">Invariant Checker: ACTIVE (Norm Clamp)</span>
        </div>
        <div className="flex items-center gap-2">
          <span>Obsidian Dark Mode</span>
          <span>•</span>
          <span>Lead: Prachi</span>
          <span>•</span>
          <span className="text-cyan-400">Next.js 14 App Router</span>
        </div>
      </footer>
    </div>
  );
}
