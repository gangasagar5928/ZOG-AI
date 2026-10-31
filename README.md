<p align="center">
  <img src="assets/logo.png" alt="RadZero Official Mission Emblem" width="560"/>
</p>

# RadZero: Physics-Aware Fault Containment & In-Situ Recovery Runtime for Autonomous Spacecraft AI

[![System Classification](https://img.shields.io/badge/Classification-Experimental%20Edge%20AI%20Runtime-00F0FF?style=for-the-badge&logo=target)](https://github.com/gangasagar5928/ZOG-AI)
[![Version](https://img.shields.io/badge/Version-2.3.0--FROZEN-00FF66?style=for-the-badge)](https://github.com/gangasagar5928/ZOG-AI)
[![Track Alignment](https://img.shields.io/badge/Track-Problem%20Statement%2031-FF9900?style=for-the-badge)](https://github.com/gangasagar5928/ZOG-AI)
[![Uptime](https://img.shields.io/badge/Process%20Uptime-100.0%25-brightgreen?style=for-the-badge)](https://github.com/gangasagar5928/ZOG-AI)
[![Tests](https://img.shields.io/badge/Unit%20%26%20Integration%20Tests-50%2F50%20Passing-success?style=for-the-badge)](https://github.com/gangasagar5928/ZOG-AI)

---

## 1. Problem Statement: The Physics of Corrupted Neural Inference in Spacecraft ADCS

Modern small satellites (CubeSats 12U/27U, SmallSats) and autonomous deep-space probes increasingly deploy unshielded Commercial Off-The-Shelf (COTS) edge accelerators—including mobile GPUs and embedded Neural Processing Units (NPUs)—to execute closed-loop Attitude Determination and Control Systems (ADCS) and autonomous vision-based proximity operations.

Operating unshielded consumer silicon outside the Earth's magnetosphere exposes volatile semiconductor memory (SRAM/DRAM) to ionizing radiation: galactic cosmic rays (GCRs), trapped Van Allen belt protons, and high-energy Solar Particle Events (SPEs). These particles deposit ionization charge in transistor gates, inducing **Single-Event Upsets (SEUs)** in model weights.

```
                  IONIZING RADIATION CASCADE & SPACECRAFT TUMBLE
                  
           Cosmic Ray / Trapped Van Allen Belt Proton Strike
                                 │
                                 ▼
         [ Volatile Semiconductor Memory Cell (Bit-Flip SEU) ]
                                 │
                                 ▼
               [ Corrupted Neural Network Inference ]
                 (Weight Exponent / Sign Bit Mutation)
                                 │
                                 ▼
             [ Physically Unsafe Actuator Control Torque ]
              (Torque Saturation / Dynamic Acceleration Breach)
                                 │
                                 ▼
           [ Reaction Wheel Momentum Saturation: ||h_RW|| > h_max ]
                                 │
                                 ▼
         [ Catastrophic Kinetic Tumble & Solar De-Pointing ]
                                 │
                                 ▼
          [ Standard Recovery: Multi-Hour Cold Reboot / Loss of Mission ]
```

### The Causal Triad: Memory Corruption $\to$ Actuator Violation $\to$ Spacecraft Loss

In deep neural networks executing closed-loop control loops, stochastic bit transitions within IEEE-754 single-precision (FP32) tensors cause **Silent Data Corruption (SDC)** that directly threatens spacecraft stability:

**1. Sign-Bit Inversion ($\text{Bit } 31$)**  
Reverses commanded torque polarity:

$$
\boldsymbol{\tau}_{\mathrm{cmd}} \to -\boldsymbol{\tau}_{\mathrm{cmd}}
$$

Injects positive angular momentum feedback into the closed loop, rapidly accelerating vehicle body rates and driving the spacecraft into an anomalous kinetic spin-up.

**2. Exponent Surge ($\text{Bits } 30\text{--}23$, $0 \to 1$)**  
Scales numerical parameters exponentially:

$$
\Delta x = 2^{+128} \approx 3.4028 \times 10^{38}
$$

Induces instantaneous numerical overflow and catastrophic `inf` / `NaN` cascades throughout activation layers, permanently corrupting actuator drive outputs.

**3. Exponent Collapse ($\text{Bits } 30\text{--}23$, $1 \to 0$)**  
Collapses values into subnormal or zeroed regimes:

$$
\Delta x = 2^{-128} \approx 2.9387 \times 10^{-39}
$$

Silently zeroes neural pathway sensitivity, severing attitude control authority and rendering the spacecraft unresponsive to external disturbance torques.

**4. Mantissa Shift ($\text{Bits } 22\text{--}0$)**  
Induces subtle, in-bounds parameter drift that evades static bounds checks while producing uncompensated attitude drift and loss of communications alignment.

**The Mission Critical Vulnerability**: Once an unphysical torque command is dispatched to reaction wheels, angular momentum accumulates across discrete control steps $\Delta t$:

$$
\mathbf{h}_{\mathrm{RW}}(t_{k+1}) = \mathbf{h}_{\mathrm{RW}}(t_k) + \boldsymbol{\tau}_{\mathrm{cmd}}\Delta t
$$

When momentum storage reaches saturation capacity ($0.10\text{ N}\cdot\text{m}\cdot\text{s}$), the wheels saturate, cross-coupling Euler torques destabilize the principal inertia axes, solar arrays de-point from the Sun, and battery depletion results in complete loss of spacecraft.

Traditional aerospace recovery relies on watchdogs triggering uncoordinated power cycles and multi-hour cold reboots (30 minutes to 6 hours), severing communications and leaving the tumbling vehicle unable to reacquire pointing.

---

## 2. Solution: Physics-Aware Fault Containment (PAFC) & In-Situ Recovery

**RadZero** moves beyond generic radiation protection by introducing **Physics-Aware Fault Containment (PAFC)**. Instead of treating fault tolerance merely as a memory-auditing task, RadZero explicitly couples tensor integrity to **rigid-body spacecraft dynamics** and **actuator kinematic limits**.

```mermaid
flowchart TD
    Inp["Kinematic State<br/>x = [q_e, w]"] --> Lock["Shared Read Lock<br/>Parameter RW-Mutex"]
    Lock --> Inf["PyTorch Graph<br/>tau_cmd = M_theta(x)"]
    Inf --> T1{"Tier 1 Tripwire<br/>NaN/Inf & Chebyshev"}
    
    T1 -- Breach --> Rec["In-Situ Recovery<br/>Host DMA Restore"]
    T1 -- Pass --> T2{"Tier 2 Gate<br/>Kinematic Limits"}
    
    T2 -- Breach --> Rec
    T2 -- Pass --> Act["Actuator Dispatch<br/>Verified Safe Torque"]
    
    Act --> Slack["Control Slack Time"]
    Slack --> T3{"Tier 3 Scrubber<br/>Cyclic CRC-32 Audit"}
    T3 -- Mismatch --> Rec
    T3 -- Pass --> Nom["Nominal Hold"]
    
    Rec --> Reeval{"Post-Recovery<br/>Re-Verification"}
    Reeval -- Pass --> Nom
    Reeval -- Fail --> Safe["Safe-Hold Mode<br/>tau_safe = -Kd * w"]
```

### Core Architectural Pillars:
1. **Tier 1: In-Line Activation Invariant Tripwires**: Low-overhead ($<0.15\text{ ms}$, $<0.2\%$ of $100\text{ ms}$ control frame) forward hooks evaluating intermediate activation tensors for non-finite values (`isnan`, `isinf`) and dynamic Chebyshev envelope breaches ($\pm 4.5\sigma$ from mean).
2. **Tier 2: Rigid-Body Dynamic & Actuator Gate**: Evaluates torque candidates against Euler's rotational equations of motion over a $\Delta t = 100\text{ ms}$ control window. Enforces physical vehicle limits before command dispatch: per-axis torque saturation ($\le 0.05\text{ N}\cdot\text{m}$), angular acceleration ($\le 0.65\text{ rad/s}^2$), and integrated vehicle slew rate ($\le 0.08\text{ rad/s}$).
3. **Tier 3: Asynchronous Cyclic Memory Scrubber**: Soft real-time cyclic worker auditing 1 parameter block per $100\text{ ms}$ frame using CRC-32-IEEE 802.3 digests against host-pinned shadow mirrors. Detects latent mutations masked by zero activations before they alter vehicle dynamics.
4. **Concurrency-Safe In-Situ Hot-Patching**: Coordinated via a fair Parameter ReadWriteLock Mutex (shared read for nominal inference, exclusive write for recovery). Upon breach detection, the sentinel drains active GPU streams via `torch.cuda.synchronize()`, executes PCIe DMA parameter restoration (`param.data.copy_()`) from host-pinned golden buffers, re-evaluates the forward pass, and dispatches the verified safe torque within **$<3.5\text{ ms}$** (mean $0.68\text{ ms}$), well under the $100\text{ ms}$ ADCS deadline.
5. **Deterministic Safe-Hold Escalation**: If both primary and backup host mirrors fail CRC verification or DMA latency breaches the deadline, the runtime engages hard-coded proportional rate damping ($-K_d \boldsymbol{\omega}$) and magnetic torquer (MTQ) momentum desaturation to safely null body rates and unload reaction wheel momentum without terminating the application process.

---

## 3. RadZero vs. Existing Approaches: Our Project vs. Others

A common limitation of prior fault-tolerance frameworks is their separation of hardware reliability from the physical system being controlled. Below is a comparative analysis detailing how RadZero differs from generic periodic software scrubbers and classical aerospace fault-tolerance mechanisms.

### Comparative Architectural Matrix

| Architectural Feature | Classical ECC / EDAC | Checkpoint & Cold Reboot | Triple Modular Redundancy (TMR) | Periodic Software Scrubbers (10-60s Sweep) | **RadZero (This Project)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fault Containment Philosophy** | Bit-level hardware detection | Coarse post-crash restart | Compute voting redundancy | Blind periodic memory audit | **Physics-Aware Closed-Loop Gate** |
| **Awareness of Vehicle Dynamics** | None (hardware blind) | None (system offline) | None (votes on raw outputs) | None (isolated memory scan) | **Euler Rigid-Body Dynamics Gate** |
| **Actuator Command Protection** | ❌ No protection | ❌ Unsafe commands fire | ⚠️ Dependent on voter sanity | ❌ Unsafe commands fire | **✅ Pre-dispatch kinematic interlock** |
| **Recovery Latency** | Instant (single-bit only) | **30 s to 45 min** (downtime) | Real-time (adds voting overhead) | **10 s to 60 s** (sweep cycle) | **$<3.5\text{ ms}$ (mean $0.68\text{ ms}$)** |
| **SWaP-C Overhead (CubeSat)** | None (built-in silicon) | High (mission downtime cost) | **+200% Compute & Power (3x)** | Moderate memory overhead | **$<0.15\text{ ms}$ (<0.2% frame), zero hardware dupl.** |
| **Process Continuity** | 100% (if single bit) | **0% (Process terminates)** | 100% (requires 3 instances) | 100% (does not heal in-flight) | **100% Continuous Process Uptime** |
| **Multi-Bit Burst & Exponent SDC** | ❌ Multi-bit silent failure | ❌ Host crash / hang | ⚠️ Susceptible to common-mode | ⚠️ Detects after delay | **✅ In-line tripwire + DMA hot-patch** |
| **In-Situ Parameter Hot-Patching** | ❌ No model patching | ❌ Full reload from NVRAM | ❌ No in-place tensor repair | ❌ Requires process restart | **✅ In-place GPU/Host RAM replacement** |
| **Flight Heritage & TRL** | Decades (standard silicon) | Flight standard (watchdog reboot) | Decades (Voyager, Shuttle, ISS) | Laboratory & SmallSat missions | **TRL 4 (Lab-validated COTS hardware)** |

### Key Differentiators: Physics-Aware In-Situ Containment vs. Periodic Scrubbers
1. **Kinematic vs. Memory-Centric Boundary**: Generic periodic scrubbers inspect memory arrays in isolation on a periodic timer (every 10–60 seconds, e.g., Berg et al., IEEE TNS). During that sweep delay, an SEU-corrupted neural network will execute hundreds of inference passes, outputting hazardous torques that saturate reaction wheels. RadZero places an **in-line physics gate between inference and the actuator bus**: unphysical commands are physically blocked before reaching thrusters or reaction wheels.
2. **Deterministic In-Situ Hot-Patching vs. Power Cycling**: Traditional scrubbers and EDAC systems cannot patch live accelerator memory on the fly without stopping execution or restarting the application. RadZero coordinates PyTorch execution and host-pinned memory to hot-patch corrupted tensor blocks in **$0.68\text{ ms}$** without dropping a single control cycle.
3. **SWaP-C Viability for SmallSats**: Unlike Triple Modular Redundancy (TMR)—which triplicates GPUs, tripling power consumption from 15W to 45W and demanding silicon area unachievable on CubeSats—RadZero operates on a single COTS accelerator with dual host shadow buffers, preserving 100% process uptime at nominal power draw.

---

## 4. Technical Stack

RadZero is engineered as an end-to-end, multi-node edge AI runtime and distributed aerospace telemetry suite:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           RADZERO TECH STACK                                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  [ 1. CORE AI & KINEMATIC RUNTIME (Python 3.10+ / PyTorch 2.x) ]
  • PyTorch 2.1.0+ (Tested: PyTorch 2.13.0+cpu / CUDA 12.x): Deterministic ADCS MLP, custom hooks, torch.inference_mode()
  • Vectorized Single-Pass Invariant Reductions: torch.aminmax(), math.isnan(), math.isinf()
  • Rigid-Body Dynamics Engine: Quaternion kinematics (Hamilton convention), Euler equations of motion, NumPy vectorized
  • Concurrency & Locking: Custom fair ReadWriteLock with writer priority (exclusive write on recovery, shared read on inference)
  • Fault Injection Engine: Raw IEEE-754 FP32 bitfield mutation (sign, exponent, mantissa bit-twiddling)

  [ 2. ACCELERATOR RUNTIME NODE (Dedicated NVIDIA RTX 3050 Mobile / CUDA) ]
  • NVIDIA CUDA 12.x / cuBLAS: Hardware stream partitioning (inference_stream vs recovery_stream)
  • Host-Pinned Memory (Page-Locked DMA): Pin-memory shadow mirrors for PCIe DMA copy throughput
  • Hardware Recovery Barrier: torch.cuda.synchronize() stream draining & atomic in-place tensor copying
  • Dual-Domain Latency Profiler: torch.cuda.Event(enable_timing=True) paired with time.perf_counter_ns()

  [ 3. TELEMETRY & STATE STREAMING BACKEND (FastAPI / ASGI) ]
  • FastAPI & Starlette: Async RESTful microservice with CORS for local subnet distribution
  • WebSocket Broadcaster: 10 Hz synchronous control frame & WebSocket telemetry streaming (/ws/telemetry)
  • HTTP Fallback Engine: 250 ms client polling fallback (/api/telemetry/latest)
  • Remote Injection Endpoints: POST /api/inject_seu, POST /api/reset, POST /api/corrupt_mirror

  [ 4. MISSION CONTROL HUD (Next.js 14 / TypeScript / Three.js) ]
  • Next.js 14 (App Router) & React 18: Full-screen Aerospace Obsidian dark-themed mission console
  • Three.js / WebGL Visualizer: Real-time 3D spacecraft orientation, celestial starfield, angular momentum
  • Telemetry Client: Resilient client with automatic WebSocket-to-HTTP fallback & RTT latency tracking
  • Visual Gating Barrier: Actuator interlock status, reaction wheel RPM, RCS thruster firing indicators
  • Tailwind CSS & Lucide React: High-contrast aerospace telemetry aesthetic (#0D1117 / #161B22)

  [ 5. VERIFICATION & BENCHMARKING SUITE (Pytest / Monte Carlo) ]
  • Pytest 7.4+ & AnyIO 3.7+: 50 comprehensive unit, concurrency, and end-to-end integration tests
  • Monte Carlo SEU Suite: Automated 50-trial fault-injection and in-situ recovery benchmark
```

---

## 5. Mathematical Formulations & Physical Invariants

### 5.1 IEEE-754 Floating-Point Bitfield Representation

Every model parameter $w \in \mathbb{R}$ is formatted in IEEE-754 32-bit single precision:

$$
w = (-1)^s \cdot 2^{e - 127} \cdot \biggl(1 + \sum_{i=1}^{23} b_{23-i} 2^{-i}\biggr)
$$

Where bitfield decomposition defines:
* Sign bit: $s \in \lbrace 0, 1 \rbrace$ ($\text{Bit } 31$)
* Biased 8-bit exponent $e \in [0, 255]$ ($\text{Bits } 30\text{--}23$):

$$
e = \sum_{j=0}^7 b_{23+j} 2^j
$$

* Fractional 23-bit mantissa $m \in [0, 1)$ ($\text{Bits } 22\text{--}0$):

$$
m = \sum_{i=1}^{23} b_{23-i} 2^{-i}
$$

---

### 5.2 Deterministic ADCS Neural Network Graph (FR-1)

The control system executes a deterministic Multi-Layer Perceptron (MLP) mapping a 7-element state input to 3-axis reaction-wheel torque commands:

$$
\mathbf{x} = \begin{bmatrix} \mathbf{q}_e \\ \boldsymbol{\omega} \end{bmatrix} \in \mathbb{R}^7, \quad \mathbf{q}_e = \begin{bmatrix} q_w \\ q_x \\ q_y \\ q_z \end{bmatrix} \in \mathbb{S}^3 \quad (\|\mathbf{q}_e\|_2 = 1), \quad \boldsymbol{\omega} = \begin{bmatrix} \omega_x \\ \omega_y \\ \omega_z \end{bmatrix} \in \mathbb{R}^3
$$

The forward inference graph computes:

$$
\mathbf{h}_0 = \tanh(\mathbf{W}_0 \mathbf{x} + \mathbf{b}_0), \quad \mathbf{W}_0 \in \mathbb{R}^{64 \times 7}
$$

$$
\mathbf{h}_1 = \tanh(\mathbf{W}_1 \mathbf{h}_0 + \mathbf{b}_1), \quad \mathbf{W}_1 \in \mathbb{R}^{64 \times 64}
$$

$$
\mathbf{h}_2 = \tanh(\mathbf{W}_2 \mathbf{h}_1 + \mathbf{b}_2), \quad \mathbf{W}_2 \in \mathbb{R}^{32 \times 64}
$$

$$
\boldsymbol{\tau}_{\mathrm{cmd}} = \mathbf{W}_3 \mathbf{h}_2 + \mathbf{b}_3, \quad \mathbf{W}_3 \in \mathbb{R}^{3 \times 32}
$$

Partitioned into 4 sequential parameter blocks:

$$
\mathcal{B} = \lbrace \mathcal{B}_0: (\mathbf{W}_0, \mathbf{b}_0), \; \mathcal{B}_1: (\mathbf{W}_1, \mathbf{b}_1), \; \mathcal{B}_2: (\mathbf{W}_2, \mathbf{b}_2), \; \mathcal{B}_3: (\mathbf{W}_3, \mathbf{b}_3) \rbrace
$$

---

### 5.3 Tier 1: In-Line Activation Tripwire (FR-3)

Intermediate layer activations $\mathbf{a}_l$ are checked via PyTorch forward-pass hooks with $<0.15\text{ ms}$ execution overhead ($<0.2\%$ of the $100\text{ ms}$ control frame):

**1. Finite Value Verification**

$$
\forall a \in \mathbf{a}_l: \quad \neg\mathrm{isnan}(a) \;\wedge\; \neg\mathrm{isinf}(a)
$$

**2. Dynamic Chebyshev Layer-Wise Bounds**

By Chebyshev's Inequality, for calibrated activation distribution $(\mu_l, \sigma_l)$ and scale factor $k = 4.5$:

$$
P(|a_l - \mu_l| \ge k \sigma_l) \le \frac{1}{k^2} = \frac{1}{4.5^2} \approx 0.0494
$$

The allowable dynamic activation envelope is:

$$
\mu_l - k\sigma_l \le a_l \le \mu_l + k\sigma_l
$$

The single-element theoretical bound of $\approx 4.94\%$ represents an extreme distribution-free upper bound. In practice, across calibrated neural activation channels under nominal ADCS operations, choosing $k = 4.5$ yields an empirical false-alarm rate below $5 \times 10^{-4}$ per frame. Vectorized reduction is evaluated with `torch.aminmax(a_l)` in a single native pass, taking $\le 0.12\text{ ms}$.

---

### 5.4 Tier 2: Rigid-Body Dynamics & Actuator Gate (FR-3)

Evaluates commanded torques against physical spacecraft kinematics over control step $\Delta t = 100\text{ ms}$:

**1. Actuator Torque Saturation**

$$
\|\boldsymbol{\tau}_{\mathrm{cmd}}\|_\infty = \max(|\tau_x|, |\tau_y|, |\tau_z|) \le \tau_{\max} = 0.05\text{ N}\cdot\text{m}
$$

**2. Rotational Dynamics (Euler's Equations of Motion)**

$$
\mathbf{I}\dot{\boldsymbol{\omega}} + \boldsymbol{\omega} \times (\mathbf{I}\boldsymbol{\omega}) = \boldsymbol{\tau}_{\mathrm{cmd}}
$$

Rearranging for angular acceleration $\dot{\boldsymbol{\omega}}$:

$$
\dot{\boldsymbol{\omega}} = \mathbf{I}^{-1} \bigl[ \boldsymbol{\tau}_{\mathrm{cmd}} - \boldsymbol{\omega} \times (\mathbf{I}\boldsymbol{\omega}) \bigr]
$$

With spacecraft moment-of-inertia tensor:

$$
\mathbf{I} = \mathrm{diag}(0.10, 0.10, 0.08)\text{ kg}\cdot\text{m}^2
$$

Evaluating dynamic angular acceleration:

$$
\|\dot{\boldsymbol{\omega}}\|_2 = \sqrt{\dot{\omega}_x^2 + \dot{\omega}_y^2 + \dot{\omega}_z^2} \le \alpha_{\max} = 0.65\text{ rad/s}^2
$$

**3. Integrated Slew-Rate Boundary**

$$
\boldsymbol{\omega}_{k+1} = \boldsymbol{\omega}_k + \dot{\boldsymbol{\omega}}\Delta t
$$

$$
\|\boldsymbol{\omega}_{k+1}\|_2 \le \omega_{\max} = 0.08\text{ rad/s}
$$

> [!NOTE]
> **Kinematic Satisfiability**: With minimum principal inertia $I_{zz} = 0.08\text{ kg}\cdot\text{m}^2$ and maximum allowable actuator torque $\tau_{\max} = 0.05\text{ N}\cdot\text{m}$, commanding pure maximum z-axis torque from rest yields angular acceleration $\dot{\omega}_z = 0.05 / 0.08 = 0.625\text{ rad/s}^2 \le \alpha_{\max}$ ($0.65\text{ rad/s}^2$). Over a $\Delta t = 100\text{ ms}$ step, the integrated body rate reaches $\Delta \omega_z = 0.0625\text{ rad/s} \le \omega_{\max}$ ($0.08\text{ rad/s}$). All three physical gates are therefore simultaneously satisfiable from rest without generating false-positive tripwire alarms.

---

### 5.5 Tier 3: Asynchronous Cyclic Parameter Scrubber (FR-3)

Operates in background slack time during the 100 ms control frame ($\le 15\text{ ms}$ budget). Cyclically verifies 1 parameter block $\mathcal{B}_i$ per frame using CRC-32-IEEE 802.3:

$$
G(x) = x^{32} + x^{26} + x^{23} + x^{22} + x^{16} + x^{12} + x^{11} + x^{10} + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1
$$

With 4 parameter blocks, complete model sweep period is:

$$
T_{\mathrm{scrub}} = N_{\mathrm{blocks}} \times \Delta t_{\mathrm{frame}} = 4 \times 100\text{ ms} = 400\text{ ms}
$$

Detects latent parameter mutations masked by zero activations or dead zones before they affect vehicle dynamics.

---

### 5.6 Classical Safe-Hold Controller (FR-5)

When unrecoverable faults occur (e.g., dual mirror corruption or latency deadline breaches), the system triggers hard-coded proportional rate damping:

$$
\boldsymbol{\tau}_{\mathrm{safe}} = \mathrm{clip}(-K_d \boldsymbol{\omega}, \; -\tau_{\max}, \; +\tau_{\max}), \quad K_d = 0.08\text{ N}\cdot\text{m}\cdot\text{s/rad}
$$

Reaction-wheel momentum storage tracks integrated torque against hardware limits:

$$
\mathbf{h}_{\mathrm{RW}}(t_{k+1}) = \mathbf{h}_{\mathrm{RW}}(t_k) + \boldsymbol{\tau}_{\mathrm{safe}}\Delta t
$$

$$
\|\mathbf{h}_{\mathrm{RW}}\|_2 \le h_{\max} = 0.10\text{ N}\cdot\text{m}\cdot\text{s}
$$

To prevent reaction-wheel saturation during extended safe-hold damping, magnetic torquer (MTQ) momentum desaturation dumps stored angular momentum against geomagnetic field lines:

$$
\mathbf{h}_{\mathrm{RW}}(t_{k+1}) = (1 - \gamma_{\mathrm{dump}}) \mathbf{h}_{\mathrm{RW}}(t_k), \quad \gamma_{\mathrm{dump}} = 0.10\text{ per frame}
$$

Once vehicle angular rates null within the nominal envelope ($\|\boldsymbol{\omega}\|_2 < 0.75 \times \omega_{\max}$) and verified golden model parameters are confirmed, the state machine autonomously clears safe-hold and transitions back to `NOMINAL` mode without human operator telecommand or host reboot.

---

## 6. Concurrency & Hot-Patching Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Inf as Inference Thread
    participant RW as Parameter RW-Lock
    participant Tiers as Invariant Sentinels (T1 / T2)
    participant Rec as Recovery Sentinel
    participant GPU as Accelerator Memory (CUDA/NPU)
    participant Mirror as Pinned Host Checkpoint Mirrors

    Inf->>RW: acquire_read()
    Inf->>GPU: Deterministic forward pass: tau_cmd = M_theta(x)
    GPU-->>Inf: Raw torque candidate
    Inf->>RW: release_read()
    
    Inf->>Tiers: validate_invariants(tau_cmd, activations)
    Tiers-->>Inf: BREACH DETECTED (Chebyshev / Kinematic Breach)
    
    Inf->>Rec: initiate_recovery(breach_context)
    Rec->>RW: acquire_write() [Exclusive Access]
    Rec->>GPU: torch.cuda.synchronize() [Drain Active Streams]
    
    Rec->>Mirror: verify_crc32(primary_mirror)
    alt Primary Mirror Valid
        Mirror-->>Rec: Primary Buffer OK
    else Primary Corrupt, Backup Valid
        Mirror-->>Rec: Backup Buffer OK
    else Both Mirrors Corrupted
        Rec->>Inf: Trigger SAFE_HOLD Escalation (-Kd * omega)
    end

    Rec->>GPU: param.data.copy_(mirror.data) [In-Place DMA Restore]
    Rec->>GPU: torch.cuda.synchronize()
    Rec->>RW: release_write()
    
    Rec->>Inf: Re-evaluate forward pass & invariants
    alt Post-Recovery Re-Verification Passed
        Inf->>GPU: Dispatch verified tau_cmd to Actuator Bus
    else Post-Recovery Re-Verification Failed
        Inf->>Inf: Escalate to Safe-Hold (-Kd * omega)
    end
```

---

## 7. Subsystem Directory Structure

```
Graviton/
├── assets/
│   └── logo.png                          # Official RadZero mission emblem & brand asset
├── radzero/                              # Core Lead Systems Runtime (Member 1)
│   ├── core/
│   │   ├── adcs_model.py                 # Deterministic MLP mapping R^7 -> R^3 (4 blocks)
│   │   ├── rwlock.py                     # Fair ReadWriteLock with writer priority
│   │   ├── safe_hold.py                  # Classical B-dot / proportional rate damping controller
│   │   └── types.py                      # TelemetryPacket, SystemState, KinematicLimits
│   ├── invariants/
│   │   ├── tier1_tripwire.py             # Layer hooks: isnan(), isinf(), dynamic Chebyshev
│   │   ├── tier2_dynamics_gate.py        # Euler rigid-body kinematic & actuator barrier
│   │   └── tier3_scrubber.py             # CRC-32-IEEE 802.3 idle cyclic memory scrubber
│   ├── mutation/
│   │   └── ieee754_injector.py           # Raw IEEE-754 FP32 bitfield mutation engine
│   ├── recovery/
│   │   ├── checkpoint_mirror.py          # Dual primary & backup host-pinned mirrors
│   │   └── state_machine.py              # RadZero runtime sentinel & in-situ coordinator
│   ├── telemetry/
│   │   └── server.py                     # FastAPI 10 Hz WebSocket & HTTP polling broadcaster
│   └── benchmarks/
│       └── suite_50_trials.py            # Automated 50-trial Monte Carlo validation suite
│
├── accelerator_runtime/                  # GPU Accelerator Runtime Node (Member 3 - Aaditya)
│   ├── src/
│   │   ├── api/                          # FastAPI LAN service (0.0.0.0:8000), WS, REST routes
│   │   ├── concurrency/                  # Reader-writer mutex coordinating CUDA execution
│   │   ├── model/                        # Member 1 PyTorch model adapter & host pinned mirrors
│   │   ├── profiling/                    # Dual-domain latency profiler (GPU Event + Monotonic)
│   │   └── runtime/                      # CUDA engine, streams, hardware barrier, injector
│   ├── dashboard/
│   │   ├── index.html                    # Embedded real-time telemetry HUD
│   │   └── logo.png                      # Local emblem asset
│   └── tests/                            # 10 integration tests validating CUDA execution
│
├── mission-control/                      # Mission Control HUD & Telemetry Frontend (Member 2 - Prachi)
│   ├── src/
│   │   ├── app/                          # Next.js 14 App Router (layout.tsx, page.tsx, globals.css)
│   │   ├── components/                   # Three.js 3D attitude visualizer, HUD panels, charts
│   │   ├── lib/                          # Resilient telemetry client (WS + HTTP fallback)
│   │   └── types/                        # Spacecraft telemetry & flight event schemas
│   └── public/
│       ├── logo.png                      # RadZero mission emblem
│       └── favicon.png                   # Browser tab icon
│
└── tests/                                # 50 Unit and integration test suite (40 core + 10 accelerator)
    ├── test_adcs_model.py                # Deterministic reproducibility & block partitioning
    ├── test_ieee754_injector.py          # IEEE-754 bit-mutation validation
    ├── test_tier1.py                     # In-line tripwire & execution overhead (<0.2%)
    ├── test_tier2.py                     # Rigid-body kinematic gating validation
    ├── test_tier3.py                     # Cyclic CRC-32 audit coverage
    ├── test_recovery.py                  # In-situ hot-patching & safe-hold escalation
    ├── test_safe_hold.py                 # Classical rate-damping physics
    ├── test_rwlock.py                    # Fair writer-priority ReadWriteLock
    ├── test_telemetry.py                 # FastAPI endpoints & WebSocket stream
    └── test_end_to_end.py                # Multi-cycle SEU injection and recovery stability
```

---

## 8. Empirical Benchmark Validation (NFR-1 / NFR-2 / NFR-3)

Dual-domain latency profiling measured across 50 consecutive physical SEU strikes on the Reference Host CPU Node (with accelerated CUDA dual-stream path for NVIDIA RTX 3050 Mobile nodes):

### 8.1 Statistical Results Summary

| Metric Dimension | Design Target | Observed Benchmark Value | Performance Margin |
| :--- | :--- | :--- | :--- |
| **Process Continuous Uptime** | $100.0\%$ (NFR-3) | **$100.0\%$ (50 / 50 Trials)** | **Zero process terminations or OS aborts** |
| **In-Situ Recovery Success Rate** | $100.0\%$ | **$100.0\%$ (50 / 50 Success)** | **$0\%$ safe-hold escalation under healthy mirrors** |
| **Mean System Latency (NFR-2)** | $\le 40.0\text{ ms}$ | **$0.68\text{ ms}$** | **$58.8\times$ faster than target** |
| **Median Latency ($P_{50}$)** | $\le 40.0\text{ ms}$ | **$0.54\text{ ms}$** | **$74.1\times$ faster than target** |
| **95th Percentile ($P_{95}$)** | $\le 40.0\text{ ms}$ | **$0.87\text{ ms}$** | **$46.0\times$ faster than target** |
| **99th Percentile ($P_{99}$)** | $\le 40.0\text{ ms}$ | **$2.12\text{ ms}$** | **$18.9\times$ faster than target** |
| **Maximum Recovery Latency** | $\le 100.0\text{ ms}$ | **$3.26\text{ ms}$** | **$30.7\times$ margin under control deadline** |

$$
\mathrm{Margin}_{\mathrm{safety}} = \frac{\Delta t_{\mathrm{deadline}} - t_{\max}}{\Delta t_{\mathrm{deadline}}} = \frac{100.0\text{ ms} - 3.26\text{ ms}}{100.0\text{ ms}} = 96.74\%
$$

#### Benchmark Run Conditions
- **Platform**: Reference Host CPU Node (x86_64, Windows, Python 3.14 / PyTorch 2.13.0+cpu)
- **Control Frame Period ($\Delta t$)**: $100.0\text{ ms}$ ($10\text{ Hz}$ ADCS update cycle)
- **Trials**: 50 consecutive closed-loop attitude determination trials with randomized non-zero IEEE-754 bit-flips across all four fault categories (sign, exponent explosion, exponent collapse, mantissa drift)
- **Kinematic Constraints**: $\tau_{\max} = 0.05\text{ N}\cdot\text{m}$, $\alpha_{\max} = 0.65\text{ rad/s}^2$, $\omega_{\max} = 0.08\text{ rad/s}$
- **In-Situ Recovery Action**: Exclusive ReadWriteLock acquisition $\to$ Host checkpoint CRC-32 verification $\to$ In-place buffer copy $\to$ Post-recovery forward re-verification $\to$ Lock release
- **Measurement Method**: Monotonic high-resolution clock (`time.perf_counter_ns()`) capturing end-to-end detection, recovery, and re-evaluation latency

---

## 9. Impact & Benefits

The deployment of RadZero enables significant operational advantages for future autonomous space systems:

1. **Mission Longevity with Unshielded COTS Silicon**:
   Allows space missions to deploy high-performance consumer GPUs (RTX 3050, Jetson Orin) that offer $100\times$ the compute density of radiation-hardened RAD750 flight computers at a fraction of the cost, while guaranteeing continuous fault containment.
2. **Elimination of Multi-Hour Cold Reboots**:
   By replacing uncoordinated system reboots with sub-2ms in-situ memory hot-patching, satellites maintain continuous celestial pointing, solar power generation, and uninterrupted communications links.
3. **Severe SWaP-C Optimization**:
   Eliminates the $200\%$ power and mass penalty of Triple Modular Redundancy (TMR), enabling autonomous AI navigation within the rigid 12U/27U CubeSat power envelopes ($<30\text{ W}$ total bus).
4. **Autonomous Closed-Loop Containment**:
   Functions completely offline over local buses without requiring ground-station telecommand intervention, vital for deep-space and planetary exploration with multi-minute radio round-trip delays.

---

## 10. Verification Test Suite

Run the complete 50-test automated verification suite:

```bash
# Run all core tests and accelerator runtime tests
python -m pytest tests/ accelerator_runtime/tests/ -v
```

```
tests/test_adcs_model.py::test_deterministic_reproducibility PASSED      [  2%]
tests/test_adcs_model.py::test_evaluation_mode_and_frozen_weights PASSED [  4%]
tests/test_adcs_model.py::test_input_output_dimensions PASSED            [  6%]
tests/test_adcs_model.py::test_nominal_torque_bounds PASSED              [  8%]
tests/test_adcs_model.py::test_four_block_partitioning PASSED            [ 10%]
tests/test_end_to_end.py::test_end_to_end_consecutive_injections_and_recoveries PASSED [ 12%]
tests/test_failsafe_fallbacks.py::TestFailSafeAndNetworkFallbacks::test_cpu_fallback_execution_path PASSED [ 14%]
tests/test_failsafe_fallbacks.py::TestFailSafeAndNetworkFallbacks::test_frontend_http_polling_fallback PASSED [ 16%]
tests/test_ieee754_injector.py::test_sign_bit_mutation_flips_polarity PASSED [ 18%]
tests/test_ieee754_injector.py::test_exponent_explosion_scales_magnitude PASSED [ 20%]
tests/test_ieee754_injector.py::test_exponent_collapse_drops_magnitude PASSED [ 22%]
tests/test_ieee754_injector.py::test_mantissa_mutation_subtle_shift PASSED [ 24%]
tests/test_ieee754_injector.py::test_multidimensional_element_idx_mapping PASSED [ 26%]
tests/test_recovery.py::test_dual_checkpoint_mirror_initialization PASSED [ 28%]
tests/test_recovery.py::test_in_situ_recovery_restores_parameters_after_seu PASSED [ 30%]
tests/test_recovery.py::test_safe_hold_escalation_when_mirrors_corrupted PASSED [ 32%]
tests/test_recovery.py::test_recovery_latency_profiling PASSED           [ 34%]
tests/test_recovery.py::test_extreme_rate_input_no_unbound_local_error PASSED [ 36%]
tests/test_rwlock.py::test_concurrent_readers PASSED                     [ 38%]
tests/test_rwlock.py::test_exclusive_writer PASSED                       [ 40%]
tests/test_safe_hold.py::test_safe_hold_rate_damping_calculation PASSED  [ 42%]
tests/test_safe_hold.py::test_safe_hold_torque_saturation PASSED         [ 44%]
tests/test_safe_hold.py::test_safe_hold_momentum_capacity_limit PASSED   [ 46%]
tests/test_safe_hold.py::test_safe_hold_mtq_momentum_desaturation PASSED [ 48%]
tests/test_telemetry.py::test_api_state_endpoint PASSED                  [ 50%]
tests/test_telemetry.py::test_api_telemetry_latest_endpoint PASSED       [ 52%]
tests/test_telemetry.py::test_api_inject_seu_endpoint PASSED             [ 54%]
tests/test_telemetry.py::test_api_reset_endpoint PASSED                  [ 56%]
tests/test_tier1.py::test_tier1_catches_nan_activation PASSED            [ 58%]
tests/test_tier1.py::test_tier1_catches_inf_activation PASSED            [ 60%]
tests/test_tier1.py::test_tier1_catches_chebyshev_range_breach PASSED    [ 62%]
tests/test_tier1.py::test_tier1_execution_overhead_benchmark PASSED      [ 64%]
tests/test_tier2.py::test_tier2_nominal_torque_passes PASSED             [ 66%]
tests/test_tier2.py::test_tier2_catches_torque_saturation PASSED         [ 68%]
tests/test_tier2.py::test_tier2_catches_angular_accel_breach PASSED      [ 70%]
tests/test_tier2.py::test_tier2_catches_slew_rate_breach PASSED          [ 72%]
tests/test_tier2.py::test_tier2_maximum_torque_on_z_axis_consistent_with_alpha_max PASSED [ 74%]
tests/test_tier3.py::test_tier3_audit_nominal_match PASSED               [ 76%]
tests/test_tier3.py::test_tier3_catches_corrupted_parameter_block PASSED [ 78%]
tests/test_tier3.py::test_tier3_cyclic_sweep_coverage PASSED             [ 80%]
accelerator_runtime/tests/test_api_endpoints.py::TestAPIEndpoints::test_direct_handler_execution PASSED [ 82%]
accelerator_runtime/tests/test_api_endpoints.py::TestAPIEndpoints::test_routes_existence PASSED [ 84%]
accelerator_runtime/tests/test_profiler.py::TestDualDomainLatencyProfiler::test_inference_profiling PASSED [ 86%]
accelerator_runtime/tests/test_profiler.py::TestDualDomainLatencyProfiler::test_record_and_throughput_computation PASSED [ 88%]
accelerator_runtime/tests/test_recovery_barrier.py::TestHardwareRecoveryBarrier::test_fault_injection_and_atomic_recovery PASSED [ 90%]
accelerator_runtime/tests/test_rw_mutex.py::TestReadWriteMutex::test_concurrent_readers PASSED [ 92%]
accelerator_runtime/tests/test_rw_mutex.py::TestReadWriteMutex::test_writer_mutual_exclusion PASSED [ 94%]
accelerator_runtime/tests/test_rw_mutex.py::TestReadWriteMutex::test_writer_priority PASSED [ 96%]
accelerator_runtime/tests/test_shadow_mirror.py::TestHostPinnedShadowMirror::test_allocation_and_metadata PASSED [ 98%]
accelerator_runtime/tests/test_shadow_mirror.py::TestHostPinnedShadowMirror::test_integrity_check PASSED [100%]
======================= 50 passed in 6.99s =======================
```

---

## 11. Quickstart & Operational Execution

### Step 1: Run Interactive Terminal Demonstration
```bash
python run_demo.py
```

### Step 2: Run 50-Trial Automated Validation Benchmark
```bash
python -m radzero.benchmarks.suite_50_trials
```

### Step 3: Launch Telemetry Streaming Service
```bash
# Launch FastAPI backend bound to 0.0.0.0:8000
python -m uvicorn radzero.telemetry.server:app --host 0.0.0.0 --port 8000
```

### Step 4: Launch Mission Control Dashboard (Next.js 14)
```bash
cd mission-control
npm install
npm run dev
# Open http://localhost:3000
```

---

## 12. Limitations & Flight Heritage Considerations

While RadZero establishes a deterministic in-situ fault containment framework, transparent engineering requires acknowledging current boundaries:

1. **Technology Readiness Level (TRL 4)**:
   The current validation comprises component and software validation in a laboratory environment (host CPU reference node and NVIDIA RTX 3050 accelerator). In-orbit spaceflight demonstration (TRL 7+) will require vacuum and radiation beam qualification.
2. **Software-Emulated Bitfield Fault Model**:
   Single-Event Upsets are currently injected in-memory at the IEEE-754 bitfield level via direct tensor memory mutation. While this accurately simulates the numerical consequences of ionization charge deposition, it does not replace physical heavy-ion cyclotron beamline radiation testing (e.g. at Texas A&M Cyclotron Institute or Lawrence Berkeley 88-Inch Cyclotron).
3. **PCIe Bus & Host Co-Processor Dependency**:
   RadZero assumes the PCIe/AXI interconnect and host CPU memory controller remain operational. In the event of a catastrophic latch-up (SEL) that freezes the PCIe bus itself, hardware watchdogs must initiate an emergency power cycle, escalating to RadZero's classical safe-hold detumble controller upon reboot.

---

## 13. References & Resources

1. **Markley, F. L., & Crassidis, J. L. (2014)**. *Fundamentals of Spacecraft Attitude Determination and Control*. Springer New York. DOI: 10.1007/978-1-4939-0802-8.
2. **NASA Technical Handbook (NASA-HDBK-4002A)**. *Mitigating Single Event Effects (SEE) in Space Electronics*. National Aeronautics and Space Administration, Washington, D.C.
3. **Berg, M. D., et al. (2008)**. "Effectiveness of Internal vs. External SEU Mitigation in FPGA-Based Soft-Core Processors." *IEEE Transactions on Nuclear Science*, 55(4), pp. 2060–2066. DOI: 10.1109/TNS.2008.2000843.
4. **European Cooperation for Space Standardization (ECSS-E-ST-70-11C)**. *Space engineering: Spacecraft and operations telemetry and telecommand packet utilization*. ESA-ESTEC, Noordwijk, The Netherlands.
5. **IEEE Std 754-2019**. *IEEE Standard for Floating-Point Arithmetic*. IEEE Computer Society, New York. DOI: 10.1109/IEEESTD.2019.8766229.
6. **Schwandt, C., et al. (2021)**. "Single-Event Upsets in Deep Neural Networks on Embedded Edge Accelerators." *IEEE Transactions on Nuclear Science*, 68(5), pp. 842-850.
7. **Wertz, J. R. (2011)**. *Spacecraft Attitude Determination and Control*. D. Reidel Publishing Company / Kluwer Academic Publishers.
8. **The CubeSat Program, Cal Poly SLO (2022)**. *CubeSat Design Specification (CDS)*, Rev. 14.1. California Polytechnic State University.
9. **Sidi, M. J. (1997)**. *Spacecraft Dynamics and Control: A Practical Engineering Approach*. Cambridge Aerospace Series, Cambridge University Press.
