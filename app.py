"""
QA Workflow Orchestrator - Streamlit Dashboard
-----------------------------------------------
Design philosophy:
1. Show the AI working first (agent pipeline)
2. Explain what it does second
3. Input form last

Single light theme. Clean. Purposeful.
Animation only when agents are actually running.
"""

import streamlit as st
import json
import os
import tempfile
import time
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="QA Workflow Orchestrator",
    page_icon="\U0001f9ea",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MAX_FREE_RUNS = 5

# ─────────────────────────────────────────
# Session State
# ─────────────────────────────────────────

def init_session_state():
    defaults = {
        "runs_used": 0,
        "current_result": None,
        "final_report": None,
        "html_report": None,
        "workflow_running": False,
        "show_review_gate": False,
        "reviewer_notes": "",
        "agent_statuses": {},
        "error_message": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ─────────────────────────────────────────
# CSS - Single light theme
# ─────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  * { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

  .main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }

  #MainMenu, footer, header { visibility: hidden; }

  /* ── Top nav ── */
  .top-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 3rem;
    border-bottom: 1px solid #e8edf2;
    background: #ffffff;
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .nav-logo {
    font-size: 1.1rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
  }

  .nav-logo span { color: #48a1aa; }

  .nav-badge {
    background: rgba(72,161,170,0.1);
    color: #48a1aa;
    border: 1px solid rgba(72,161,170,0.3);
    padding: 0.25rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  /* ── Agent pipeline section ── */
  .pipeline-section {
    background: #f8fafc;
    padding: 3rem 3rem 2.5rem;
    border-bottom: 1px solid #e8edf2;
  }

  .pipeline-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #48a1aa;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.4rem;
  }

  .pipeline-heading {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.3rem;
  }

  .pipeline-sub {
    font-size: 0.85rem;
    color: #64748b;
    margin-bottom: 2rem;
  }

  /* Judge agent */
  .judge-row {
    display: flex;
    justify-content: center;
    margin-bottom: 1rem;
  }

  .judge-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    background: #ffffff;
    border: 1.5px solid #48a1aa;
    border-radius: 50px;
    padding: 0.5rem 1.2rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: #48a1aa;
    box-shadow: 0 2px 12px rgba(72,161,170,0.12);
  }

  .judge-pill.running {
    animation: judge-pulse 1.2s ease-in-out infinite;
    background: rgba(72,161,170,0.06);
  }

  .judge-pill.passed {
    background: rgba(189,227,195,0.2);
    border-color: #5cb85c;
    color: #2d6a4f;
  }

  .judge-pill.warning {
    background: rgba(248,247,186,0.4);
    border-color: #f0ad4e;
    color: #7d6608;
  }

  @keyframes judge-pulse {
    0%, 100% { box-shadow: 0 2px 12px rgba(72,161,170,0.12); }
    50% { box-shadow: 0 2px 24px rgba(72,161,170,0.4); }
  }

  /* Connector line */
  .connector {
    display: flex;
    justify-content: center;
    margin-bottom: 1rem;
  }

  .connector-line {
    width: 1.5px;
    height: 24px;
    background: linear-gradient(to bottom, #48a1aa, #e8edf2);
  }

  /* Agent cards grid */
  .agents-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.75rem;
  }

  .agent-card {
    background: #ffffff;
    border: 1px solid #e8edf2;
    border-radius: 10px;
    padding: 1rem 0.8rem;
    text-align: center;
    transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s;
    position: relative;
    overflow: hidden;
  }

  .agent-card.idle {
    border-top: 2px solid #e8edf2;
  }

  .agent-card.running {
    border-top: 2px solid #48a1aa;
    box-shadow: 0 4px 20px rgba(72,161,170,0.15);
    animation: card-pulse 1.5s ease-in-out infinite;
  }

  .agent-card.passed {
    border-top: 2px solid #BDE3C3;
    box-shadow: 0 4px 16px rgba(189,227,195,0.3);
  }

  .agent-card.warning {
    border-top: 2px solid #F8F7BA;
    box-shadow: 0 4px 16px rgba(248,247,186,0.4);
  }

  .agent-card.skipped {
    opacity: 0.5;
    border-top: 2px solid #e8edf2;
  }

  @keyframes card-pulse {
    0%, 100% { transform: translateY(0); box-shadow: 0 4px 20px rgba(72,161,170,0.15); }
    50% { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(72,161,170,0.25); }
  }

  .agent-emoji {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    display: block;
  }

  .agent-name {
    font-size: 0.72rem;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 0.2rem;
    line-height: 1.3;
  }

  .agent-role {
    font-size: 0.65rem;
    color: #94a3b8;
    line-height: 1.4;
    margin-bottom: 0.5rem;
  }

  .agent-badge {
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
  }

  .badge-idle { background: #f1f5f9; color: #94a3b8; }
  .badge-running { background: rgba(72,161,170,0.1); color: #48a1aa; }
  .badge-passed { background: rgba(189,227,195,0.3); color: #2d6a4f; }
  .badge-warning { background: rgba(248,247,186,0.5); color: #7d6608; }
  .badge-skipped { background: #f1f5f9; color: #94a3b8; }

  /* ── About section ── */
  .about-section {
    background: #ffffff;
    padding: 3rem;
    border-bottom: 1px solid #e8edf2;
  }

  .about-headline {
    font-size: 1.8rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
    margin-bottom: 0.8rem;
    letter-spacing: -0.02em;
  }

  .about-headline span { color: #48a1aa; }

  .about-sub {
    font-size: 0.95rem;
    color: #64748b;
    line-height: 1.7;
    max-width: 560px;
    margin-bottom: 1.5rem;
  }

  .features-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.6rem;
    max-width: 560px;
  }

  .feature-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: #374151;
  }

  .feature-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #48a1aa;
    flex-shrink: 0;
  }

  /* Stats */
  .stats-row {
    display: flex;
    gap: 2.5rem;
    margin-top: 2rem;
    padding-top: 2rem;
    border-top: 1px solid #e8edf2;
  }

  .stat-item { text-align: left; }

  .stat-num {
    font-size: 1.8rem;
    font-weight: 800;
    color: #48a1aa;
    line-height: 1;
  }

  .stat-lbl {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.2rem;
  }

  /* ── Input section ── */
  .input-section {
    background: #f8fafc;
    padding: 3rem;
    min-height: auto;
  }

  .input-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #48a1aa;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.4rem;
  }

  .input-heading {
    font-size: 1.3rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.3rem;
  }

  .input-sub {
    font-size: 0.85rem;
    color: #64748b;
    margin-bottom: 1.5rem;
  }

  /* Usage */
  .usage-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 1.5rem;
  }

  .usage-pip {
    width: 28px;
    height: 4px;
    border-radius: 2px;
  }

  .pip-used { background: #48a1aa; }
  .pip-free { background: #e2e8f0; }

  .usage-text {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-left: 0.3rem;
  }

  /* Run button override */
  div[data-testid="stButton"] button[kind="primary"] {
    background: #48a1aa !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 2rem !important;
    transition: all 0.2s !important;
  }

  div[data-testid="stButton"] button[kind="primary"]:hover {
    background: #3d8f98 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(72,161,170,0.3) !important;
  }

  /* Progress area */
  .progress-area {
    background: #ffffff;
    border: 1px solid #e8edf2;
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
  }

  .progress-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 1rem;
  }

  .progress-agent-row {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.8rem;
  }

  .progress-agent-row:last-child { border-bottom: none; }

  /* Go/No-Go banner */
  .go-banner {
    border-radius: 12px;
    padding: 1.5rem 2rem;
    text-align: center;
    margin: 1.5rem 0;
  }

  /* Result tabs */
  .result-metric {
    background: #f8fafc;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    text-align: center;
  }

  .result-metric-num {
    font-size: 1.4rem;
    font-weight: 700;
    color: #48a1aa;
  }

  .result-metric-lbl {
    font-size: 0.7rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  @media (max-width: 768px) {
    .agents-grid { grid-template-columns: repeat(3, 1fr); }
    .top-nav { padding: 1rem 1.5rem; }
    .pipeline-section, .about-section, .input-section { padding: 2rem 1.5rem; }
    .about-headline { font-size: 1.4rem; }
    .features-list { grid-template-columns: 1fr; }
    .stats-row { gap: 1.5rem; flex-wrap: wrap; }
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Agents data
# ─────────────────────────────────────────

AGENTS = [
    ("\U0001f4cb", "Requirements Analyst", "Finds gaps and ambiguities"),
    ("\u26a0\ufe0f", "Risk Assessor", "Scores risks by likelihood x impact"),
    ("\U0001f5fa\ufe0f", "Test Strategist", "Decides what and how to test"),
    ("\u270d\ufe0f", "Test Case Writer", "Writes all test cases"),
    ("\U0001f50d", "Coverage Analyser", "Finds gaps vs existing suite"),
    ("\U0001f4c4", "Report Writer", "Produces final QA plan"),
]

# ─────────────────────────────────────────
# Paywall
# ─────────────────────────────────────────

if st.session_state.runs_used >= MAX_FREE_RUNS:
    st.markdown("""
    <div style="min-height:100vh;display:flex;align-items:center;
                justify-content:center;background:#f8fafc;padding:3rem">
      <div style="text-align:center;max-width:440px">
        <div style="font-size:3.5rem;margin-bottom:1rem">\U0001f512</div>
        <h2 style="font-size:1.6rem;font-weight:800;color:#0f172a;margin-bottom:0.5rem">
          5 free runs used
        </h2>
        <p style="color:#64748b;line-height:1.7;margin-bottom:2rem">
          This tool is open source. Self-host it on your own machine
          for unlimited runs — free forever.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.link_button("\u2b50 View on GitHub",
                      "https://github.com/thila98/qa-workflow-orchestrator",
                      use_container_width=True)
        st.link_button("\U0001f517 Connect on LinkedIn",
                      "https://linkedin.com/in/thilangi-de-silva-66bb0b190/",
                      use_container_width=True)
    st.stop()

# ─────────────────────────────────────────
# Top Nav
# ─────────────────────────────────────────

st.markdown("""
<div class="top-nav">
  <div class="nav-logo">QA Orchestrator<span>.</span></div>
  <div class="nav-badge">\U0001f9ea AI-Powered QA Planning</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Helper: render agent pipeline
# ─────────────────────────────────────────

def render_pipeline(statuses):
    judge_status = statuses.get("_judge", "idle")
    if judge_status == "running":
        judge_class = "running"
        judge_text = "\u27f3 Validating..."
    elif judge_status == "passed":
        judge_class = "passed"
        judge_text = "\u2713 All outputs validated"
    elif judge_status == "warning":
        judge_class = "warning"
        judge_text = "\u26a1 Corrections applied"
    else:
        judge_class = ""
        judge_text = "\U0001f6e1\ufe0f Judge Agent — Always Watching"

    cards_html = ""
    for emoji, name, role in AGENTS:
        status = statuses.get(name, "idle")
        card_class = status
        if status == "idle":
            badge = "<span class=\"agent-badge badge-idle\">Idle</span>"
        elif status == "running":
            badge = "<span class=\"agent-badge badge-running\">\u27f3 Running</span>"
        elif status == "passed":
            badge = "<span class=\"agent-badge badge-passed\">\u2713 Passed</span>"
        elif status == "warning":
            badge = "<span class=\"agent-badge badge-warning\">\u26a1 Corrected</span>"
        elif status == "skipped":
            badge = "<span class=\"agent-badge badge-skipped\">\u2014 Skipped</span>"
        else:
            badge = "<span class=\"agent-badge badge-idle\">Idle</span>"

        cards_html += f"""
        <div class="agent-card {card_class}">
          <span class="agent-emoji">{emoji}</span>
          <div class="agent-name">{name}</div>
          <div class="agent-role">{role}</div>
          {badge}
        </div>"""

    return f"""
    <div class="pipeline-section">
      <div class="pipeline-label">Live Agent Pipeline</div>
      <div class="pipeline-heading">Watch your AI QA team work</div>
      <div class="pipeline-sub">
        Each agent has one specialist role. Agents animate only when running.
      </div>
      <div class="judge-row">
        <div class="judge-pill {judge_class}">{judge_text}</div>
      </div>
      <div class="connector">
        <div class="connector-line"></div>
      </div>
      <div class="agents-grid">{cards_html}</div>
    </div>"""

# ─────────────────────────────────────────
# Render pipeline (static when idle)
# ─────────────────────────────────────────

pipeline_placeholder = st.empty()
pipeline_placeholder.markdown(
    render_pipeline(st.session_state.agent_statuses),
    unsafe_allow_html=True
)

# ─────────────────────────────────────────
# About section
# ─────────────────────────────────────────

if not st.session_state.show_review_gate and not st.session_state.final_report:
    st.markdown("""
    <div class="about-section">
      <h2 class="about-headline">
        Most AI tools generate test cases.<br>
        <span>This one thinks like your entire QA team.</span>
      </h2>
      <p class="about-sub">
        6 specialist AI agents work together — analysing requirements, assessing risk,
        designing strategy, writing test cases, checking coverage, and producing a complete
        QA plan. A Judge Agent validates every output before it passes to the next agent.
      </p>
      <div class="features-list">
        <div class="feature-item">
          <div class="feature-dot"></div>Requirements gap analysis
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>Risk matrix with scores
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>Test strategy document
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>20+ structured test cases
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>Coverage gap report
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>Go/No-Go recommendation
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>Downloadable HTML report
        </div>
        <div class="feature-item">
          <div class="feature-dot"></div>Auto correction loops
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">
          <div class="stat-num">6</div>
          <div class="stat-lbl">AI Agents</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">20+</div>
          <div class="stat-lbl">Test Cases</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">90s</div>
          <div class="stat-lbl">Avg Runtime</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">$0.05</div>
          <div class="stat-lbl">Per Run</div>
        </div>
        <div class="stat-item">
          <div class="stat-num">5</div>
          <div class="stat-lbl">Free Runs</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# Input Section
# ─────────────────────────────────────────

if not st.session_state.show_review_gate and not st.session_state.final_report:

    runs_remaining = MAX_FREE_RUNS - st.session_state.runs_used
    pips = ""
    for i in range(MAX_FREE_RUNS):
        cls = "pip-used" if i < st.session_state.runs_used else "pip-free"
        pips += f'<div class="usage-pip {cls}"></div>'

    st.markdown(f"""
    <div class="input-section">
      <div class="input-label">Try It Free</div>
      <div class="input-heading">Paste your requirement</div>
      <div class="input-sub">
        Describe the feature you want to test. The more specific you are,
        the better the QA plan will be.
      </div>
      <div class="usage-row">
        {pips}
        <span class="usage-text">{runs_remaining} run{"s" if runs_remaining != 1 else ""} remaining</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        col_main, col_side = st.columns([3, 1])

        with col_main:
            with st.expander("See example requirements"):
                examples = {
                    "User Login with Lockout": "User login with email and password. After 3 consecutive failed login attempts the account locks for 15 minutes. Users can reset their password via email. The reset link expires after 24 hours.",
                    "SOP Acknowledgement": "Workspace Admins can mark any published SOP as requiring acknowledgement. Users who open a flagged SOP see an Acknowledge button. Clicking opens a confirmation popup with SOP name and version. User ticks checkbox and clicks Confirm. Acknowledgement recorded with timestamp. Users can only acknowledge once per version.",
                    "File Upload": "File upload that accepts PDF and DOCX up to 10MB. Files scanned for malware before saving. Email confirmation sent on successful upload. Files stored 30 days then auto-deleted unless marked permanent. Authenticated users only.",
                }
                selected = st.selectbox("Load an example:", ["Select..."] + list(examples.keys()))
                if selected and selected != "Select...":
                    if st.button("Use this example"):
                        st.session_state["example_req"] = examples[selected]
                        st.rerun()

            default_req = st.session_state.get("example_req", "")
            requirement = st.text_area(
                "Requirement",
                value=default_req,
                height=160,
                placeholder="Describe the feature you want to test...",
                label_visibility="collapsed"
            )

            char_count = len(requirement.strip())
            if char_count > 0:
                if char_count < 100:
                    st.caption(f"\u26a0\ufe0f {char_count} characters — add more detail for better results")
                else:
                    st.caption(f"\u2705 {char_count} characters")

            uploaded_file = st.file_uploader(
                "Existing test suite CSV — optional, for coverage gap analysis",
                type=["csv"],
                label_visibility="visible"
            )

            existing_suite_path = None
            if uploaded_file:
                with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    existing_suite_path = tmp.name
                st.session_state["temp_suite_path"] = existing_suite_path

            if "temp_suite_path" in st.session_state and not uploaded_file:
                existing_suite_path = st.session_state.get("temp_suite_path")

            run_button = st.button(
                "\U0001f680  Run QA Workflow",
                disabled=st.session_state.workflow_running or not requirement.strip(),
                type="primary"
            )

        with col_side:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e8edf2;border-radius:10px;
                        padding:1.2rem;margin-top:0.5rem;font-size:0.8rem;color:#374151">
              <div style="font-weight:700;color:#0f172a;margin-bottom:0.8rem;font-size:0.82rem">
                What you get
              </div>
              <div style="line-height:2.2;color:#64748b">
                \u2713 Requirements analysis<br>
                \u2713 Risk matrix with scores<br>
                \u2713 Test strategy<br>
                \u2713 20+ test cases<br>
                \u2713 Coverage gap report<br>
                \u2713 Go/No-Go recommendation<br>
                \u2713 HTML report download
              </div>
              <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #e8edf2;
                          color:#94a3b8;font-size:0.72rem;line-height:1.8">
                Time: 90–120 seconds<br>
                Cost: $0.03–0.10 per run<br>
                Agents: 4–6 depending on input
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Run workflow ────────────────────────────────────────────

    if run_button and requirement.strip():
        from validation.input_validator import validate_input
        input_check = validate_input(requirement)

        if not input_check.is_valid:
            st.error(f"\u274c {input_check.error_message}")
        else:
            st.session_state.workflow_running = True

            status_placeholder = st.empty()
            progress_bar = st.progress(0)

            agent_statuses = {name: "idle" for _, name, _ in AGENTS}
            agent_statuses["_judge"] = "idle"

            def update_pipeline(statuses, progress=0):
                pipeline_placeholder.markdown(
                    render_pipeline(statuses),
                    unsafe_allow_html=True
                )
                progress_bar.progress(progress)

            try:
                from main import run_workflow

                for i, (_, name, _) in enumerate(AGENTS[:4]):
                    agent_statuses[name] = "running"
                    agent_statuses["_judge"] = "running"
                    update_pipeline(agent_statuses, (i * 15) / 100)
                    status_placeholder.caption(f"Running {name}...")

                result = run_workflow(
                    requirement=requirement,
                    existing_test_suite_path=existing_suite_path
                )

                if result.get("status") == "error":
                    st.error(f"\u274c {result.get('message','Unknown error')}")
                    st.session_state.workflow_running = False
                else:
                    judge_results = result.get("judge_results", {})
                    for _, name, _ in AGENTS[:4]:
                        j = judge_results.get(name, {})
                        rec = j.get("recommendation", "PASS")
                        if rec == "PASS_WITH_WARNINGS":
                            agent_statuses[name] = "warning"
                        else:
                            agent_statuses[name] = "passed"

                    agent_statuses["Coverage Analyser"] = "passed" if existing_suite_path else "skipped"
                    agent_statuses["Report Writer"] = "idle"

                    has_warnings = any(v == "warning" for v in agent_statuses.values())
                    agent_statuses["_judge"] = "warning" if has_warnings else "passed"

                    update_pipeline(agent_statuses, 1.0)
                    status_placeholder.success("\u2705 Workflow complete — ready for your review")

                    st.session_state.runs_used += 1
                    st.session_state.current_result = result
                    st.session_state.agent_statuses = agent_statuses
                    st.session_state.show_review_gate = True
                    st.session_state.workflow_running = False
                    st.rerun()

            except Exception as e:
                st.error(f"\u274c Workflow failed: {str(e)}")
                st.session_state.workflow_running = False

# ─────────────────────────────────────────
# Human Review Gate
# ─────────────────────────────────────────

elif st.session_state.show_review_gate and not st.session_state.final_report:

    result = st.session_state.current_result
    outputs = result.get("outputs", {})
    confidence = result.get("confidence", {})
    session_id = result.get("session_id", "")
    conf_score = confidence.get("score", 0)
    cost = result.get("workflow_state", {}).get("total_cost_usd", 0)

    st.markdown(f"""
    <div style="background:#f8fafc;padding:2rem 3rem 1rem;border-bottom:1px solid #e8edf2">
      <div style="font-size:0.7rem;font-weight:700;color:#48a1aa;text-transform:uppercase;
                  letter-spacing:0.12em;margin-bottom:0.3rem">Review Gate</div>
      <div style="font-size:1.3rem;font-weight:700;color:#0f172a;margin-bottom:0.3rem">
        Review agent outputs before generating your report
      </div>
      <div style="font-size:0.82rem;color:#64748b">
        Session {session_id} &nbsp;·&nbsp;
        Confidence: <strong>{conf_score:.0%}</strong> &nbsp;·&nbsp;
        API cost: <strong>${cost:.4f}</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)

    flags = confidence.get("flags", [])
    if flags:
        with st.expander(f"\u26a0\ufe0f {len(flags)} validation flag(s)"):
            for flag in flags:
                if "CRITICAL" in flag or "HALLUCINATION" in flag:
                    st.error(flag)
                else:
                    st.warning(flag)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "\U0001f4cb Requirements",
        "\u26a0\ufe0f Risk",
        "\U0001f5fa\ufe0f Strategy",
        "\u270d\ufe0f Test Cases",
        "\U0001f50d Coverage"
    ])

    with tab1:
        req = outputs.get("requirements_analysis", {})
        if req:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Quality Score", f"{req.get('quality_score','N/A')}/10")
            c2.metric("Gaps Found", len(req.get("gaps", [])))
            c3.metric("Ambiguities", len(req.get("ambiguities", [])))
            c4.metric("Testable", "Yes" if req.get("is_testable") else "No")
            st.info(req.get("summary", ""))
            if req.get("gaps"):
                st.markdown("**Gaps identified:**")
                for g in req.get("gaps", []):
                    st.warning(f"• {g}")
            if req.get("clarification_questions"):
                st.markdown("**Questions before testing:**")
                for q in req.get("clarification_questions", []):
                    st.info(f"• {q}")

    with tab2:
        risk = outputs.get("risk_assessment", {})
        if risk:
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall Risk", risk.get("overall_risk_level","N/A"))
            c2.metric("Risk Areas", len(risk.get("risk_areas",[])))
            c3.metric("Critical Risks", len(risk.get("critical_risks",[])))
            st.info(risk.get("risk_summary",""))
            risk_areas = risk.get("risk_areas", [])
            if risk_areas:
                df = pd.DataFrame([{
                    "Risk Area": r.get("name",""),
                    "Category": r.get("category",""),
                    "Likelihood": r.get("likelihood",""),
                    "Impact": r.get("impact",""),
                    "Score": r.get("score",""),
                    "Priority": r.get("priority_level","")
                } for r in risk_areas])
                st.dataframe(df, use_container_width=True)

    with tab3:
        strategy = outputs.get("test_strategy", {})
        if strategy:
            c1, c2, c3 = st.columns(3)
            c1.metric("Est. Test Cases", strategy.get("estimated_test_cases","N/A"))
            c2.metric("Est. Hours", strategy.get("estimated_hours","N/A"))
            c3.metric("Security Testing", "Required" if strategy.get("security_testing_required") else "Not Required")
            st.info(strategy.get("strategy_summary",""))
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Manual:**")
                for t in strategy.get("manual_tests",[]):
                    st.markdown(f"• {t}")
            with cb:
                st.markdown("**Automate:**")
                for t in strategy.get("automated_tests",[]):
                    st.markdown(f"• {t}")

    with tab4:
        tc_data = outputs.get("test_cases", {})
        test_cases = tc_data.get("test_cases", [])
        if test_cases:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cases", len(test_cases))
            c2.metric("Complexity", tc_data.get("complexity_level","N/A").replace("_"," ").title())
            c3.metric("Batches", tc_data.get("batch_count","N/A"))
            st.info(tc_data.get("coverage_summary",""))
            df = pd.DataFrame([{
                "ID": tc.get("tc_id",""),
                "Category": tc.get("category",""),
                "Title": tc.get("title",""),
                "Priority": tc.get("priority",""),
                "Type": tc.get("test_type","")
            } for tc in test_cases])
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "\U0001f4e5 Download Test Cases CSV",
                data=df.to_csv(index=False),
                file_name=f"test_cases_{session_id}.csv",
                mime="text/csv"
            )

    with tab5:
        coverage = outputs.get("coverage_analysis", {})
        if coverage and not coverage.get("skipped"):
            c1, c2 = st.columns(2)
            c1.metric("Coverage Estimate", coverage.get("coverage_estimate","N/A"))
            c2.metric("New Tests Adding Value", coverage.get("new_tests_adding_value","N/A"))
            st.info(coverage.get("coverage_summary",""))
        else:
            st.info("No existing test suite uploaded. Add a CSV on your next run for coverage gap analysis.")

    st.divider()
    st.markdown("**Your notes for the Report Writer** (optional)")
    reviewer_notes = st.text_area(
        "Notes",
        value=st.session_state.reviewer_notes,
        height=80,
        placeholder="Add any corrections or missing scenarios...",
        label_visibility="collapsed"
    )
    st.session_state.reviewer_notes = reviewer_notes

    col_approve, col_restart = st.columns(2)
    with col_approve:
        if st.button("\u2705 Approve and Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating final QA plan..."):
                try:
                    from agents.report_writer import write_report
                    from tools.report_generator import generate_html_report
                    final_report = write_report(
                        requirement=result.get("requirement",""),
                        all_outputs=outputs,
                        human_reviewer_notes=reviewer_notes,
                        confidence_score=conf_score
                    )
                    html = generate_html_report(
                        requirement=result.get("requirement",""),
                        all_outputs=outputs,
                        final_report=final_report,
                        confidence=confidence,
                        workflow_state_data=result.get("workflow_state",{}),
                        session_id=session_id
                    )
                    st.session_state.final_report = final_report
                    st.session_state.html_report = html
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate report: {str(e)}")

    with col_restart:
        if st.button("\U0001f504 Start Over", use_container_width=True):
            for key in ["current_result","final_report","html_report",
                        "show_review_gate","reviewer_notes","agent_statuses",
                        "temp_suite_path","example_req"]:
                if key in st.session_state:
                    del st.session_state[key]
            init_session_state()
            st.rerun()

# ─────────────────────────────────────────
# Final Report
# ─────────────────────────────────────────

elif st.session_state.final_report:

    final_report = st.session_state.final_report
    result = st.session_state.current_result or {}
    session_id = result.get("session_id","")
    outputs = result.get("outputs",{})

    recommendation = final_report.get("go_no_go_recommendation","GO")
    if recommendation == "GO":
        rec_color = "#2d6a4f"
        rec_bg = "#f0fdf4"
        rec_border = "#BDE3C3"
        rec_icon = "\u2705"
    elif recommendation == "CONDITIONAL GO":
        rec_color = "#7d6608"
        rec_bg = "#fefce8"
        rec_border = "#F8F7BA"
        rec_icon = "\u26a0\ufe0f"
    else:
        rec_color = "#c0392b"
        rec_bg = "#fff5f5"
        rec_border = "#F5D2D2"
        rec_icon = "\U0001f6ab"

    st.markdown(f"""
    <div style="background:{rec_bg};border:2px solid {rec_border};border-radius:12px;
                padding:1.5rem 2rem;margin:2rem 3rem 1rem;text-align:center">
      <div style="font-size:2.5rem">{rec_icon}</div>
      <div style="font-size:1.8rem;font-weight:800;color:{rec_color};margin:0.3rem 0">
        {recommendation}
      </div>
      <div style="color:#64748b;font-size:0.9rem">
        {final_report.get("go_no_go_reasoning","")}
      </div>
    </div>
    """, unsafe_allow_html=True)

    suite = final_report.get("test_suite_summary",{})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Test Cases", suite.get("total_test_cases","N/A"))
    c2.metric("High Priority", suite.get("high_priority_count","N/A"))
    c3.metric("Auto Candidates", suite.get("automation_candidates","N/A"))
    c4.metric("Confidence", f"{result.get('confidence',{}).get('score',0):.0%}")

    st.markdown("**Executive Summary**")
    st.info(final_report.get("executive_summary",""))

    if final_report.get("next_steps"):
        st.markdown("**Next Steps**")
        for i, step in enumerate(final_report.get("next_steps",[]), 1):
            st.markdown(f"{i}. {step}")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.session_state.html_report:
            st.download_button(
                "\U0001f4c4 Download HTML Report",
                data=st.session_state.html_report,
                file_name=f"qa_plan_{session_id}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
    with col2:
        test_cases = outputs.get("test_cases",{}).get("test_cases",[])
        if test_cases:
            tc_df = pd.DataFrame([{
                "TC_ID": tc.get("tc_id",""),
                "Category": tc.get("category",""),
                "Title": tc.get("title",""),
                "Precondition": tc.get("precondition",""),
                "Steps": tc.get("steps",""),
                "Expected Result": tc.get("expected_result",""),
                "Priority": tc.get("priority",""),
                "Test Type": tc.get("test_type",""),
                "Risk Area": tc.get("risk_area",""),
                "Requirement Reference": tc.get("requirement_reference","")
            } for tc in test_cases])
            st.download_button(
                "\U0001f4ca Download CSV",
                data=tc_df.to_csv(index=False),
                file_name=f"test_cases_{session_id}.csv",
                mime="text/csv",
                use_container_width=True
            )
    with col3:
        if st.button("\U0001f504 New Analysis", use_container_width=True):
            for key in ["current_result","final_report","html_report",
                        "show_review_gate","reviewer_notes","agent_statuses",
                        "temp_suite_path","example_req"]:
                if key in st.session_state:
                    del st.session_state[key]
            init_session_state()
            st.rerun()

    st.markdown("""
    <div style="text-align:center;color:#94a3b8;font-size:0.75rem;padding:2rem 0 1rem">
      Built by Thilangi Uththara De Silva &nbsp;·&nbsp;
      <a href="https://github.com/thila98/qa-workflow-orchestrator" style="color:#48a1aa">GitHub</a>
      &nbsp;·&nbsp;
      <a href="https://linkedin.com/in/thilangi-de-silva-66bb0b190/" style="color:#48a1aa">LinkedIn</a>
    </div>
    """, unsafe_allow_html=True)
