"""Professional Presentation Generator for RadZero Spacecraft Edge AI Runtime.

Generates a 12-slide 16:9 widescreen PowerPoint (.pptx) presentation:
- Aerospace Obsidian Design System (#0D1117 / #161B22 / #00F0FF / #00FF66 / #FFAA00)
- Inlines official RadZero emblem logo
- Comprehensive technical depth: problem, mathematical invariants, PAFC, 50-trial benchmarks, competitive matrix
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# Design System Colors
BG_COLOR = RGBColor(13, 17, 23)        # #0D1117 Obsidian
CARD_COLOR = RGBColor(22, 27, 34)      # #161B22 Container
BORDER_COLOR = RGBColor(48, 54, 61)    # #30363D Border
CYAN_ACCENT = RGBColor(0, 240, 255)    # #00F0FF Primary Accent
GREEN_ACCENT = RGBColor(0, 255, 102)   # #00FF66 Success / Invariant
AMBER_ACCENT = RGBColor(255, 170, 0)   # #FFAA00 Warning / SEU Threat
WHITE_TEXT = RGBColor(240, 246, 252)   # #F0F6FC High Contrast
MUTED_TEXT = RGBColor(139, 148, 158)   # #8B949E Secondary
DARK_BLUE = RGBColor(18, 30, 49)       # Accent Card Fill


def apply_background(slide, prs):
    """Fill slide background with Obsidian aerospace dark tone."""
    bg_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = BG_COLOR
    bg_shape.line.fill.background()  # No border
    return bg_shape


def add_header(slide, title_text, category_text="RADZERO ORBITAL FLIGHT SYSTEMS"):
    """Standardized top header with cyan accent line."""
    # Category / Pill
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.35))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category_text.upper()
    p_c.font.size = Pt(10)
    p_c.font.bold = True
    p_c.font.color.rgb = CYAN_ACCENT

    # Main Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.7))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title_text
    p_t.font.size = Pt(24)
    p_t.font.bold = True
    p_t.font.color.rgb = WHITE_TEXT

    # Subtle divider rule
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.45), Inches(11.7), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = BORDER_COLOR
    line.line.fill.background()


def add_card(slide, left, top, width, height, title="", border_color=BORDER_COLOR, fill_color=CARD_COLOR):
    """Draw a dark card container with optional border and title."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = fill_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.2)

    if title:
        tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.4))
        tf = tb.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = CYAN_ACCENT

    return card


def build_deck():
    prs = Presentation()
    # 16:9 Widescreen aspect ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    logo_path = os.path.join(project_root, "assets", "logo.png")

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    apply_background(s1, prs)

    # Logo if available
    if os.path.exists(logo_path):
        s1.shapes.add_picture(logo_path, Inches(1.0), Inches(1.8), width=Inches(3.8))

    # Title & Subtitle block
    t_box = s1.shapes.add_textbox(Inches(5.2), Inches(1.6), Inches(7.4), Inches(4.5))
    tf1 = t_box.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "PROBLEM STATEMENT 31 • EDGE AI RESILIENCE"
    p0.font.size = Pt(12)
    p0.font.bold = True
    p0.font.color.rgb = CYAN_ACCENT
    p0.space_after = Pt(12)

    p1 = tf1.add_paragraph()
    p1.text = "RadZero: Physics-Aware Fault Containment & In-Situ Recovery"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = WHITE_TEXT
    p1.space_after = Pt(12)

    p2 = tf1.add_paragraph()
    p2.text = "Autonomous Sub-10ms Fault Tolerance for Edge AI Spacecraft Attitude Control (ADCS)"
    p2.font.size = Pt(16)
    p2.font.color.rgb = MUTED_TEXT
    p2.space_after = Pt(24)

    p3 = tf1.add_paragraph()
    p3.text = "Flight Systems Engineering Team: Member 1 (ADCS Lead) • Member 2 - Prachi (UI Lead) • Member 3 - Aaditya (CUDA Lead) • Member 4 - Aashu (Validation & Pitch Lead)"
    p3.font.size = Pt(12)
    p3.font.color.rgb = GREEN_ACCENT

    # Badges at bottom
    add_card(s1, Inches(5.2), Inches(5.6), Inches(2.2), Inches(0.9), fill_color=DARK_BLUE, border_color=CYAN_ACCENT)
    b1 = s1.shapes.add_textbox(Inches(5.3), Inches(5.65), Inches(2.0), Inches(0.8))
    b1.text_frame.word_wrap = True
    bp1 = b1.text_frame.paragraphs[0]
    bp1.text = "P50 RECOVERY"
    bp1.font.size = Pt(9)
    bp1.font.color.rgb = MUTED_TEXT
    bp2 = b1.text_frame.add_paragraph()
    bp2.text = "3.81 ms"
    bp2.font.size = Pt(18)
    bp2.font.bold = True
    bp2.font.color.rgb = CYAN_ACCENT

    add_card(s1, Inches(7.6), Inches(5.6), Inches(2.2), Inches(0.9), fill_color=DARK_BLUE, border_color=GREEN_ACCENT)
    b2 = s1.shapes.add_textbox(Inches(7.7), Inches(5.65), Inches(2.0), Inches(0.8))
    b2.text_frame.word_wrap = True
    b2p1 = b2.text_frame.paragraphs[0]
    b2p1.text = "PROCESS UPTIME"
    b2p1.font.size = Pt(9)
    b2p1.font.color.rgb = MUTED_TEXT
    b2p2 = b2.text_frame.add_paragraph()
    b2p2.text = "100.0%"
    b2p2.font.size = Pt(18)
    b2p2.font.bold = True
    b2p2.font.color.rgb = GREEN_ACCENT

    add_card(s1, Inches(10.0), Inches(5.6), Inches(2.5), Inches(0.9), fill_color=DARK_BLUE, border_color=AMBER_ACCENT)
    b3 = s1.shapes.add_textbox(Inches(10.1), Inches(5.65), Inches(2.3), Inches(0.8))
    b3.text_frame.word_wrap = True
    b3p1 = b3.text_frame.paragraphs[0]
    b3p1.text = "DEADLINE MARGIN"
    b3p1.font.size = Pt(9)
    b3p1.font.color.rgb = MUTED_TEXT
    b3p2 = b3.text_frame.add_paragraph()
    b3p2.text = "26.2x Faster"
    b3p2.font.size = Pt(18)
    b3p2.font.bold = True
    b3p2.font.color.rgb = AMBER_ACCENT

    # =========================================================================
    # SLIDE 2: Executive Summary & Mission Problem
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    apply_background(s2, prs)
    add_header(s2, "Executive Summary: The Deep Space Computing Dilemma")

    # Left Column: The Problem
    add_card(s2, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.1), title="THE HAZARD: UNPROTECTED COTS SILICON", border_color=AMBER_ACCENT)
    tb = s2.shapes.add_textbox(Inches(1.0), Inches(2.3), Inches(5.3), Inches(4.3))
    tf = tb.text_frame
    tf.word_wrap = True
    items = [
        ("Ionizing Space Radiation", "Galactic Cosmic Rays (GCRs) and Van Allen Belt protons strike unshielded commercial accelerators (mobile GPUs, NPUs)."),
        ("Single-Event Upsets (SEUs)", "Radiation deposits charge directly into semiconductor registers, flipping bits inside active FP32 neural weights."),
        ("Silent Data Corruption (SDC)", "Corrupted weights produce NaN, Inf, or inverted torque commands, driving reaction wheels to catastrophic saturation (||h_RW|| > h_max)."),
        ("The Spacecraft Tumble", "Satellites lose attitude lock, solar panels de-point from the Sun, batteries drain, resulting in complete vehicle loss.")
    ]
    for idx, (title, desc) in enumerate(items):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = f"• {title}: "
        p.font.bold = True
        p.font.size = Pt(13)
        p.font.color.rgb = WHITE_TEXT
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = MUTED_TEXT
        p.space_after = Pt(10)

    # Right Column: The RadZero Solution
    add_card(s2, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.1), title="THE SOLUTION: RADZERO PAFC RUNTIME", border_color=GREEN_ACCENT)
    tb_r = s2.shapes.add_textbox(Inches(7.0), Inches(2.3), Inches(5.3), Inches(4.3))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    sol_items = [
        ("Physics-Aware Fault Containment", "Couples neural tensor integrity directly to rigid-body rotational equations of motion and reaction wheel physical limits."),
        ("Triple-Tier Invariant Sentinels", "In-line Chebyshev dynamic tripwire (Tier 1), rigid-body kinematic gate (Tier 2), and cyclic background scrubber (Tier 3)."),
        ("Actuator Gating Barrier", "A mathematical interlock clamping corrupted commands before they reach physical thrusters or wheels."),
        ("In-Situ Sub-4ms Hot-Patching", "Restores corrupted tensors from host-pinned shadow mirrors over PCIe DMA in 3.81 ms with 100% process uptime (Zero Reboots).")
    ]
    for idx, (title, desc) in enumerate(sol_items):
        p = tf_r.paragraphs[0] if idx == 0 else tf_r.add_paragraph()
        p.text = f"✔ {title}: "
        p.font.bold = True
        p.font.size = Pt(13)
        p.font.color.rgb = CYAN_ACCENT
        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = MUTED_TEXT
        p.space_after = Pt(10)

    # =========================================================================
    # SLIDE 3: The Physics of IEEE-754 Bit Mutations
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    apply_background(s3, prs)
    add_header(s3, "Failure Mode Analysis: How an SEU Destroys ADCS Control")

    cards = [
        ("Sign Bit (Bit 31)", "REVERSED TORQUE POLARITY", "tau_cmd -> -tau_cmd", "Injects positive angular momentum feedback into the closed loop. Induces rapid rotational kinetic spin-up.", AMBER_ACCENT),
        ("Exponent Surge (Bits 30-23)", "OVERFLOW EXPLOSION", "Delta x = 2^+128 ~ 3.4e38", "Scales weight magnitude by 10^38. Propagates NaN / Inf cascade through activation layers. Saturates reaction wheels.", RGBColor(255, 68, 68)),
        ("Exponent Collapse (Bits 30-23)", "ZEROED SENSITIVITY", "Delta x = 2^-128 ~ 2.9e-39", "Collapses values to subnormal zero. Neural sensitivity is severed; spacecraft is non-responsive to external gravity disturbances.", RGBColor(255, 136, 0)),
        ("Mantissa Shift (Bits 22-0)", "LATENT PARAMETER DRIFT", "Small sub-threshold shift", "Evades static range bounds. Slowly accumulates pointing drift over orbits, breaking high-gain crosslink communications.", CYAN_ACCENT)
    ]
    card_w = Inches(2.7)
    for i, (b_title, b_sub, b_math, b_desc, col) in enumerate(cards):
        cx = Inches(0.8) + i * Inches(2.95)
        add_card(s3, cx, Inches(1.8), card_w, Inches(4.9), title=b_title, border_color=col)
        tb_c = s3.shapes.add_textbox(cx + Inches(0.15), Inches(2.5), card_w - Inches(0.3), Inches(4.0))
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True

        p1 = tf_c.paragraphs[0]
        p1.text = b_sub
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.space_after = Pt(8)

        p2 = tf_c.add_paragraph()
        p2.text = b_math
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = WHITE_TEXT
        p2.space_after = Pt(12)

        p3 = tf_c.add_paragraph()
        p3.text = b_desc
        p3.font.size = Pt(11)
        p3.font.color.rgb = MUTED_TEXT

    # =========================================================================
    # SLIDE 4: The Fatal Flaw of Watchdogs & Traditional Scrubbers
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    apply_background(s4, prs)
    add_header(s4, "The Aerospace Status Quo vs. RadZero")

    # Table comparing approaches
    table_shape = s4.shapes.add_table(5, 5, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    table = table_shape.table

    # Column widths
    table.columns[0].width = Inches(2.5)
    table.columns[1].width = Inches(2.3)
    table.columns[2].width = Inches(2.3)
    table.columns[3].width = Inches(2.3)
    table.columns[4].width = Inches(2.3)

    headers = ["Evaluation Metric", "Watchdog Cold Reboot", "Triple Modular Red. (TMR)", "Periodic Memory Scrubber", "RadZero (Our Project)"]
    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_BLUE
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = CYAN_ACCENT if c_idx == 4 else WHITE_TEXT

    rows_data = [
        ("Recovery Latency", "30 to 120 seconds", "Real-time (voting delay)", "10 to 60 seconds delay", "3.81 ms (P50 Verified)"),
        ("Actuator Bus Safety", "❌ Hazardous torques fire", "⚠️ Susceptible to voting flaws", "❌ Unsafe commands fire", "✔ Pre-dispatch dynamic gate"),
        ("Process Uptime (NFR-3)", "0% (Application crashes)", "100% (3 parallel GPUs)", "100% (delayed detection)", "100% (Zero Reboots)"),
        ("SWaP-C Overhead", "High downtime cost", "+200% Compute/Power (3x)", "Moderate background RAM", "<0.2% frame overhead, 1 GPU")
    ]
    for r_idx, r_vals in enumerate(rows_data):
        for c_idx, val in enumerate(r_vals):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_COLOR if c_idx < 4 else DARK_BLUE
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(11)
            p.font.bold = (c_idx == 4 or c_idx == 0)
            p.font.color.rgb = GREEN_ACCENT if c_idx == 4 else (WHITE_TEXT if c_idx == 0 else MUTED_TEXT)

    # =========================================================================
    # SLIDE 5: Physics-Aware Fault Containment (PAFC)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    apply_background(s5, prs)
    add_header(s5, "Architecture: Physics-Aware Fault Containment (PAFC)")

    # Flowchart Blocks
    flow_steps = [
        ("1. INGESTION", "Vehicle Kinematics\nx = [q_e, omega]", "Quaternion attitude and body rate sensors sampled at 30 Hz", CYAN_ACCENT),
        ("2. INFERENCE", "PyTorch Graph\ntau_cmd = M(x)", "Protected by shared parameter read-lock in inference_mode", WHITE_TEXT),
        ("3. TIER 1 GATE", "Chebyshev Tripwire\n||a - mu|| <= 4.5 sigma", "Zero-overhead in-line hooks detect NaN/Inf and explosions", GREEN_ACCENT),
        ("4. TIER 2 GATE", "Rigid-Body Dynamics\ntau <= tau_max, alpha <= alpha_max", "Validates torque against Euler equations of motion", GREEN_ACCENT),
        ("5. DISPATCH", "Actuator Command\ntau_verified -> Reaction Wheels", "Gating Barrier permits verified physical torque commands", CYAN_ACCENT)
    ]
    bw = Inches(2.2)
    for idx, (step_h, step_sub, step_body, col) in enumerate(flow_steps):
        bx = Inches(0.8) + idx * Inches(2.38)
        add_card(s5, bx, Inches(1.8), bw, Inches(3.2), title=step_h, border_color=col)
        tb_f = s5.shapes.add_textbox(bx + Inches(0.1), Inches(2.4), bw - Inches(0.2), Inches(2.5))
        tf_f = tb_f.text_frame
        tf_f.word_wrap = True

        p1 = tf_f.paragraphs[0]
        p1.text = step_sub
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.space_after = Pt(8)

        p2 = tf_f.add_paragraph()
        p2.text = step_body
        p2.font.size = Pt(10)
        p2.font.color.rgb = MUTED_TEXT

    # Bottom banner for In-Situ Recovery
    add_card(s5, Inches(0.8), Inches(5.2), Inches(11.7), Inches(1.6), title="IN-SITU RECOVERY & SAFE-HOLD ESCALATION", border_color=AMBER_ACCENT, fill_color=DARK_BLUE)
    tb_bot = s5.shapes.add_textbox(Inches(1.0), Inches(5.7), Inches(11.3), Inches(1.0))
    tf_b = tb_bot.text_frame
    tf_b.word_wrap = True
    pb = tf_b.paragraphs[0]
    pb.text = "Upon Invariant Breach: Parameter RW-Mutex claims exclusive write lock -> drains GPU CUDA streams via torch.cuda.synchronize() -> restores pristine weights from host-pinned shadow mirror via PCIe DMA -> re-verifies forward pass. If both mirrors fault, latches deterministic Safe-Hold (classical -Kd * omega rate damping) without process termination."
    pb.font.size = Pt(12)
    pb.font.color.rgb = WHITE_TEXT

    # =========================================================================
    # SLIDE 6: Triple-Tier Invariant Sentinels
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    apply_background(s6, prs)
    add_header(s6, "Defense-in-Depth: Triple-Tier Invariant Sentinels")

    tier_cards = [
        ("Tier 1: In-Line Activation Tripwire", "NEURAL GRAPH ENVELOPE", "Math: ||a_l - mu_l||_inf <= k * sigma_l (k = 4.5)", "Executes as PyTorch forward pre/post hooks. Inspects internal activation tensors for non-finite values (NaN/Inf) and dynamic envelope overflow. Negligible overhead (<0.05 ms).", CYAN_ACCENT),
        ("Tier 2: Rigid-Body Dynamics Gate", "ORBITAL RIGID-BODY LAWS", "Math: tau <= 0.05 N*m, alpha <= 0.02 rad/s^2, omega <= 0.05 rad/s", "Validates candidate torque using Euler's rotational equations of motion over delta_t = 100ms. Prevents reaction wheel momentum saturation (||h_RW|| <= 0.02 N*m*s) before command dispatch.", GREEN_ACCENT),
        ("Tier 3: Asynchronous Scrubber", "STORED PARAMETER AUDIT", "Math: CRC-32-IEEE 802.3 Hash Verification", "Runs during the 100ms control frame idle slack time. Cyclically verifies 1 parameter block per frame against golden host-pinned mirrors. Completes full network sweep every 400ms to catch latent faults.", AMBER_ACCENT)
    ]
    tw = Inches(3.7)
    for i, (t_title, t_sub, t_math, t_body, col) in enumerate(tier_cards):
        tx = Inches(0.8) + i * Inches(3.95)
        add_card(s6, tx, Inches(1.8), tw, Inches(4.9), title=t_title, border_color=col)
        tb_t = s6.shapes.add_textbox(tx + Inches(0.15), Inches(2.5), tw - Inches(0.3), Inches(4.0))
        tf_t = tb_t.text_frame
        tf_t.word_wrap = True

        p1 = tf_t.paragraphs[0]
        p1.text = t_sub
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.space_after = Pt(8)

        p2 = tf_t.add_paragraph()
        p2.text = t_math
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = WHITE_TEXT
        p2.space_after = Pt(12)

        p3 = tf_t.add_paragraph()
        p3.text = t_body
        p3.font.size = Pt(11)
        p3.font.color.rgb = MUTED_TEXT

    # =========================================================================
    # SLIDE 7: Actuator Gating Barrier & Safe-Hold
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    apply_background(s7, prs)
    add_header(s7, "Actuator Gating Barrier & Deterministic Safe-Hold")

    # Left: Gating Barrier Logic
    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.9), title="THE ACTUATOR GATING BARRIER", border_color=CYAN_ACCENT)
    tb_g = s7.shapes.add_textbox(Inches(1.0), Inches(2.4), Inches(5.3), Inches(4.1))
    tf_g = tb_g.text_frame
    tf_g.word_wrap = True

    g_points = [
        ("Pre-Dispatch Hardware Interlock", "Acts as a strict firewall between the AI inference runtime and the satellite's physical attitude actuators."),
        ("Binary Permitted / Inhibited States", "NOMINAL: Torque passes unimpeded.\nBREACH: Gating barrier clamps torque within < 0.1 ms to prevent hazardous thruster firings."),
        ("Zero Momentum Saturation Guarantee", "Guarantees that reaction wheels never encounter high-rate step spikes, maintaining angular momentum safety margin.")
    ]
    for idx, (gt, gd) in enumerate(g_points):
        p = tf_g.paragraphs[0] if idx == 0 else tf_g.add_paragraph()
        p.text = f"• {gt}: "
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = CYAN_ACCENT
        run = p.add_run()
        run.text = gd
        run.font.bold = False
        run.font.color.rgb = MUTED_TEXT
        p.space_after = Pt(12)

    # Right: Safe-Hold
    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9), title="DETERMINISTIC SAFE-HOLD ESCALATION", border_color=AMBER_ACCENT)
    tb_s = s7.shapes.add_textbox(Inches(7.0), Inches(2.4), Inches(5.3), Inches(4.1))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True

    s_points = [
        ("Classical Lyapunov Rate Damping", "tau_safe = -Kd * omega (Kd = 0.8 N*m*s/rad). Directly counteracts vehicle tumbling rates using simple, uncorruptible CPU arithmetic."),
        ("Magnetic Torquer Desaturation", "Activates B-Dot magnetic torquers to dump excess angular momentum into the planetary geomagnetic field."),
        ("Infinite Fault Tolerance (Zero Crashes)", "If multi-bit burst corrupts both shadow mirrors, the runtime latches Safe-Hold indefinitely without terminating the OS process.")
    ]
    for idx, (st, sd) in enumerate(s_points):
        p = tf_s.paragraphs[0] if idx == 0 else tf_s.add_paragraph()
        p.text = f"• {st}: "
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = AMBER_ACCENT
        run = p.add_run()
        run.text = sd
        run.font.bold = False
        run.font.color.rgb = MUTED_TEXT
        p.space_after = Pt(12)

    # =========================================================================
    # SLIDE 8: Multi-Node Hardware Architecture
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    apply_background(s8, prs)
    add_header(s8, "Distributed Dual-Node System Architecture")

    # Three Node Cards
    node_w = Inches(3.7)
    nodes = [
        ("Aaditya's GPU Node", "CUDA ACCELERATION WORKSTATION", "• Hardware: NVIDIA RTX 3050 Mobile\n• PyTorch 2.x CUDA 12.x C++ runtime\n• Dual host-pinned memory mirrors\n• FastAPI 30 Hz streaming engine\n• Physical IEEE-754 mutation injector\n• Low-latency PCIe DMA channel", CYAN_ACCENT),
        ("Prachi's UI Node", "MISSION CONTROL OBSIDIAN HUD", "• Hardware: Next.js 14 / TypeScript laptop\n• Three.js 3D attitude visualizer\n• Live threat overlays & badge states\n• Recharts latency & kinematic streams\n• Automated WebSocket-to-HTTP fallback\n• Air-gapped offline presentation mode", GREEN_ACCENT),
        ("Aashu's Validation Node", "EMPIRICAL BENCHMARK SUITE", "• Hardware: Reference CPU & Test Harness\n• 50-trial sequential benchmark validator\n• Cross-platform performance profiling\n• Cloudflare Tunnel integration\n• Automated fail-safe fallback tests\n• Verified 100% process survival logs", AMBER_ACCENT)
    ]
    for i, (n_title, n_sub, n_body, col) in enumerate(nodes):
        nx = Inches(0.8) + i * Inches(3.95)
        add_card(s8, nx, Inches(1.8), node_w, Inches(4.9), title=n_title, border_color=col)
        tb_n = s8.shapes.add_textbox(nx + Inches(0.15), Inches(2.5), node_w - Inches(0.3), Inches(4.0))
        tf_n = tb_n.text_frame
        tf_n.word_wrap = True

        p1 = tf_n.paragraphs[0]
        p1.text = n_sub
        p1.font.size = Pt(10)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.space_after = Pt(12)

        p2 = tf_n.add_paragraph()
        p2.text = n_body
        p2.font.size = Pt(12)
        p2.font.color.rgb = WHITE_TEXT

    # =========================================================================
    # SLIDE 9: Empirical Benchmark Results (50 Sequential Trials)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    apply_background(s9, prs)
    add_header(s9, "Empirical Validation: 50-Trial Benchmark Suite")

    # Table of verified numbers
    table_shape9 = s9.shapes.add_table(8, 4, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    table9 = table_shape9.table

    table9.columns[0].width = Inches(3.7)
    table9.columns[1].width = Inches(2.7)
    table9.columns[2].width = Inches(2.7)
    table9.columns[3].width = Inches(2.6)

    h9 = ["Validation Metric", "Aaditya's RTX 3050 GPU", "Reference CPU Node", "Aerospace Specification"]
    for c_idx, h_text in enumerate(h9):
        cell = table9.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = DARK_BLUE
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = CYAN_ACCENT if c_idx == 1 else WHITE_TEXT

    bench_rows = [
        ("Total Trials Executed", "50 / 50 (100.0%)", "50 / 50 (100.0%)", "50 consecutive cycles"),
        ("Process Uptime (Zero Crashes)", "100.0% (Zero Aborts)", "100.0% (Zero Aborts)", "Zero process exits (NFR-3)"),
        ("In-Situ Recovery Success", "100.0% (50/50 Recovered)", "100.0% (50/50 Recovered)", "> 99.0%"),
        ("Median Latency (P50)", "3.81 ms", "2.48 ms", "< 10.0 ms (NFR-1)"),
        ("95th Percentile Latency (P95)", "7.42 ms", "2.86 ms", "< 15.0 ms (NFR-1)"),
        ("Standard Deviation (sigma)", "1.15 ms", "0.36 ms", "Deterministic clustering"),
        ("Control Frame Safety Margin", "26.2x under 100ms deadline", "29.3x under 100ms deadline", "Guaranteed non-divergence")
    ]
    for r_idx, r_vals in enumerate(bench_rows):
        for c_idx, val in enumerate(r_vals):
            cell = table9.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = DARK_BLUE if c_idx == 1 else CARD_COLOR
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(11)
            p.font.bold = (c_idx == 1 or c_idx == 0)
            p.font.color.rgb = GREEN_ACCENT if (c_idx == 1 or c_idx == 2) else WHITE_TEXT

    # =========================================================================
    # SLIDE 10: Fail-Safe & Network Fallback Resilience
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    apply_background(s10, prs)
    add_header(s10, "Fail-Safe Engineering: Redundancy Across Drivers & Network")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.9), title="1. AUTOMATED CPU EXECUTION FALLBACK", border_color=GREEN_ACCENT)
    tb_c1 = s10.shapes.add_textbox(Inches(1.0), Inches(2.4), Inches(5.3), Inches(4.1))
    tf_c1 = tb_c1.text_frame
    tf_c1.word_wrap = True
    c1_items = [
        ("Driver Fault Containment", "If NVIDIA CUDA drivers fault, encounter illegal memory access, or power down, RadZero switches to CPU execution path."),
        ("Zero Host Aborts", "Model and unpinned host shadow mirrors execute directly on the host CPU with zero unhandled exceptions."),
        ("Empirically Verified", "Formally verified in tests/test_failsafe_fallbacks.py: CPU recovery latency = 2.93 ms (< 100 ms control frame deadline).")
    ]
    for idx, (ct, cd) in enumerate(c1_items):
        p = tf_c1.paragraphs[0] if idx == 0 else tf_c1.add_paragraph()
        p.text = f"✔ {ct}: "
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = GREEN_ACCENT
        run = p.add_run()
        run.text = cd
        run.font.bold = False
        run.font.color.rgb = MUTED_TEXT
        p.space_after = Pt(14)

    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9), title="2. HTTP POLLING TELEMETRY FALLBACK", border_color=CYAN_ACCENT)
    tb_c2 = s10.shapes.add_textbox(Inches(7.0), Inches(2.4), Inches(5.3), Inches(4.1))
    tf_c2 = tb_c2.text_frame
    tf_c2.word_wrap = True
    c2_items = [
        ("Multi-Transport Transport Fallback", "Mission Control defaults to 30 Hz WebSockets (/ws/telemetry) for smooth Three.js attitude tracking."),
        ("250ms HTTP Polling Fallback", "If network jitter drops WebSockets, telemetry client automatically drops to /api/telemetry/latest without losing state."),
        ("100% Schema Consistency", "All 10 essential HUD keys validated during network drops. Plus: Onboard deterministic simulation fallback if all servers drop.")
    ]
    for idx, (ct, cd) in enumerate(c2_items):
        p = tf_c2.paragraphs[0] if idx == 0 else tf_c2.add_paragraph()
        p.text = f"✔ {ct}: "
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = CYAN_ACCENT
        run = p.add_run()
        run.text = cd
        run.font.bold = False
        run.font.color.rgb = MUTED_TEXT
        p.space_after = Pt(14)

    # =========================================================================
    # SLIDE 11: Mission Control HUD Walkthrough
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    apply_background(s11, prs)
    add_header(s11, "Mission Control HUD: Aerospace Obsidian Interface")

    hud_cards = [
        ("3D Spacecraft Visualizer", "Three.js & WebGL rendering driven directly by live quaternion [q_w, q_x, q_y, q_z] and angular rate vector. Shows smooth tracking, tumbling on SEU, and rate-damping re-alignment.", CYAN_ACCENT),
        ("Dynamic Threat Badges", "Instant visual transition across 4 operational states: NOMINAL (Emerald), INLINE INVARIANT BREACH (Pulsing Red), ACTUATOR INHIBITED (Amber), and IN-SITU RECOVERY VERIFIED (Cyan).", GREEN_ACCENT),
        ("Live Kinematics & Latency", "Recharts components graphing real-time recovery latency distributions (P50, P95) and vehicle kinematic acceleration trends over scrolling millisecond event stream.", AMBER_ACCENT),
        ("Air-Gapped Offline Playback", "Cached 45-second deterministic playback dataset (1,350 frames) and lightweight streaming server ensuring 100% demo reliability under zero connectivity.", WHITE_TEXT)
    ]
    hw = Inches(5.7)
    for idx, (ht, hd, col) in enumerate(hud_cards):
        hx = Inches(0.8) if idx % 2 == 0 else Inches(6.8)
        hy = Inches(1.8) if idx < 2 else Inches(4.35)
        add_card(s11, hx, hy, hw, Inches(2.35), title=ht, border_color=col)
        tb_h = s11.shapes.add_textbox(hx + Inches(0.2), hy + Inches(0.65), hw - Inches(0.4), Inches(1.5))
        tf_h = tb_h.text_frame
        tf_h.word_wrap = True
        ph = tf_h.paragraphs[0]
        ph.text = hd
        ph.font.size = Pt(12)
        ph.font.color.rgb = MUTED_TEXT

    # =========================================================================
    # SLIDE 12: Mission Impact & Conclusion
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    apply_background(s12, prs)
    add_header(s12, "Space Mission Impact & Conclusion")

    # Big takeaway box
    add_card(s12, Inches(0.8), Inches(1.8), Inches(11.7), Inches(3.2), title="ENGINEERING BREAKTHROUGH SUMMARY", border_color=CYAN_ACCENT, fill_color=DARK_BLUE)
    tb_con = s12.shapes.add_textbox(Inches(1.1), Inches(2.5), Inches(11.1), Inches(2.3))
    tf_c = tb_con.text_frame
    tf_c.word_wrap = True

    c_points = [
        ("Sub-4ms Recovery Solved", "Eliminates the lethal 120-second satellite reboot blackout. In-situ DMA restores neural weights 26x faster than the 100ms control deadline."),
        ("Pure Software Certifiability", "Zero proprietary radiation-hardened hardware required. Deploys directly on commercial COTS accelerators (Jetson Orin, Snapdragon, Hailo-8)."),
        ("Mission Applicability", "Enables high-throughput AI on CubeSats, lunar landers, satellite constellations, and autonomous active debris removal probes.")
    ]
    for idx, (cpt, cpd) in enumerate(c_points):
        p = tf_c.paragraphs[0] if idx == 0 else tf_c.add_paragraph()
        p.text = f"✔ {cpt}: "
        p.font.bold = True
        p.font.size = Pt(13)
        p.font.color.rgb = CYAN_ACCENT
        run = p.add_run()
        run.text = cpd
        run.font.bold = False
        run.font.color.rgb = WHITE_TEXT
        p.space_after = Pt(10)

    # Bottom Contact & GitHub Bar
    add_card(s12, Inches(0.8), Inches(5.3), Inches(11.7), Inches(1.5), fill_color=CARD_COLOR, border_color=GREEN_ACCENT)
    tb_foot = s12.shapes.add_textbox(Inches(1.1), Inches(5.5), Inches(11.1), Inches(1.1))
    tf_foot = tb_foot.text_frame
    tf_foot.word_wrap = True
    pf1 = tf_foot.paragraphs[0]
    pf1.text = "RADZERO: ZERO PROCESS CRASHES • SUB-10MS IN-SITU RECOVERY • DETERMINISTIC SAFETY"
    pf1.font.size = Pt(14)
    pf1.font.bold = True
    pf1.font.color.rgb = GREEN_ACCENT

    pf2 = tf_foot.add_paragraph()
    pf2.text = "GitHub Repository: https://github.com/gangasagar5928/ZOG-AI.git  |  Live HUD: https://radzero.web.app"
    pf2.font.size = Pt(12)
    pf2.font.color.rgb = WHITE_TEXT

    # Output file paths
    out_dir = os.path.join(project_root, "presentation")
    os.makedirs(out_dir, exist_ok=True)
    out_pptx = os.path.join(out_dir, "RadZero_Orbital_AI_Presentation.pptx")
    prs.save(out_pptx)
    print(f"[SUCCESS] Generated 12-slide presentation: {out_pptx}")
    return out_pptx


if __name__ == "__main__":
    build_deck()
