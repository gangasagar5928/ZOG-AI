"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { SpacecraftTelemetry, OperationalState } from "@/types/telemetry";
import {
  Compass,
  Layers,
  RotateCcw,
  Maximize2,
  AlertTriangle,
  ShieldCheck,
  Zap,
} from "lucide-react";

interface AttitudeVisualizerProps {
  telemetry: SpacecraftTelemetry | null;
}

export default function AttitudeVisualizer({ telemetry }: AttitudeVisualizerProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const spacecraftGroupRef = useRef<THREE.Group | null>(null);
  const omegaArrowRef = useRef<THREE.ArrowHelper | null>(null);
  const auraRingRef = useRef<THREE.Mesh | null>(null);
  const starsRef = useRef<THREE.Points | null>(null);
  const gridHelperRef = useRef<THREE.GridHelper | null>(null);

  const [wireframe, setWireframe] = useState<boolean>(false);
  const [showAxes, setShowAxes] = useState<boolean>(true);
  const [showHorizon, setShowHorizon] = useState<boolean>(true);
  const [cameraDistance, setCameraDistance] = useState<number>(4.2);

  // Fallback / default values
  const q = telemetry?.quaternion || { w: 1, x: 0, y: 0, z: 0 };
  const omega = telemetry?.angularVelocity || { x: 0, y: 0, z: 0 };
  const euler = telemetry?.eulerAngles || { roll: 0, pitch: 0, yaw: 0 };
  const state: OperationalState = telemetry?.state || "NOMINAL";

  const qNorm = Math.sqrt(q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z);
  const omegaMag = Math.sqrt(omega.x * omega.x + omega.y * omega.y + omega.z * omega.z);
  const omegaMagDeg = (omegaMag * (180 / Math.PI)).toFixed(2);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene Setup
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e14);
    sceneRef.current = scene;

    // 2. Camera Setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(2.8, 2.2, 3.8);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 3. Renderer Setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
    sunLight.position.set(10, 15, 8);
    scene.add(sunLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.8);
    rimLight.position.set(-10, -5, -10);
    scene.add(rimLight);

    // 5. Starfield Background
    const starGeometry = new THREE.BufferGeometry();
    const starCount = 800;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 80;
      starPositions[i + 1] = (Math.random() - 0.5) * 80;
      starPositions[i + 2] = (Math.random() - 0.5) * 80;
    }
    starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    const starMaterial = new THREE.PointsMaterial({
      color: 0x8b949e,
      size: 0.18,
      transparent: true,
      opacity: 0.7,
    });
    const stars = new THREE.Points(starGeometry, starMaterial);
    scene.add(stars);
    starsRef.current = stars;

    // 6. Orbital / Celestial Reference Grid
    const grid = new THREE.GridHelper(12, 24, 0x30363d, 0x161b22);
    grid.position.y = -1.5;
    scene.add(grid);
    gridHelperRef.current = grid;

    // 7. Spacecraft Model Group
    const spacecraftGroup = new THREE.Group();
    scene.add(spacecraftGroup);
    spacecraftGroupRef.current = spacecraftGroup;

    // --- Build High-Fidelity Spacecraft Model ---
    // Central Bus (Satellite Body)
    const busGeo = new THREE.BoxGeometry(0.9, 1.3, 0.9);
    const busMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.85,
      roughness: 0.25,
      wireframe: false,
    });
    const bus = new THREE.Mesh(busGeo, busMat);
    bus.name = "bus";
    spacecraftGroup.add(bus);

    // Gold Multi-Layer Insulation (MLI) Facets
    const mliGeo = new THREE.BoxGeometry(0.92, 0.5, 0.92);
    const mliMat = new THREE.MeshStandardMaterial({
      color: 0xd97706,
      metalness: 0.95,
      roughness: 0.3,
    });
    const mli = new THREE.Mesh(mliGeo, mliMat);
    mli.position.y = -0.2;
    spacecraftGroup.add(mli);

    // Solar Array Booms & Panels (Port and Starboard)
    const panelGeo = new THREE.BoxGeometry(1.4, 0.04, 0.65);
    const panelMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      metalness: 0.7,
      roughness: 0.2,
      emissive: 0x0369a1,
      emissiveIntensity: 0.2,
    });

    // Port Panel
    const portPanel = new THREE.Mesh(panelGeo, panelMat);
    portPanel.position.set(1.4, 0, 0);
    spacecraftGroup.add(portPanel);

    // Starboard Panel
    const stbdPanel = new THREE.Mesh(panelGeo, panelMat);
    stbdPanel.position.set(-1.4, 0, 0);
    spacecraftGroup.add(stbdPanel);

    // High-Gain Parabolic Antenna (Nadir pointing)
    const dishGeo = new THREE.CylinderGeometry(0.45, 0.05, 0.2, 24, 1, true);
    const dishMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0,
      metalness: 0.9,
      roughness: 0.2,
      side: THREE.DoubleSide,
    });
    const dish = new THREE.Mesh(dishGeo, dishMat);
    dish.position.set(0, 0.75, 0);
    dish.rotation.x = Math.PI;
    spacecraftGroup.add(dish);

    // Antenna Feed Horn
    const feedGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.28, 8);
    const feedMat = new THREE.MeshStandardMaterial({ color: 0xef4444 });
    const feed = new THREE.Mesh(feedGeo, feedMat);
    feed.position.set(0, 0.9, 0);
    spacecraftGroup.add(feed);

    // Thruster Clusters (4 corners at base)
    const thrusterGeo = new THREE.ConeGeometry(0.08, 0.16, 12);
    const thrusterMat = new THREE.MeshStandardMaterial({
      color: 0x64748b,
      metalness: 0.9,
    });
    const corners = [
      [0.35, -0.7, 0.35],
      [-0.35, -0.7, 0.35],
      [0.35, -0.7, -0.35],
      [-0.35, -0.7, -0.35],
    ];
    corners.forEach(([x, y, z]) => {
      const nozzle = new THREE.Mesh(thrusterGeo, thrusterMat);
      nozzle.position.set(x, y, z);
      nozzle.rotation.x = Math.PI;
      spacecraftGroup.add(nozzle);
    });

    // Gimbal / Attitude Reference Rings
    const ringMatYaw = new THREE.LineBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.45,
    });
    const ringMatPitch = new THREE.LineBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.45,
    });
    const ringMatRoll = new THREE.LineBasicMaterial({
      color: 0xf59e0b,
      transparent: true,
      opacity: 0.45,
    });

    const ringGeo = new THREE.BufferGeometry();
    const ringPoints: THREE.Vector3[] = [];
    const segments = 64;
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2;
      ringPoints.push(new THREE.Vector3(Math.cos(theta) * 2.2, 0, Math.sin(theta) * 2.2));
    }
    ringGeo.setFromPoints(ringPoints);

    const yawRing = new THREE.Line(ringGeo, ringMatYaw);
    scene.add(yawRing);

    const pitchRing = new THREE.Line(ringGeo, ringMatPitch);
    pitchRing.rotation.z = Math.PI / 2;
    scene.add(pitchRing);

    const rollRing = new THREE.Line(ringGeo, ringMatRoll);
    rollRing.rotation.x = Math.PI / 2;
    scene.add(rollRing);

    // Threat / Aura Glow Torus
    const auraGeo = new THREE.TorusGeometry(1.8, 0.04, 16, 64);
    const auraMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.5,
    });
    const aura = new THREE.Mesh(auraGeo, auraMat);
    aura.rotation.x = Math.PI / 2;
    spacecraftGroup.add(aura);
    auraRingRef.current = aura;

    // Angular Velocity Vector Arrow (starts along Y)
    const arrowDir = new THREE.Vector3(0, 1, 0);
    const arrow = new THREE.ArrowHelper(
      arrowDir,
      new THREE.Vector3(0, 0, 0),
      1.5,
      0x38bdf8,
      0.3,
      0.2
    );
    scene.add(arrow);
    omegaArrowRef.current = arrow;

    // Animation Loop
    let animId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Slow drift for background stars
      if (starsRef.current) {
        starsRef.current.rotation.y = elapsed * 0.015;
      }

      // Render
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    };
    animate();

    // Resize Handler
    const handleResize = () => {
      if (!container || !rendererRef.current || !cameraRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      if (rendererRef.current?.domElement) {
        rendererRef.current.dispose();
      }
    };
  }, []);

  // Update Spacecraft Transform & Visual States based on Live Telemetry
  useEffect(() => {
    if (!spacecraftGroupRef.current) return;

    // 1. Direct Quaternion Mapping: Three.js uses (x, y, z, w)
    const threeQuat = new THREE.Quaternion(q.x, q.y, q.z, q.w).normalize();
    spacecraftGroupRef.current.quaternion.copy(threeQuat);

    // 2. Angular Velocity Vector Arrow Update
    if (omegaArrowRef.current) {
      const omegaVec = new THREE.Vector3(omega.x, omega.y, omega.z);
      const mag = omegaVec.length();
      if (mag > 0.0001) {
        omegaArrowRef.current.setDirection(omegaVec.clone().normalize());
        const arrowLength = Math.min(3.5, Math.max(0.6, mag * 2.5));
        omegaArrowRef.current.setLength(arrowLength, arrowLength * 0.25, arrowLength * 0.15);
      }

      // Color arrow based on magnitude & state
      if (state === "INLINE_INVARIANT_BREACH") {
        omegaArrowRef.current.setColor(new THREE.Color(0xef4444)); // Pulsing Red
      } else if (state === "SAFE_HOLD" || state === "RECOVERY_VERIFIED") {
        omegaArrowRef.current.setColor(new THREE.Color(0x06b6d4)); // Cyan
      } else {
        omegaArrowRef.current.setColor(new THREE.Color(0x10b981)); // Emerald
      }
    }

    // 3. Aura Ring Glow & Color State
    if (auraRingRef.current) {
      const mat = auraRingRef.current.material as THREE.MeshBasicMaterial;
      if (state === "INLINE_INVARIANT_BREACH") {
        mat.color.setHex(0xef4444);
        mat.opacity = 0.8 + 0.2 * Math.sin(Date.now() * 0.01);
      } else if (state === "ACTUATOR_INHIBITED") {
        mat.color.setHex(0xf59e0b);
        mat.opacity = 0.7;
      } else if (state === "RECOVERY_VERIFIED") {
        mat.color.setHex(0x06b6d4);
        mat.opacity = 0.85;
      } else if (state === "SAFE_HOLD") {
        mat.color.setHex(0x38bdf8);
        mat.opacity = 0.6;
      } else {
        mat.color.setHex(0x10b981);
        mat.opacity = 0.45;
      }
    }

    // 4. Wireframe Toggle on Bus Mesh
    const bus = spacecraftGroupRef.current.getObjectByName("bus") as THREE.Mesh;
    if (bus && bus.material) {
      (bus.material as THREE.MeshStandardMaterial).wireframe = wireframe;
      if (state === "INLINE_INVARIANT_BREACH") {
        (bus.material as THREE.MeshStandardMaterial).emissive.setHex(0xef4444);
        (bus.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.35;
      } else {
        (bus.material as THREE.MeshStandardMaterial).emissive.setHex(0x000000);
        (bus.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.0;
      }
    }
  }, [q, omega, state, wireframe]);

  // Camera Orbit / Distance Adjustment
  useEffect(() => {
    if (cameraRef.current) {
      const dir = cameraRef.current.position.clone().normalize();
      cameraRef.current.position.copy(dir.multiplyScalar(cameraDistance));
      cameraRef.current.lookAt(0, 0, 0);
    }
  }, [cameraDistance]);

  const handleResetCamera = () => {
    if (cameraRef.current) {
      cameraRef.current.position.set(2.8, 2.2, 3.8);
      cameraRef.current.lookAt(0, 0, 0);
      setCameraDistance(4.2);
    }
  };

  return (
    <div className="relative w-full h-full flex flex-col bg-[#161B22] border border-[#30363D] rounded-lg overflow-hidden shadow-2xl">
      {/* Top HUD Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0D1117]/80 backdrop-blur border-b border-[#30363D] z-10">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-cyan-400 animate-spin-slow" />
          <span className="font-mono text-xs uppercase tracking-wider text-slate-300 font-bold">
            Spacecraft Attitude & Dynamics Engine
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-[#21262D] text-slate-400 border border-[#30363D]">
            3D THREE.JS WEBGL
          </span>
        </div>

        {/* Viewport Action Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setWireframe(!wireframe)}
            className={`px-2 py-1 text-[11px] font-mono rounded border transition-colors flex items-center gap-1 ${
              wireframe
                ? "bg-cyan-950/80 border-cyan-500 text-cyan-300"
                : "bg-[#21262D] border-[#30363D] text-slate-400 hover:text-slate-200"
            }`}
            title="Toggle Wireframe Mesh"
          >
            <Layers className="w-3 h-3" />
            <span>WIRE</span>
          </button>
          <button
            onClick={() => setShowHorizon(!showHorizon)}
            className={`px-2 py-1 text-[11px] font-mono rounded border transition-colors ${
              showHorizon
                ? "bg-emerald-950/80 border-emerald-500 text-emerald-300"
                : "bg-[#21262D] border-[#30363D] text-slate-400 hover:text-slate-200"
            }`}
            title="Toggle HUD Pitch Ladder & Crosshair"
          >
            HUD
          </button>
          <button
            onClick={handleResetCamera}
            className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#21262D] rounded border border-[#30363D]"
            title="Reset Camera View"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main 3D Canvas Viewport */}
      <div className="relative flex-1 w-full min-h-[360px] overflow-hidden">
        <div ref={mountRef} className="w-full h-full" />

        {/* Flight State Visual Overlay Banner */}
        <div className="absolute top-3 left-3 pointer-events-none z-10 flex flex-col gap-1.5">
          {state === "NOMINAL" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-950/80 border border-emerald-500/70 rounded shadow-lg backdrop-blur">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <div className="text-[11px] font-mono text-emerald-300 font-semibold">
                STABLE CELESTIAL TRACKING
              </div>
            </div>
          )}

          {state === "INLINE_INVARIANT_BREACH" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-red-950/90 border border-red-500 rounded shadow-lg backdrop-blur animate-pulse">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <div>
                <div className="text-[11px] font-mono text-red-300 font-bold tracking-wide">
                  VEHICLE TUMBLING ACTIVE
                </div>
                <div className="text-[9px] font-mono text-red-400">
                  Angular rate divergence | Rate: {omegaMagDeg}°/s
                </div>
              </div>
            </div>
          )}

          {state === "SAFE_HOLD" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-sky-950/90 border border-sky-500/80 rounded shadow-lg backdrop-blur">
              <Zap className="w-4 h-4 text-sky-400 animate-pulse" />
              <div>
                <div className="text-[11px] font-mono text-sky-300 font-semibold">
                  SAFE-HOLD B-DOT DAMPING
                </div>
                <div className="text-[9px] font-mono text-sky-400">
                  Magnetorquer rate deceleration active
                </div>
              </div>
            </div>
          )}

          {state === "RECOVERY_VERIFIED" && (
            <div className="flex items-center gap-2 px-3 py-1 bg-cyan-950/90 border border-cyan-400 rounded shadow-lg backdrop-blur">
              <ShieldCheck className="w-4 h-4 text-cyan-300" />
              <div>
                <div className="text-[11px] font-mono text-cyan-200 font-bold">
                  RECOVERY RATE-DAMPING ALIGNMENT
                </div>
                <div className="text-[9px] font-mono text-cyan-400">
                  Converging to celestial target vector
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 2D Artificial Horizon & Pitch Ladder HUD Layer */}
        {showHorizon && (
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            {/* Center Reticle */}
            <div className="relative w-44 h-44 border border-cyan-500/20 rounded-full flex items-center justify-center">
              {/* Pitch Ladder Marks */}
              <div
                className="w-full h-full relative transition-transform duration-75"
                style={{
                  transform: `rotate(${-euler.roll}deg)`,
                }}
              >
                {/* Horizontal Center Horizon Line */}
                <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-cyan-400/40 transform -translate-y-1/2 flex items-center justify-between px-1">
                  <span className="text-[8px] font-mono text-cyan-400">L</span>
                  <span className="text-[8px] font-mono text-cyan-400">R</span>
                </div>

                {/* Pitch Bars */}
                <div
                  className="absolute left-1/2 -translate-x-1/2 w-16 h-12 flex flex-col justify-between transition-all duration-75"
                  style={{
                    transform: `translate(-50%, ${-euler.pitch * 1.5}px)`,
                  }}
                >
                  <div className="h-[1px] bg-cyan-400/50 flex justify-between">
                    <span className="text-[7px] font-mono text-cyan-300 -mt-2.5">+10°</span>
                    <span className="text-[7px] font-mono text-cyan-300 -mt-2.5">+10°</span>
                  </div>
                  <div className="h-[1px] bg-cyan-400/50 flex justify-between">
                    <span className="text-[7px] font-mono text-cyan-300 mt-0.5">-10°</span>
                    <span className="text-[7px] font-mono text-cyan-300 mt-0.5">-10°</span>
                  </div>
                </div>
              </div>

              {/* Center Crosshair Fixed */}
              <div className="absolute w-6 h-6 border-t border-b border-l border-r border-amber-400/70" />
              <div className="absolute w-1.5 h-1.5 bg-amber-400 rounded-full" />
            </div>
          </div>
        )}

        {/* Live Vector Telemetry Float Cards */}
        <div className="absolute bottom-3 left-3 right-3 pointer-events-none grid grid-cols-1 md:grid-cols-3 gap-2">
          {/* Quaternion Readout */}
          <div className="bg-[#0D1117]/90 border border-[#30363D] rounded px-3 py-2 backdrop-blur">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
              <span>QUATERNION [w, x, y, z]</span>
              <span
                className={`font-semibold ${
                  Math.abs(qNorm - 1.0) < 0.005 ? "text-emerald-400" : "text-red-400"
                }`}
              >
                ||q|| = {qNorm.toFixed(4)}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-1 text-center font-mono text-xs text-slate-200">
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">QW</span>
                {q.w.toFixed(3)}
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">QX</span>
                {q.x.toFixed(3)}
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">QY</span>
                {q.y.toFixed(3)}
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">QZ</span>
                {q.z.toFixed(3)}
              </div>
            </div>
          </div>

          {/* Angular Velocity Readout */}
          <div className="bg-[#0D1117]/90 border border-[#30363D] rounded px-3 py-2 backdrop-blur">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
              <span>ANGULAR VELOCITY [ω]</span>
              <span className="text-cyan-400 font-semibold">{omegaMagDeg}°/s</span>
            </div>
            <div className="grid grid-cols-3 gap-1 text-center font-mono text-xs text-slate-200">
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">ωX rad/s</span>
                {omega.x.toFixed(3)}
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">ωY rad/s</span>
                {omega.y.toFixed(3)}
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">ωZ rad/s</span>
                {omega.z.toFixed(3)}
              </div>
            </div>
          </div>

          {/* Euler Attitude (Roll, Pitch, Yaw) */}
          <div className="bg-[#0D1117]/90 border border-[#30363D] rounded px-3 py-2 backdrop-blur">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
              <span>EULER ANGLES</span>
              <span className="text-amber-400 font-semibold">Tait-Bryan (XYZ)</span>
            </div>
            <div className="grid grid-cols-3 gap-1 text-center font-mono text-xs text-slate-200">
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">ROLL</span>
                {euler.roll}°
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">PITCH</span>
                {euler.pitch}°
              </div>
              <div className="bg-[#161B22] py-0.5 rounded border border-[#30363D]">
                <span className="text-[9px] text-slate-500 block">YAW</span>
                {euler.yaw}°
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
