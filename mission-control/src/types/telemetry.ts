export type OperationalState =
  | "NOMINAL"
  | "INLINE_INVARIANT_BREACH"
  | "ACTUATOR_INHIBITED"
  | "RECOVERY_VERIFIED"
  | "SAFE_HOLD";

export interface Quaternion {
  w: number;
  x: number;
  y: number;
  z: number;
}

export interface AngularVelocity {
  x: number; // rad/s or deg/s
  y: number;
  z: number;
}

export interface LinearAcceleration {
  x: number; // m/s^2
  y: number;
  z: number;
}

export interface EulerAngles {
  roll: number;  // deg
  pitch: number; // deg
  yaw: number;   // deg
}

export interface ActuatorBusState {
  gatingPermitted: boolean;
  latchReason: string;
  interlockTriggered: boolean;
  rcsThrusters: {
    enabled: boolean;
    firingRateHz: number;
    thrustOutputN: number;
  };
  reactionWheels: {
    xRpm: number;
    yRpm: number;
    zRpm: number;
    saturationPct: number;
    inhibited: boolean;
  };
  magnetorquers: {
    bDotActive: boolean;
    dipoleCurrentA: number;
  };
  gimbalServos: {
    pitchDeg: number;
    yawDeg: number;
    locked: boolean;
  };
}

export interface TelemetryEvent {
  id: string;
  timestamp: string; // ISO string with ms precision
  epochMs: number;
  severity: "info" | "warning" | "error" | "recovery" | "critical";
  affectedTensorLayer: string;
  faultClassification: string;
  message: string;
}

export interface LatencyMetric {
  timestamp: string;
  epochMs: number;
  p50: number; // ms
  p95: number; // ms
  rawLatencyMs: number;
}

export interface KinematicMetric {
  timestamp: string;
  epochMs: number;
  ax: number;
  ay: number;
  az: number;
  alphaTotal: number; // rad/s^2
  angularRateMag: number; // deg/s
}

export interface SpacecraftTelemetry {
  timestamp: string;
  epochMs: number;
  state: OperationalState;
  quaternion: Quaternion;
  angularVelocity: AngularVelocity;
  linearAcceleration: LinearAcceleration;
  eulerAngles: EulerAngles;
  actuatorBus: ActuatorBusState;
  radiationFluxKrad: number;
  tensorHealthIndex: number; // 0.0 - 1.0 (1.0 = perfect weights)
  seuStrikesTotal: number;
  recoveryCyclesTotal: number;
  network: {
    activeUrl: string;
    backendStatus: "connected_primary" | "connected_fallback" | "simulated" | "disconnected";
    rttMs: number;
    packetCount: number;
    pollingMode: "POLLING" | "STREAMING";
  };
}

export interface OperatorCommandResponse {
  success: boolean;
  action: string;
  message: string;
  newState?: OperationalState;
  timestamp: string;
}
