import {
  SpacecraftTelemetry,
  OperationalState,
  TelemetryEvent,
  LatencyMetric,
  KinematicMetric,
  Quaternion,
  AngularVelocity,
  OperatorCommandResponse,
} from "@/types/telemetry";

// Default LAN target and fallback
const DEFAULT_PRIMARY =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const DEFAULT_FALLBACK =
  process.env.NEXT_PUBLIC_FALLBACK_URL || "http://localhost:8000";

// Simulation State
interface SimulationInternal {
  state: OperationalState;
  q: [number, number, number, number]; // [w, x, y, z]
  omega: [number, number, number]; // [wx, wy, wz] rad/s
  alpha: [number, number, number]; // [ax, ay, az] rad/s^2
  linearAcc: [number, number, number]; // m/s^2
  rwRpm: [number, number, number];
  bDotActive: boolean;
  tensorHealth: number;
  seuCount: number;
  recoveryCount: number;
  lastBreachLayer: string;
  lastFaultReason: string;
  gatingBarrierLocked: boolean;
  recoveryStartTime: number | null;
}

class TelemetryEngine {
  private primaryUrl: string = DEFAULT_PRIMARY;
  private fallbackUrl: string = DEFAULT_FALLBACK;
  private activeUrl: string = DEFAULT_PRIMARY;
  private connectionStatus:
    | "connected_primary"
    | "connected_fallback"
    | "simulated"
    | "disconnected" = "simulated";
  private pollingMode: "POLLING" | "STREAMING" = "STREAMING";
  private pollingIntervalMs: number = 50;
  private timer: NodeJS.Timeout | null = null;
  private ws: WebSocket | null = null;
  private listeners: ((telemetry: SpacecraftTelemetry) => void)[] = [];
  private eventListeners: ((event: TelemetryEvent) => void)[] = [];
  private latencyHistory: LatencyMetric[] = [];
  private kinematicHistory: KinematicMetric[] = [];
  private packetCounter: number = 0;
  private lastPingMs: number = 2.4;

  private sim: SimulationInternal = {
    state: "NOMINAL",
    q: [1.0, 0.0, 0.0, 0.0],
    omega: [0.005, -0.003, 0.002],
    alpha: [0.001, -0.001, 0.0005],
    linearAcc: [0.01, 0.02, 0.98],
    rwRpm: [1200, -850, 420],
    bDotActive: false,
    tensorHealth: 1.0,
    seuCount: 0,
    recoveryCount: 0,
    lastBreachLayer: "None",
    lastFaultReason: "System Nominal",
    gatingBarrierLocked: false,
    recoveryStartTime: null,
  };

  private candidateTensorLayers = [
    "block0.weight",
    "block1.weight",
    "block2.weight",
    "block3.weight",
    "head.quaternion_regressor.fc1.weight",
    "actuator_gating.boundary_clamp.weight",
  ];

  private faultReasons = [
    "Single Event Upset (SEU) in Bit 14 (Bitflip detected)",
    "Tensor Norm Invariant Divergence (||W|| > Lambda_max)",
    "NaN/Inf activation gradient detected in Layer 3",
    "Quaternion Regressor Unnormalized State (||q|| != 1.0)",
    "Tier 1 Invariant Tripwire Breach: Non-finite value in activations",
    "Tier 2 Rigid-Body Kinematic Limit Exceeded (||tau|| > tau_max)",
  ];

  constructor() {
    this.initHistory();
  }

  private initHistory() {
    const now = Date.now();
    for (let i = 25; i >= 0; i--) {
      const t = now - i * 1000;
      const iso = new Date(t).toISOString();
      const p50 = 3.8 + Math.sin(i * 0.4) * 0.8 + Math.random() * 0.4;
      const p95 = 8.2 + Math.cos(i * 0.3) * 1.5 + Math.random() * 0.9;
      this.latencyHistory.push({
        timestamp: iso.substring(11, 23),
        epochMs: t,
        p50: parseFloat(p50.toFixed(2)),
        p95: parseFloat(p95.toFixed(2)),
        rawLatencyMs: parseFloat((p50 + Math.random() * 2).toFixed(2)),
      });

      this.kinematicHistory.push({
        timestamp: iso.substring(11, 23),
        epochMs: t,
        ax: parseFloat((Math.sin(i * 0.3) * 0.15).toFixed(3)),
        ay: parseFloat((Math.cos(i * 0.25) * 0.12).toFixed(3)),
        az: parseFloat((0.98 + Math.sin(i * 0.1) * 0.05).toFixed(3)),
        alphaTotal: parseFloat((0.02 + Math.random() * 0.015).toFixed(4)),
        angularRateMag: parseFloat((0.45 + Math.random() * 0.1).toFixed(2)),
      });
    }
  }

  public getPrimaryUrl(): string {
    return this.primaryUrl;
  }

  public getActiveUrl(): string {
    return this.activeUrl;
  }

  public getConnectionStatus() {
    return this.connectionStatus;
  }

  public setBackendUrl(url: string) {
    this.primaryUrl = url.trim();
    this.checkConnection();
  }

  public setPollingMode(mode: "POLLING" | "STREAMING") {
    this.pollingMode = mode;
    this.pollingIntervalMs = mode === "STREAMING" ? 50 : 250;
    this.restartLoop();
  }

  public getPollingMode(): "POLLING" | "STREAMING" {
    return this.pollingMode;
  }

  public subscribe(listener: (telemetry: SpacecraftTelemetry) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  public subscribeEvents(listener: (event: TelemetryEvent) => void): () => void {
    this.eventListeners.push(listener);
    return () => {
      this.eventListeners = this.eventListeners.filter((l) => l !== listener);
    };
  }

  public getLatencyHistory(): LatencyMetric[] {
    return this.latencyHistory;
  }

  public getKinematicHistory(): KinematicMetric[] {
    return this.kinematicHistory;
  }

  public start() {
    if (this.timer) return;
    this.checkConnection();
    this.restartLoop();
  }

  public stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private restartLoop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = setInterval(() => {
      this.tick();
    }, this.pollingIntervalMs);
  }

  private async checkConnection() {
    // Attempt pinging primary GPU node first
    try {
      const start = performance.now();
      const res = await fetch(`${this.primaryUrl}/api/state`, {
        method: "GET",
        signal: AbortSignal.timeout(1200),
      });
      if (res.ok) {
        this.activeUrl = this.primaryUrl;
        this.connectionStatus = "connected_primary";
        this.lastPingMs = Math.round(performance.now() - start);
        this.connectWebSocket();
        return;
      }
    } catch {
      // Fallback check: localhost:8000
      try {
        const start = performance.now();
        const resFallback = await fetch(`${this.fallbackUrl}/api/state`, {
          method: "GET",
          signal: AbortSignal.timeout(1200),
        });
        if (resFallback.ok) {
          this.activeUrl = this.fallbackUrl;
          this.connectionStatus = "connected_fallback";
          this.lastPingMs = Math.round(performance.now() - start);
          this.connectWebSocket();
          return;
        }
      } catch {
        // Fallback to internal high-fidelity simulation engine
        this.activeUrl = "IN-SITU SIMULATOR (LAN Standby)";
        this.connectionStatus = "simulated";
        this.lastPingMs = 1.2;
      }
    }
  }

  private connectWebSocket() {
    if (typeof window === "undefined") return;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (!this.connectionStatus.startsWith("connected")) return;

    try {
      const wsUrl = this.activeUrl.replace(/^http/, "ws") + "/ws/telemetry";
      const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);
          this.handleBackendPacket(raw);
        } catch {
          // ignore malformed
        }
      };

      ws.onerror = () => {
        // will fallback to polling
      };

      this.ws = ws;
    } catch {
      // fallback
    }
  }

  private handleBackendPacket(raw: any) {
    this.packetCounter++;
    const now = Date.now();

    // Convert RadZero SystemState: NOMINAL, FAULT_ACTIVE, RECOVERY_VERIFIED, SAFE_HOLD
    let mappedState: OperationalState = "NOMINAL";
    if (raw.state === "FAULT_ACTIVE" || !raw.tier1_passed || !raw.tier2_passed) {
      mappedState = "INLINE_INVARIANT_BREACH";
    } else if (raw.state === "ACTUATOR_INHIBITED") {
      mappedState = "ACTUATOR_INHIBITED";
    } else if (raw.state === "SAFE_HOLD" || raw.safe_hold_active) {
      mappedState = "SAFE_HOLD";
    } else if (raw.state === "RECOVERY_VERIFIED") {
      mappedState = "RECOVERY_VERIFIED";
    }

    const q: [number, number, number, number] = raw.quaternion || [1, 0, 0, 0];
    const omega: [number, number, number] = raw.angular_velocity || [0, 0, 0];
    const alpha: [number, number, number] = raw.angular_accel || [0, 0, 0];
    const euler = this.quaternionToEuler(q);

    const isActuatorInhibited =
      mappedState === "INLINE_INVARIANT_BREACH" ||
      mappedState === "ACTUATOR_INHIBITED" ||
      !raw.tier2_passed;

    const recoveryMs = raw.recovery_latency_system_ms || 3.8;
    const isoTime = new Date(now).toISOString().substring(11, 23);

    // Update latency & kinematics history
    if (this.packetCounter % 5 === 0) {
      this.latencyHistory.push({
        timestamp: isoTime,
        epochMs: now,
        p50: parseFloat(recoveryMs.toFixed(2)),
        p95: parseFloat((recoveryMs * 1.8).toFixed(2)),
        rawLatencyMs: parseFloat(this.lastPingMs.toFixed(2)),
      });
      if (this.latencyHistory.length > 30) this.latencyHistory.shift();

      const alphaMag = Math.sqrt(alpha[0] ** 2 + alpha[1] ** 2 + alpha[2] ** 2);
      const rateMag =
        Math.sqrt(omega[0] ** 2 + omega[1] ** 2 + omega[2] ** 2) * (180 / Math.PI);
      this.kinematicHistory.push({
        timestamp: isoTime,
        epochMs: now,
        ax: parseFloat((raw.torque_cmd?.[0] || 0.01).toFixed(3)),
        ay: parseFloat((raw.torque_cmd?.[1] || 0.02).toFixed(3)),
        az: parseFloat((raw.torque_cmd?.[2] || 0.98).toFixed(3)),
        alphaTotal: parseFloat(alphaMag.toFixed(4)),
        angularRateMag: parseFloat(rateMag.toFixed(2)),
      });
      if (this.kinematicHistory.length > 30) this.kinematicHistory.shift();
    }

    const telemetry: SpacecraftTelemetry = {
      timestamp: new Date(now).toISOString(),
      epochMs: now,
      state: mappedState,
      quaternion: { w: q[0], x: q[1], y: q[2], z: q[3] },
      angularVelocity: { x: omega[0], y: omega[1], z: omega[2] },
      linearAcceleration: {
        x: raw.torque_cmd?.[0] || 0.01,
        y: raw.torque_cmd?.[1] || 0.02,
        z: raw.torque_cmd?.[2] || 0.98,
      },
      eulerAngles: euler,
      actuatorBus: {
        gatingPermitted: !isActuatorInhibited,
        latchReason: isActuatorInhibited
          ? raw.last_breach || "Tier 1/2 Invariant Safety Breach"
          : "Permitted - Lyapunov Safe Invariant Satisfied",
        interlockTriggered: isActuatorInhibited,
        rcsThrusters: {
          enabled: !isActuatorInhibited,
          firingRateHz: isActuatorInhibited ? 0 : 4.2,
          thrustOutputN: isActuatorInhibited ? 0 : 12.5,
        },
        reactionWheels: {
          xRpm: Math.round((raw.momentum_storage?.[0] || 0) * 12000),
          yRpm: Math.round((raw.momentum_storage?.[1] || 0) * 12000),
          zRpm: Math.round((raw.momentum_storage?.[2] || 0) * 12000),
          saturationPct: Math.round(
            (Math.abs(raw.momentum_storage?.[0] || 0) / 0.1) * 100
          ),
          inhibited: isActuatorInhibited,
        },
        magnetorquers: {
          bDotActive: raw.safe_hold_active,
          dipoleCurrentA: raw.safe_hold_active ? 1.85 : 0.05,
        },
        gimbalServos: {
          pitchDeg: isActuatorInhibited ? 0 : parseFloat((euler.pitch * 0.4).toFixed(1)),
          yawDeg: isActuatorInhibited ? 0 : parseFloat((euler.yaw * 0.4).toFixed(1)),
          locked: isActuatorInhibited,
        },
      },
      radiationFluxKrad: mappedState === "INLINE_INVARIANT_BREACH" ? 142.8 : 28.4,
      tensorHealthIndex: isActuatorInhibited ? 0.35 : 1.0,
      seuStrikesTotal: raw.recovery_count > 0 ? raw.recovery_count + 1 : 0,
      recoveryCyclesTotal: raw.recovery_count || 0,
      network: {
        activeUrl: this.activeUrl,
        backendStatus: this.connectionStatus,
        rttMs: this.lastPingMs,
        packetCount: this.packetCounter,
        pollingMode: this.pollingMode,
      },
    };

    this.listeners.forEach((listener) => listener(telemetry));
  }

  // --- Operator Actions ---
  public async injectSEU(): Promise<OperatorCommandResponse> {
    const timestamp = new Date().toISOString();
    const randomLayer =
      this.candidateTensorLayers[
        Math.floor(Math.random() * this.candidateTensorLayers.length)
      ];
    const randomFault =
      this.faultReasons[Math.floor(Math.random() * this.faultReasons.length)];

    if (this.connectionStatus.startsWith("connected")) {
      try {
        const res = await fetch(`${this.activeUrl}/api/inject_seu`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ layer: randomLayer, target: "EXPONENT_EXPLODE" }),
        });
        if (res.ok) {
          const data = await res.json();
          const event: TelemetryEvent = {
            id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
            timestamp,
            epochMs: Date.now(),
            severity: "critical",
            affectedTensorLayer: randomLayer,
            faultClassification: "Single Event Upset (SEU) IEEE-754 Mutation",
            message: `CRITICAL: Exponent bitflip injected into ${randomLayer}. Invariant tripwire engaged.`,
          };
          this.emitEvent(event);
          return {
            success: true,
            action: "INJECT_SEU",
            message: `SEU strike injected into ${randomLayer}. Actuators inhibited.`,
            newState: "INLINE_INVARIANT_BREACH",
            timestamp,
          };
        }
      } catch {
        // Fallback
      }
    }

    // Local Simulation
    this.sim.state = "INLINE_INVARIANT_BREACH";
    this.sim.gatingBarrierLocked = true;
    this.sim.tensorHealth = Math.max(0.12, this.sim.tensorHealth - 0.45);
    this.sim.seuCount += 1;
    this.sim.lastBreachLayer = randomLayer;
    this.sim.lastFaultReason = randomFault;

    this.sim.omega[0] += (Math.random() - 0.5) * 1.8;
    this.sim.omega[1] += (Math.random() - 0.5) * 1.8;
    this.sim.omega[2] += (Math.random() - 0.5) * 1.8;

    this.sim.alpha[0] = (Math.random() - 0.5) * 0.4;
    this.sim.alpha[1] = (Math.random() - 0.5) * 0.4;
    this.sim.alpha[2] = (Math.random() - 0.5) * 0.4;

    const event: TelemetryEvent = {
      id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
      timestamp,
      epochMs: Date.now(),
      severity: "critical",
      affectedTensorLayer: randomLayer,
      faultClassification: randomFault,
      message: `CRITICAL: Invariant breach detected in ${randomLayer}. Hardware interlock engaged: Actuators Clamped.`,
    };
    this.emitEvent(event);

    return {
      success: true,
      action: "INJECT_SEU",
      message: `SEU strike injected into ${randomLayer}. Invariant breach verified. Actuators inhibited.`,
      newState: "INLINE_INVARIANT_BREACH",
      timestamp,
    };
  }

  public async triggerRecovery(): Promise<OperatorCommandResponse> {
    const timestamp = new Date().toISOString();

    if (this.connectionStatus.startsWith("connected")) {
      try {
        const res = await fetch(`${this.activeUrl}/api/reset`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        if (res.ok) {
          const event: TelemetryEvent = {
            id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
            timestamp,
            epochMs: Date.now(),
            severity: "recovery",
            affectedTensorLayer: "All Tensor Blocks Restored",
            faultClassification: "In-Situ Hot Patching Complete",
            message: `IN-SITU RECOVERY: Tensors hot-patched from shadow mirrors. Zero process termination verified.`,
          };
          this.emitEvent(event);
          return {
            success: true,
            action: "TRIGGER_RECOVERY",
            message: "In-situ self-healing verified on GPU node. Spacecraft attitude re-stabilized.",
            newState: "RECOVERY_VERIFIED",
            timestamp,
          };
        }
      } catch {
        // fallback
      }
    }

    // Local Simulation
    this.sim.recoveryStartTime = Date.now();
    this.sim.state = "RECOVERY_VERIFIED";
    this.sim.recoveryCount += 1;
    this.sim.tensorHealth = 0.995;
    this.sim.gatingBarrierLocked = false;
    this.sim.bDotActive = true;

    const event: TelemetryEvent = {
      id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
      timestamp,
      epochMs: Date.now(),
      severity: "recovery",
      affectedTensorLayer: this.sim.lastBreachLayer,
      faultClassification: "In-Situ Checkpoint Projection & SVD Clamp",
      message: `IN-SITU RECOVERY: Tensor checkpoint re-projected onto safe invariant manifold. Actuators uninhibited. Rate damping active.`,
    };
    this.emitEvent(event);

    return {
      success: true,
      action: "TRIGGER_RECOVERY",
      message:
        "In-situ self-healing verified. Tensor layers restored. Spacecraft executing rate-damping re-alignment.",
      newState: "RECOVERY_VERIFIED",
      timestamp,
    };
  }

  public async engageSafeHold(): Promise<OperatorCommandResponse> {
    const timestamp = new Date().toISOString();

    if (this.connectionStatus.startsWith("connected")) {
      try {
        const res = await fetch(`${this.activeUrl}/api/corrupt_mirror`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ param_name: "block0.weight", corrupt_backup: true }),
        });
        if (res.ok) {
          const event: TelemetryEvent = {
            id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
            timestamp,
            epochMs: Date.now(),
            severity: "warning",
            affectedTensorLayer: "Autonomous Guidance Escalate",
            faultClassification: "SAFE_HOLD Escalation Triggered",
            message: `SAFE-HOLD ENGAGED: Proportional rate damping tau = -Kd * omega active on spacecraft.`,
          };
          this.emitEvent(event);
          return {
            success: true,
            action: "ENGAGE_SAFE_HOLD",
            message: "Spacecraft escalated to Safe-Hold mode.",
            newState: "SAFE_HOLD",
            timestamp,
          };
        }
      } catch {
        // fallback
      }
    }

    this.sim.state = "SAFE_HOLD";
    this.sim.bDotActive = true;
    this.sim.gatingBarrierLocked = true;

    const event: TelemetryEvent = {
      id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
      timestamp,
      epochMs: Date.now(),
      severity: "warning",
      affectedTensorLayer: "Autonomous Guidance Override",
      faultClassification: "Operator Initiated Safe-Hold",
      message: `SAFE-HOLD ENGAGED: B-Dot magnetorquer rate-damping active. Solar array locked to Sun-pointing vector.`,
    };
    this.emitEvent(event);

    return {
      success: true,
      action: "ENGAGE_SAFE_HOLD",
      message: "Spacecraft transitioned to Safe-Hold mode. Rate damping engaged.",
      newState: "SAFE_HOLD",
      timestamp,
    };
  }

  public resetToNominal(): void {
    const timestamp = new Date().toISOString();
    this.sim.state = "NOMINAL";
    this.sim.tensorHealth = 1.0;
    this.sim.gatingBarrierLocked = false;
    this.sim.bDotActive = false;
    this.sim.omega = [0.005, -0.002, 0.003];
    this.sim.alpha = [0.001, -0.0005, 0.0008];
    this.sim.lastBreachLayer = "None";
    this.sim.lastFaultReason = "System Nominal";

    const event: TelemetryEvent = {
      id: "EVT-" + Math.random().toString(36).substring(2, 9).toUpperCase(),
      timestamp,
      epochMs: Date.now(),
      severity: "info",
      affectedTensorLayer: "All Layers Verified",
      faultClassification: "Lyapunov Basin Restored",
      message:
        "SYSTEM RESTORED: Spacecraft attitude locked in celestial tracking nominal mode.",
    };
    this.emitEvent(event);
  }

  private emitEvent(event: TelemetryEvent) {
    this.eventListeners.forEach((listener) => listener(event));
  }

  private async tick() {
    // If polling mode is active and connected, fetch latest telemetry
    if (
      this.connectionStatus.startsWith("connected") &&
      this.pollingMode === "POLLING"
    ) {
      try {
        const res = await fetch(`${this.activeUrl}/api/telemetry/latest`);
        if (res.ok) {
          const raw = await res.json();
          this.handleBackendPacket(raw);
          return;
        }
      } catch {
        // fallback to simulation tick
      }
    }

    // If WebSocket is actively receiving, let ws message handler tick
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    // Otherwise run high-fidelity internal physics simulator
    this.packetCounter++;
    const dt = this.pollingIntervalMs / 1000.0;
    const now = Date.now();

    if (this.sim.state === "INLINE_INVARIANT_BREACH") {
      this.sim.omega[0] += (Math.random() - 0.49) * 0.15;
      this.sim.omega[1] += (Math.random() - 0.51) * 0.15;
      this.sim.omega[2] += (Math.random() - 0.48) * 0.15;

      this.sim.alpha[0] = this.sim.omega[0] * 1.4;
      this.sim.alpha[1] = this.sim.omega[1] * 1.4;
      this.sim.alpha[2] = this.sim.omega[2] * 1.4;
      this.sim.linearAcc[0] = (Math.random() - 0.5) * 1.2;
      this.sim.linearAcc[1] = (Math.random() - 0.5) * 1.2;
      this.sim.linearAcc[2] = 0.98 + (Math.random() - 0.5) * 0.8;

      this.sim.rwRpm[0] = Math.min(6000, this.sim.rwRpm[0] + 45);
      this.sim.rwRpm[1] = Math.max(-6000, this.sim.rwRpm[1] - 50);
      this.sim.rwRpm[2] = Math.min(6000, this.sim.rwRpm[2] + 40);
    } else if (
      this.sim.state === "SAFE_HOLD" ||
      this.sim.state === "RECOVERY_VERIFIED"
    ) {
      const dampingFactor = 0.92;
      this.sim.omega[0] *= dampingFactor;
      this.sim.omega[1] *= dampingFactor;
      this.sim.omega[2] *= dampingFactor;

      this.sim.alpha[0] *= 0.88;
      this.sim.alpha[1] *= 0.88;
      this.sim.alpha[2] *= 0.88;

      this.sim.linearAcc[0] += (0.0 - this.sim.linearAcc[0]) * 0.1;
      this.sim.linearAcc[1] += (0.0 - this.sim.linearAcc[1]) * 0.1;
      this.sim.linearAcc[2] += (0.98 - this.sim.linearAcc[2]) * 0.1;

      this.sim.rwRpm[0] *= 0.95;
      this.sim.rwRpm[1] *= 0.95;
      this.sim.rwRpm[2] *= 0.95;

      const rateMag = Math.sqrt(
        this.sim.omega[0] ** 2 + this.sim.omega[1] ** 2 + this.sim.omega[2] ** 2
      );
      if (rateMag < 0.04 && this.sim.state === "RECOVERY_VERIFIED") {
        this.sim.state = "NOMINAL";
        this.sim.bDotActive = false;
        this.sim.gatingBarrierLocked = false;
      }
    } else {
      const tSec = now / 1000.0;
      this.sim.omega[0] = 0.004 * Math.sin(tSec * 0.2);
      this.sim.omega[1] = 0.003 * Math.cos(tSec * 0.25);
      this.sim.omega[2] = 0.002 * Math.sin(tSec * 0.15);

      this.sim.alpha[0] = 0.0008 * Math.cos(tSec * 0.2);
      this.sim.alpha[1] = -0.0006 * Math.sin(tSec * 0.25);
      this.sim.alpha[2] = 0.0004 * Math.cos(tSec * 0.15);

      this.sim.linearAcc[0] = 0.01 * Math.sin(tSec * 0.5);
      this.sim.linearAcc[1] = 0.02 * Math.cos(tSec * 0.4);
      this.sim.linearAcc[2] = 0.981 + 0.005 * Math.sin(tSec * 0.3);

      this.sim.rwRpm[0] = 1200 + 150 * Math.sin(tSec * 0.1);
      this.sim.rwRpm[1] = -850 + 120 * Math.cos(tSec * 0.12);
      this.sim.rwRpm[2] = 420 + 80 * Math.sin(tSec * 0.08);
    }

    const [qw, qx, qy, qz] = this.sim.q;
    const [wx, wy, wz] = this.sim.omega;

    const dqw = 0.5 * (-qx * wx - qy * wy - qz * wz);
    const dqx = 0.5 * (qw * wx + qy * wz - qz * wy);
    const dqy = 0.5 * (qw * wy - qx * wz + qz * wx);
    const dqz = 0.5 * (qw * wz + qx * wy - qy * wx);

    let nqw = qw + dqw * dt;
    let nqx = qx + dqx * dt;
    let nqy = qy + dqy * dt;
    let nqz = qz + dqz * dt;

    const norm =
      Math.sqrt(nqw * nqw + nqx * nqx + nqy * nqy + nqz * nqz) || 1.0;
    this.sim.q = [nqw / norm, nqx / norm, nqy / norm, nqz / norm];

    const euler = this.quaternionToEuler(this.sim.q);

    const alphaMag = Math.sqrt(
      this.sim.alpha[0] ** 2 + this.sim.alpha[1] ** 2 + this.sim.alpha[2] ** 2
    );
    const rateMagDeg =
      Math.sqrt(
        this.sim.omega[0] ** 2 + this.sim.omega[1] ** 2 + this.sim.omega[2] ** 2
      ) *
      (180 / Math.PI);

    if (this.packetCounter % 5 === 0) {
      const isoTime = new Date(now).toISOString().substring(11, 23);
      const isBreach = this.sim.state === "INLINE_INVARIANT_BREACH";
      const p50 = isBreach
        ? 12.4 + Math.random() * 4.2
        : 3.6 + Math.random() * 0.8;
      const p95 = isBreach
        ? 34.8 + Math.random() * 9.5
        : 7.9 + Math.random() * 1.8;

      this.latencyHistory.push({
        timestamp: isoTime,
        epochMs: now,
        p50: parseFloat(p50.toFixed(2)),
        p95: parseFloat(p95.toFixed(2)),
        rawLatencyMs: parseFloat(
          (this.lastPingMs + (isBreach ? 15 : 0)).toFixed(2)
        ),
      });
      if (this.latencyHistory.length > 30) this.latencyHistory.shift();

      this.kinematicHistory.push({
        timestamp: isoTime,
        epochMs: now,
        ax: parseFloat(this.sim.linearAcc[0].toFixed(3)),
        ay: parseFloat(this.sim.linearAcc[1].toFixed(3)),
        az: parseFloat(this.sim.linearAcc[2].toFixed(3)),
        alphaTotal: parseFloat(alphaMag.toFixed(4)),
        angularRateMag: parseFloat(rateMagDeg.toFixed(2)),
      });
      if (this.kinematicHistory.length > 30) this.kinematicHistory.shift();
    }

    const isActuatorInhibited =
      this.sim.state === "INLINE_INVARIANT_BREACH" ||
      this.sim.state === "ACTUATOR_INHIBITED" ||
      this.sim.gatingBarrierLocked;

    const telemetry: SpacecraftTelemetry = {
      timestamp: new Date(now).toISOString(),
      epochMs: now,
      state: this.sim.state,
      quaternion: {
        w: this.sim.q[0],
        x: this.sim.q[1],
        y: this.sim.q[2],
        z: this.sim.q[3],
      },
      angularVelocity: {
        x: this.sim.omega[0],
        y: this.sim.omega[1],
        z: this.sim.omega[2],
      },
      linearAcceleration: {
        x: this.sim.linearAcc[0],
        y: this.sim.linearAcc[1],
        z: this.sim.linearAcc[2],
      },
      eulerAngles: euler,
      actuatorBus: {
        gatingPermitted: !isActuatorInhibited,
        latchReason: isActuatorInhibited
          ? this.sim.lastFaultReason
          : "Permitted - Lyapunov Safe Invariant Satisfied",
        interlockTriggered: isActuatorInhibited,
        rcsThrusters: {
          enabled: !isActuatorInhibited,
          firingRateHz: isActuatorInhibited ? 0 : 4.2,
          thrustOutputN: isActuatorInhibited ? 0 : 12.5,
        },
        reactionWheels: {
          xRpm: Math.round(this.sim.rwRpm[0]),
          yRpm: Math.round(this.sim.rwRpm[1]),
          zRpm: Math.round(this.sim.rwRpm[2]),
          saturationPct: Math.round(
            (Math.max(
              Math.abs(this.sim.rwRpm[0]),
              Math.abs(this.sim.rwRpm[1]),
              Math.abs(this.sim.rwRpm[2])
            ) /
              6000) *
              100
          ),
          inhibited: isActuatorInhibited,
        },
        magnetorquers: {
          bDotActive: this.sim.bDotActive,
          dipoleCurrentA: this.sim.bDotActive ? 1.85 : 0.05,
        },
        gimbalServos: {
          pitchDeg: isActuatorInhibited
            ? 0
            : parseFloat((euler.pitch * 0.4).toFixed(1)),
          yawDeg: isActuatorInhibited
            ? 0
            : parseFloat((euler.yaw * 0.4).toFixed(1)),
          locked: isActuatorInhibited,
        },
      },
      radiationFluxKrad:
        this.sim.state === "INLINE_INVARIANT_BREACH" ? 142.8 : 28.4,
      tensorHealthIndex: parseFloat(this.sim.tensorHealth.toFixed(3)),
      seuStrikesTotal: this.sim.seuCount,
      recoveryCyclesTotal: this.sim.recoveryCount,
      network: {
        activeUrl: this.activeUrl,
        backendStatus: this.connectionStatus,
        rttMs: this.lastPingMs,
        packetCount: this.packetCounter,
        pollingMode: this.pollingMode,
      },
    };

    this.listeners.forEach((listener) => listener(telemetry));
  }

  private quaternionToEuler(q: [number, number, number, number]): {
    roll: number;
    pitch: number;
    yaw: number;
  } {
    const [w, x, y, z] = q;

    const sinr_cosp = 2 * (w * x + y * z);
    const cosr_cosp = 1 - 2 * (x * x + y * y);
    const roll = Math.atan2(sinr_cosp, cosr_cosp) * (180 / Math.PI);

    const sinp = 2 * (w * y - z * x);
    let pitch: number;
    if (Math.abs(sinp) >= 1) {
      pitch = ((Math.sign(sinp) * Math.PI) / 2) * (180 / Math.PI);
    } else {
      pitch = Math.asin(sinp) * (180 / Math.PI);
    }

    const siny_cosp = 2 * (w * z + x * y);
    const cosy_cosp = 1 - 2 * (y * y + z * z);
    const yaw = Math.atan2(siny_cosp, cosy_cosp) * (180 / Math.PI);

    return {
      roll: parseFloat(roll.toFixed(1)),
      pitch: parseFloat(pitch.toFixed(1)),
      yaw: parseFloat(yaw.toFixed(1)),
    };
  }
}

export const telemetryClient = new TelemetryEngine();
