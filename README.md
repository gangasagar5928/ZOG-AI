# RadZero: Experimental In-Situ Fault-Tolerant Inference Runtime for Embedded Edge AI

**Document Version:** 2.3.0-FROZEN  
**System Classification:** Experimental In-Situ Fault-Tolerant Inference Runtime for Embedded Edge AI  
**Deployment Target:** Dual-Node COTS Edge Architecture (Primary Node: NVIDIA GeForce RTX 3050 Mobile / Secondary Node: Reference x86-64 Host)  
**Track Alignment:** Problem Statement 31 (Open Innovation), GRAVITON 2026, CGC University  

---

## 1. Executive Summary & Problem Scope

Operating Commercial Off-The-Shelf (COTS) edge accelerators (such as mobile GPUs and embedded NPUs) in space radiation environments exposes volatile semiconductor memory to ionizing cosmic rays and solar particle events, inducing **Single-Event Upsets (SEUs)**.

In deep neural networks executing Attitude Determination and Control Systems (ADCS), stochastic bit-flips in IEEE-754 single-precision (FP32) tensors cause **Silent Data Corruption (SDC)**:
* **Exponent-bit transitions ($0 \to 1$):** Scale numerical values by up to $2^{+128} \approx 3.40 \times 10^{38}$, causing immediate `NaN` or `inf` cascades.
* **Exponent-bit transitions ($1 \to 0$):** Collapse numerical values by up to $2^{-128} \approx 2.94 \times 10^{-39}$, dropping weights into subnormal or zeroed regimes that sever operational channels.
* **Sign-bit flips (Bit 31):** Invert actuation polarity, driving spacecraft actuators in opposite directions and causing kinetic spin-up.

Standard aerospace recovery relies on uncoordinated system power cycles and multi-hour cold reboots, leading to mission loss. **RadZero** is an experimental software-defined runtime sentinel that guards the neural execution graph in volatile accelerator memory. By coupling in-line activation tripwires, rigid-body kinematic physical gates, concurrency-safe in-situ tensor hot-patching, and asynchronous background memory auditing, RadZero inhibits anomalous commands and restores operational weights without terminating host processes or triggering system reboots.

---

## 2. Multi-Tier Fault Defense Architecture

```
[ Kinematic State Vector: Error Quaternion (q_e), Angular Velocity (omega) ]
                                    │
               (Shared Parameter Read Lock Acquired)
                                    ▼
       [ PyTorch Inference Graph: Deterministic ADCS Model ]
                                    │
                                    ▼
           [ Tier 1: In-Line Activation Invariant Tripwire ]
           • Finite value evaluation: isnan(), isinf()
           • Dynamic Chebyshev layer-wise numerical range limits
                                    │
                       Invariant Breach Detected?
                         ├── YES ──► [ INITIATE IN-SITU RECOVERY ]
                         └── NO
                                    │
                                    ▼
           [ Tier 2: Rigid-Body Dynamic & Actuator Gate ]
           • Actuator torque saturation: ||tau_cmd||_inf <= tau_max (0.05 N*m)
           • Dynamic angular acceleration: ||alpha||_2 <= alpha_max (0.5 rad/s^2)
             where alpha = I^-1 [ tau_cmd - omega x (I * omega) ]
           • Slew-rate integration: ||omega_(k+1)||_2 <= omega_max (0.05 rad/s)
             where omega_(k+1) = omega_k + alpha * Delta_t (Delta_t = 100 ms)
                                    │
                         Kinematic Bounds Satisfied?
                         ├── NO  ──► [ INITIATE IN-SITU RECOVERY ]
                         └── YES
                                    │
                                    ▼
                  [ Dispatch Command to Actuator Bus ]

─────────────────────────────────────────────────────────────────────────
[ Background Slack Time: Tier 3 Asynchronous Parameter Scrubber ]
• Soft real-time cyclic audit of 1 tensor block per 100 ms idle window
• Algebraic CRC-32-IEEE 802.3 verification against protected host mirrors
• Full-model sweep period: T_scrub = 400 ms (nominal 4-block partition)
• Detects input-masked faults and sub-threshold parameter drift
```

---

## 3. Subsystem Implementation Overview

### FR-1: Deterministic ADCS Control Model (`radzero.core.adcs_model`)
* Maps 7-element state input (quaternion $\mathbf{q}_e \in \mathbb{R}^4$, body angular velocity $\boldsymbol{\omega} \in \mathbb{R}^3$) to 3 commanded reaction-wheel torques ($\boldsymbol{\tau}_{\text{cmd}} \in \mathbb{R}^3$).
* Strictly deterministic floating-point operations (`CUBLAS_WORKSPACE_CONFIG=:4096:8`, `torch.use_deterministic_algorithms(True)`).
* Frozen weights (`param.requires_grad = False`) and explicit evaluation mode (`model.eval()`, `torch.inference_mode()`).
* Partitioned into 4 explicit parameter blocks (`block0_fc1`, `block1_fc2`, `block2_fc3`, `block3_fc4`) for cyclic scrubbing.

### FR-2: IEEE-754 FP32 In-Memory Bit-Mutation Harness (`radzero.mutation.ieee754_injector`)
* In-place bitfield manipulation directly on raw tensor storage:
  * **Sign Bit (Bit 31):** Flips sign bit, reversing torque polarity.
  * **Exponent Bits (Bits 30–23):** Induces exponential dynamic range explosion ($0 \to 1$) or collapse to subnormal/zero regimes ($1 \to 0$).
  * **Mantissa Bits (Bits 22–0):** Injects subtle, in-bounds precision shifts.

### FR-3: Multi-Tier Anomaly Detection (`radzero.invariants`)
* **Tier 1 (In-Line Tripwire):** PyTorch forward-pass hooks evaluating activations for non-finite entries (`isnan`, `isinf`) and Chebyshev dynamic range limits ($|\mathbf{a} - \boldsymbol{\mu}| \le k\boldsymbol{\sigma}$) with $<5\%$ execution overhead.
* **Tier 2 (Rigid-Body Physical Gate):** Validates commanded torques against spacecraft physical dynamics over $\Delta t = 100\text{ ms}$:
  * Saturation: $\|\boldsymbol{\tau}_{\text{cmd}}\|_\infty \le \tau_{\max} = 0.05\text{ N}\cdot\text{m}$.
  * Angular Acceleration: $\dot{\boldsymbol{\omega}} = \mathbf{I}^{-1}[\boldsymbol{\tau}_{\text{cmd}} - \boldsymbol{\omega} \times (\mathbf{I}\boldsymbol{\omega})]$ with $\|\dot{\boldsymbol{\omega}}\|_2 \le \alpha_{\max} = 0.5\text{ rad/s}^2$.
  * Integrated Slew-Rate: $\boldsymbol{\omega}_{k+1} = \boldsymbol{\omega}_k + \dot{\boldsymbol{\omega}}\Delta t$ with $\|\boldsymbol{\omega}_{k+1}\|_2 \le \omega_{\max} = 0.05\text{ rad/s}$.
* **Tier 3 (Asynchronous Idle Scrubber):** Audits 1 tensor block per 100 ms idle window ($\le 15\text{ ms}$ execution budget) using CRC-32-IEEE 802.3 digests against host-pinned shadow mirrors. Full-model sweep period: $T_{\text{scrub}} = 400\text{ ms}$.

### FR-4: Concurrency-Safe In-Situ Hot-Patching (`radzero.core.rwlock`, `radzero.recovery`)
* Parameter Read-Write Mutex: Shared read lock for deterministic inference; exclusive write lock for recovery.
* Device synchronization (`torch.cuda.synchronize()`) drains active accelerator streams.
* In-place memory replacement (`param.data.copy_()`) from host-pinned shadow mirrors without reallocating tensor memory or restarting processes.

### FR-5: Post-Recovery Re-Verification & Safe-Hold Escalation
* Following hot-patching, re-runs forward pass and evaluates Tier 1 and Tier 2.
* Transitions to `SAFE_HOLD` if:
  * Recovery latency breaches $100\text{ ms}$ control deadline.
  * Both primary and backup host shadow mirrors fail CRC-32 integrity checks.
  * Re-evaluated forward pass fails Tier 1 or Tier 2.
* Safe-hold engages hard-coded proportional rate damping ($\boldsymbol{\tau}_{\text{safe}} = -K_d \boldsymbol{\omega}$), with telemetry logging torque saturation ($\tau_{\max}$) and reaction-wheel momentum storage capacity limits ($h_{\max}$).

### FR-6: Distributed Telemetry Streaming (`radzero.telemetry.server`)
* FastAPI service streaming 30 Hz JSON telemetry packets over WebSockets (`/ws/telemetry`) to Next.js Mission Control dashboard.
* HTTP polling fallback (`/api/telemetry/latest`) every 250 ms.
* Endpoints for fault injection (`POST /api/inject_seu`), state query (`GET /api/state`), and reset (`POST /api/reset`).

---

## 4. Empirical Benchmark Validation (NFR-1 / NFR-2 / NFR-3)

Ran automated 50-trial benchmark suite (`radzero.benchmarks.suite_50_trials`):

| Metric | Target Specification | Empirical Result (CPU Node) | Margin |
| :--- | :--- | :--- | :--- |
| **Process Uptime (NFR-3)** | 100% (Zero Process Terminations) | **100.0%** | **PASSED** (50/50 trials without crash) |
| **In-Situ Recovery Success** | > 99.0% | **100.0%** | **PASSED** |
| **Mean System Latency (NFR-2)** | $\le 40.0\text{ ms}$ | **1.06 ms** | **37.7x faster than deadline** |
| **Median (P50) Latency** | $\le 40.0\text{ ms}$ | **0.89 ms** | **44.9x faster than deadline** |
| **95th Percentile (P95)** | $\le 40.0\text{ ms}$ | **2.31 ms** | **17.3x faster than deadline** |
| **Maximum Recovery Latency** | $\le 100.0\text{ ms}$ | **3.81 ms** | **26.2x margin under control deadline** |

---

## 5. Verification Test Suite

32 unit and integration tests covering all subsystems:

```bash
$env:PYTHONPATH="."
python -m pytest tests/ -v
```

Output:
```
============================= test session starts =============================
tests/test_adcs_model.py::test_deterministic_reproducibility PASSED      [  3%]
tests/test_adcs_model.py::test_evaluation_mode_and_frozen_weights PASSED [  6%]
tests/test_adcs_model.py::test_input_output_dimensions PASSED            [  9%]
tests/test_adcs_model.py::test_nominal_torque_bounds PASSED              [ 12%]
tests/test_adcs_model.py::test_four_block_partitioning PASSED            [ 15%]
tests/test_end_to_end.py::test_end_to_end_consecutive_injections_and_recoveries PASSED [ 18%]
tests/test_ieee754_injector.py::test_sign_bit_mutation_flips_polarity PASSED [ 21%]
tests/test_ieee754_injector.py::test_exponent_explosion_scales_magnitude PASSED [ 25%]
tests/test_ieee754_injector.py::test_exponent_collapse_drops_magnitude PASSED [ 28%]
tests/test_ieee754_injector.py::test_mantissa_mutation_subtle_shift PASSED [ 31%]
tests/test_recovery.py::test_dual_checkpoint_mirror_initialization PASSED [ 34%]
tests/test_recovery.py::test_in_situ_recovery_restores_parameters_after_seu PASSED [ 37%]
tests/test_recovery.py::test_safe_hold_escalation_when_mirrors_corrupted PASSED [ 40%]
tests/test_recovery.py::test_recovery_latency_profiling PASSED           [ 43%]
tests/test_safe_hold.py::test_safe_hold_rate_damping_calculation PASSED  [ 46%]
tests/test_safe_hold.py::test_safe_hold_torque_saturation PASSED         [ 50%]
tests/test_safe_hold.py::test_safe_hold_momentum_capacity_limit PASSED   [ 53%]
tests/test_telemetry.py::test_api_state_endpoint PASSED                   [ 56%]
tests/test_telemetry.py::test_api_telemetry_latest_endpoint PASSED       [ 59%]
tests/test_telemetry.py::test_api_inject_seu_endpoint PASSED             [ 62%]
tests/test_telemetry.py::test_api_reset_endpoint PASSED                  [ 65%]
tests/test_tier1.py::test_tier1_catches_nan_activation PASSED            [ 68%]
tests/test_tier1.py::test_tier1_catches_inf_activation PASSED            [ 71%]
tests/test_tier1.py::test_tier1_catches_chebyshev_range_breach PASSED    [ 75%]
tests/test_tier1.py::test_tier1_execution_overhead_benchmark PASSED      [ 78%]
tests/test_tier2.py::test_tier2_nominal_torque_passes PASSED             [ 81%]
tests/test_tier2.py::test_tier2_catches_torque_saturation PASSED         [ 84%]
tests/test_tier2.py::test_tier2_catches_angular_accel_breach PASSED      [ 87%]
tests/test_tier2.py::test_tier2_catches_slew_rate_breach PASSED          [ 90%]
tests/test_tier3.py::test_tier3_audit_nominal_match PASSED               [ 93%]
tests/test_tier3.py::test_tier3_catches_corrupted_parameter_block PASSED [ 96%]
tests/test_tier3.py::test_tier3_cyclic_sweep_coverage PASSED             [100%]
======================= 32 passed in 6.94s =======================
```

---

## 6. Running the System

### Live Interactive Demonstration:
```bash
python run_demo.py
```

### 50-Trial Automated Benchmark Suite:
```bash
python -m radzero.benchmarks.suite_50_trials
```

### Telemetry Server (FastAPI + WebSockets):
```bash
uvicorn radzero.telemetry.server:app --host 0.0.0.0 --port 8000
```
* **WebSocket Stream:** `ws://localhost:8000/ws/telemetry` (30 Hz JSON packets)
* **HTTP Polling Fallback:** `http://localhost:8000/api/telemetry/latest`
* **Inject SEU Endpoint:** `POST http://localhost:8000/api/inject_seu`
* **Reset Endpoint:** `POST http://localhost:8000/api/reset`
