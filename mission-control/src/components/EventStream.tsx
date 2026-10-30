"use client";

import React, { useState, useRef, useEffect } from "react";
import { TelemetryEvent } from "@/types/telemetry";
import {
  ListFilter,
  Pause,
  Play,
  Trash2,
  Search,
  Terminal,
  AlertOctagon,
  ShieldCheck,
  AlertTriangle,
  Info,
} from "lucide-react";

interface EventStreamProps {
  events: TelemetryEvent[];
  onClear?: () => void;
}

export default function EventStream({ events, onClear }: EventStreamProps) {
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [searchLayer, setSearchLayer] = useState<string>("");
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const scrollEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when new events arrive if not paused
  useEffect(() => {
    if (!isPaused && scrollEndRef.current) {
      scrollEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, isPaused]);

  const filteredEvents = events.filter((evt) => {
    if (filterSeverity !== "ALL" && evt.severity !== filterSeverity) {
      return false;
    }
    if (
      searchLayer &&
      !evt.affectedTensorLayer.toLowerCase().includes(searchLayer.toLowerCase()) &&
      !evt.faultClassification.toLowerCase().includes(searchLayer.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const getSeverityBadge = (severity: TelemetryEvent["severity"]) => {
    switch (severity) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-red-950 text-red-400 border border-red-800">
            <AlertOctagon className="w-3 h-3 text-red-400" />
            CRIT
          </span>
        );
      case "recovery":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
            RECOV
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            WARN
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-red-900 text-red-300 border border-red-700">
            ERR
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-900 text-slate-400 border border-slate-700">
            <Info className="w-3 h-3 text-slate-400" />
            INFO
          </span>
        );
    }
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#161B22] border border-[#30363D] rounded-lg overflow-hidden shadow-xl">
      {/* Top Controls Header */}
      <div className="flex flex-wrap items-center justify-between px-3 py-2 bg-[#0D1117] border-b border-[#30363D] gap-2">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="font-mono text-xs font-bold tracking-wider text-slate-200">
            REAL-TIME EVENT STREAM
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 bg-[#21262D] text-slate-400 rounded border border-[#30363D]">
            {events.length} records
          </span>
        </div>

        {/* Filter and Pause Controls */}
        <div className="flex items-center gap-1.5">
          {/* Quick Filter buttons */}
          <div className="flex items-center bg-[#21262D] rounded border border-[#30363D] p-0.5">
            {["ALL", "critical", "recovery", "warning"].map((sev) => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2 py-0.5 text-[10px] font-mono rounded uppercase transition-colors ${
                  filterSeverity === sev
                    ? "bg-[#30363D] text-slate-100 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          {/* Pause / Resume Button */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-1.5 rounded border transition-colors ${
              isPaused
                ? "bg-amber-950/80 border-amber-500 text-amber-300"
                : "bg-[#21262D] border-[#30363D] text-slate-400 hover:text-slate-200"
            }`}
            title={isPaused ? "Resume auto-scroll" : "Pause auto-scroll"}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
          </button>

          {/* Clear Log */}
          {onClear && (
            <button
              onClick={onClear}
              className="p-1.5 bg-[#21262D] border border-[#30363D] text-slate-400 hover:text-red-400 hover:border-red-900 rounded"
              title="Clear event stream"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Search Input Filter */}
      <div className="px-3 py-1.5 bg-[#161B22] border-b border-[#30363D] flex items-center gap-2">
        <Search className="w-3.5 h-3.5 text-slate-500" />
        <input
          type="text"
          value={searchLayer}
          onChange={(e) => setSearchLayer(e.target.value)}
          placeholder="Filter by affected tensor layer or fault classification..."
          className="w-full bg-transparent text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none"
        />
        {searchLayer && (
          <button
            onClick={() => setSearchLayer("")}
            className="text-[10px] font-mono text-slate-400 hover:text-slate-200 px-1"
          >
            Clear
          </button>
        )}
      </div>

      {/* Scrolling Stream Content */}
      <div className="flex-1 min-h-[220px] max-h-[380px] overflow-y-auto p-2 space-y-1.5 font-mono text-xs select-text scrollbar-thin">
        {filteredEvents.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 text-xs py-8">
            No events match current filter. Stream awaiting telemetry events...
          </div>
        ) : (
          filteredEvents.map((evt) => (
            <div
              key={evt.id}
              className={`p-2 rounded border transition-colors ${
                evt.severity === "critical"
                  ? "bg-red-950/30 border-red-900/60 hover:bg-red-950/40"
                  : evt.severity === "recovery"
                  ? "bg-cyan-950/30 border-cyan-900/60 hover:bg-cyan-950/40"
                  : evt.severity === "warning"
                  ? "bg-amber-950/20 border-amber-900/50 hover:bg-amber-950/30"
                  : "bg-[#0D1117] border-[#30363D] hover:bg-[#1a202c]"
              }`}
            >
              <div className="flex items-center justify-between text-[11px] mb-1 gap-2">
                <div className="flex items-center gap-2 truncate">
                  {getSeverityBadge(evt.severity)}
                  {/* Millisecond precision timestamp */}
                  <span className="text-slate-400 text-[10px] whitespace-nowrap">
                    {evt.timestamp}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500">{evt.id}</span>
              </div>

              {/* Affected Tensor Layer */}
              <div className="flex items-baseline gap-2 text-[11px] my-0.5">
                <span className="text-slate-500 text-[10px]">TENSOR LAYER:</span>
                <span
                  className={`font-semibold ${
                    evt.affectedTensorLayer !== "None" &&
                    evt.affectedTensorLayer !== "All Layers Verified"
                      ? "text-cyan-300 bg-cyan-950/60 px-1 rounded border border-cyan-800/40"
                      : "text-slate-400"
                  }`}
                >
                  {evt.affectedTensorLayer}
                </span>
              </div>

              {/* Fault Classification Cause */}
              <div className="flex items-baseline gap-2 text-[11px] my-0.5">
                <span className="text-slate-500 text-[10px]">FAULT CAUSE:</span>
                <span
                  className={
                    evt.severity === "critical"
                      ? "text-red-300 font-bold"
                      : evt.severity === "recovery"
                      ? "text-cyan-300 font-bold"
                      : "text-amber-300"
                  }
                >
                  {evt.faultClassification}
                </span>
              </div>

              {/* Message */}
              <div className="text-[10px] text-slate-400 mt-1 leading-relaxed border-t border-[#30363D]/40 pt-1">
                {evt.message}
              </div>
            </div>
          ))
        )}
        <div ref={scrollEndRef} />
      </div>
    </div>
  );
}
