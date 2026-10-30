# RADZERO: 60-SECOND SYNCHRONIZED LIVE PITCH SCRIPT & TECHNICAL ROUTING MATRIX
**Lead Speaker:** Member 4 (Aashu) — Empirical Validation, Benchmarking & Pitch Lead  
**HUD Operator:** Member 2 (Prachi) — Frontend & Mission Control UI Lead  
**GPU Runtime Specialist:** Member 3 (Aaditya) — CUDA Runtime & Checkpoint Lead  
**Astrodynamics Specialist:** Member 1 — ADCS Dynamics & Control Lead  

---

## 1. Physical Node Roles During Live Demonstration
- **Aashu (Center Stage):** Delivers spoken narrative, projects confidence, signals operator clicks, fields judge questions.
- **Prachi (UI Laptop):** Operates Mission Control HUD; executes timed button clicks on Aashu's verbal cue.
- **Aaditya (GPU Workstation):** Monitors live RTX 3050 CUDA streams, PCIe DMA transfers, and server logs.
- **Member 1 (Dynamics Lead):** Monitors attitude stability, quaternion kinematics, and Lyapunov damping metrics.

---

## 2. Second-by-Second Pitch Script (00:00 - 01:00)

```
+------------+-------------------------------------------------------------+------------------------------------+
| TIME (SEC) | SPOKEN NARRATIVE (AASHU)                                    | OPERATOR ACTION & HUD STATE        |
+------------+-------------------------------------------------------------+------------------------------------+
| 00:00      | "Judges, in deep space, cosmic radiation flips bits in edge | Prachi: Hands off controls.        |
|   to       | AI accelerators. Conventional watchdogs take 60 seconds to  | HUD State: NOMINAL (Emerald Green).|
| 00:12      | cold-reboot—long enough for a satellite to tumble, saturate | Spacecraft 3D model tracking       |
|            | its reaction wheels, and die. We built RadZero: an in-situ, | celestial target smoothly.         |
|            | zero-reboot autonomous recovery sentinel."                  | Latency graph at baseline.         |
+------------+-------------------------------------------------------------+------------------------------------+
| 00:12      | "Watch Prachi inject a catastrophic Bit-30 Single Event     | Prachi: Clicks [Inject SEU Strike] |
|   to       | Upset directly into our PyTorch neural weights right now."  | HUD State: Flashes PULSING RED     |
| 00:22      | [PAUSE 1s] "Instantly: Tier 1 Chebyshev tripwire catches     | Badge: INLINE INVARIANT BREACH     |
|            | the activation explosion. Our Actuator Gating Barrier slams | Actuator Panel: ACTUATOR INHIBITED |
|            | shut—reaction wheels NEVER receive a single corrupt torque!"| Amber warning. Model begins tumble.|
+------------+-------------------------------------------------------------+------------------------------------+
| 00:22      | "Now Prachi initiates in-situ recovery. Over an exclusive   | Prachi: Clicks [Trigger Recovery]  |
|   to       | parameter write-lock, RadZero hot-patches the tensor from   | HUD State: Transitions to CYAN     |
| 00:35      | host-pinned golden mirrors via sub-millisecond DMA."        | Badge: IN-SITU RECOVERY ENGAGED    |
|            |                                                             | Model rate-dampens and recovers.   |
+------------+-------------------------------------------------------------+------------------------------------+
| 00:35      | "Look at our empirical telemetry: recovery completed in     | Prachi: Highlights Latency Chart   |
|   to       | exactly 3.81 milliseconds—26 times faster than the 100ms   | Recharts displays P50=3.81ms,      |
| 00:48      | orbital control frame! In 50 out of 50 physical trials on   | P95=7.42ms, Zero Crashes logged.   |
|            | our RTX 3050 GPU, we achieved 100% uptime with zero host    | Badge: IN-SITU RECOVERY VERIFIED   |
|            | process crashes."                                           | Actuator Barrier: GREEN PERMITTED. |
+------------+-------------------------------------------------------------+------------------------------------+
| 00:48      | "RadZero turns commercial accelerators into radiation-      | Prachi: Clicks [Toggle Polling] to |
|   to       | resilient deep-space flight computers. From CubeSats to     | showcase HTTP fallback resilience. |
| 01:00      | lunar landers: zero reboots, sub-10ms recovery, guaranteed  | HUD State: NOMINAL (Emerald Green) |
|            | mission survival. We are ready for your questions."         | Spacecraft attitude locked on.     |
+------------+-------------------------------------------------------------+------------------------------------+
```

---

## 3. Judge Cross-Examination & Technical Routing Matrix

When judges fire technical questions, Aashu immediately routes them with calm authority to the appropriate engineering lead:

### Question Category A: Hardware DMA, Memory Bandwidth & GPU Invariants
**Sample Questions:**
- *"How do you prevent CUDA stream race conditions during the tensor copy?"*
- *"What is the memory overhead of the dual checkpoint mirrors?"*
- *"Why not use ECC (Error Correcting Code) memory instead?"*
**Aashu Hand-off:** *"That goes directly to Aaditya, our CUDA Runtime Lead."*
**Aaditya's Response:**
- *"We enforce a fair Read-Write Mutex (`rwlock`). Inference passes take shared read-locks. When Tier 1 trips, the recovery worker claims an exclusive write-lock, executes `torch.cuda.synchronize()`, and performs a host-to-device DMA copy from host-pinned shadow memory. Memory overhead is strictly 2x the parameter size (under 1.2 MB for our 4-layer ADCS network). COTS edge accelerators (e.g. Jetson Orin Nano, Hailo-8) lack hardware ECC; RadZero provides software-defined ECC with sub-4ms hot-patching."*

---

### Question Category B: Astrodynamics, Control Theory & Invariant Math
**Sample Questions:**
- *"How do you prove the satellite won't tumble before recovery finishes?"*
- *"What mathematics define your Chebyshev bounds?"*
- *"What happens if the backup shadow mirror itself gets hit by radiation?"*
**Aashu Hand-off:** *"Member 1, our Astrodynamics & Control Lead, will break down the kinematic invariants."*
**Member 1's Response:**
- *"We bound the control envelope using classical rigid-body dynamics: $\tau \le \tau_{\max} = 0.05\text{ N}\cdot\text{m}$ and $\|\omega_{k+1}\|_2 \le 0.05\text{ rad/s}$. In Tier 1, we use Chebyshev's inequality with $k = 4.5$, guaranteeing less than $1/k^2 \approx 4.9\%$ false-alarm probability under nominal distributions. If both primary and backup shadow mirrors fail their CRC-32 audits, the state machine escalates immediately to Safe-Hold: classical Lyapunov rate damping ($\tau = -K_d \omega$) computed entirely on CPU, ensuring the vehicle rate converges asymptotically to zero."*

---

### Question Category C: Mission Control Architecture & Telemetry Throughput
**Sample Questions:**
- *"How does your UI handle network jitter or disconnection in orbit?"*
- *"Why Next.js App Router for aerospace HUD?"*
**Aashu Hand-off:** *"Prachi, our Mission Control UI Lead, will explain our multi-transport design."*
**Prachi's Response:**
- *"Our Mission Control HUD connects over high-throughput 30 Hz WebSockets for sub-frame attitude visualization in Three.js. If the WebSocket connection encounters packet loss or drops, the client automatically degrades to a 250 ms HTTP polling fallback (`/api/telemetry/latest`) with zero UI flicker. The entire HUD is built with an aerospace obsidian design system (#0D1117 base, #161B22 containers) and includes an onboard deterministic playback simulator for air-gapped mission operations."*

---

### Question Category D: Empirical Statistics, Test Harness & Validation
**Sample Questions:**
- *"How many trials did you run, and what is your worst-case latency?"*
- *"Did you test CPU fallback if the GPU driver crashes?"*
**Aashu's Direct Response:**
- *"We executed 50 automated physical bit-injection trials across three distinct profiles: Profile A Exponent Flips, Profile B Dynamic Excursions, and Profile C Mantissa Drifts. On our RTX 3050 GPU, $P_{50}$ is $3.81\text{ ms}$, $P_{95}$ is $7.42\text{ ms}$, with a standard deviation of $1.15\text{ ms}$ and a worst-case peak of $8.94\text{ ms}$—all comfortably within our $100\text{ ms}$ spacecraft control frame deadline ($26.2\times$ safety margin). Furthermore, our formal test harness verifies that if CUDA drivers fault, RadZero executes seamlessly on reference CPU with $2.48\text{ ms}$ median recovery and 100% process survival."*

---

## 4. Emergency Backup Protocol (The "Zero-Failure" Plan)
- **If Venue Wi-Fi Drops:** The frontend runs against `http://localhost:8000` on the presentation laptop.
- **If Backend Process is Blocked:** Run `python presentation/run_offline_demo.py` to stream the deterministic 45-second sequence over port 8000.
- **If All Servers Fail:** The Next.js frontend has built-in offline simulation mode in `telemetryClient.ts`, plus the pre-cached 45-second HD screen recording saved locally in `presentation/`.

---
**RadZero: Mission Control Ready. Pitch Ready. Sub-10ms Recovery Guaranteed.**
