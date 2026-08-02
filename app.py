"""
QA Workflow Orchestrator - Streamlit Dashboard
-----------------------------------------------
Modern AI-powered QA planning dashboard.
Designed to feel different from every other QA tool.
"""

import streamlit as st
import json
import os
import tempfile
import time
from datetime import datetime

st.set_page_config(
    page_title="QA Workflow Orchestrator",
    page_icon="🧪",
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
        "approved": False,
        "error_message": None,
        "agent_statuses": {},
        "show_input": True,
        "dark_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ─────────────────────────────────────────
# Theme
# ─────────────────────────────────────────

dark = st.session_state.dark_mode

if dark:
    bg_primary = "#0f1724"
    bg_secondary = "#1a2235"
    bg_card = "#1e2a3a"
    text_primary = "#e2e8f0"
    text_secondary = "#94a3b8"
    border_color = "rgba(163,204,218,0.15)"
else:
    bg_primary = "#f8fafc"
    bg_secondary = "#ffffff"
    bg_card = "#ffffff"
    text_primary = "#1a202c"
    text_secondary = "#4a5568"
    border_color = "rgba(163,204,218,0.3)"

teal = "#48a1aa"
pink = "#F5D2D2"
yellow = "#F8F7BA"
green = "#BDE3C3"
blue = "#A3CCDA"

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

  * {{ font-family: 'Poppins', sans-serif !important; }}

  .main .block-container {{
    padding: 0 !important;
    max-width: 100% !important;
  }}

  #MainMenu, footer, header {{ visibility: hidden; }}

  /* Hero */
  .hero-section {{
    background: {bg_primary if not dark else "linear-gradient(135deg, #0f1724 0%, #1a2235 50%, #0f2030 100%)"};
    padding: 5rem 4rem 4rem;
    position: relative;
    overflow: hidden;
  }}

  .hero-section::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at center,
      rgba(72,161,170,0.08) 0%,
      transparent 60%);
    animation: rotate 20s linear infinite;
  }}

  @keyframes rotate {{
    from {{ transform: rotate(0deg); }}
    to {{ transform: rotate(360deg); }}
  }}

  .hero-badge {{
    display: inline-block;
    background: rgba(72,161,170,0.15);
    border: 1px solid rgba(72,161,170,0.4);
    color: {teal};
    padding: 0.3rem 1rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    margin-bottom: 1.5rem;
    letter-spacing: 0.05em;
  }}

  .hero-title {{
    font-size: 2.8rem;
    font-weight: 800;
    color: {text_primary};
    line-height: 1.15;
    margin-bottom: 1.2rem;
    position: relative;
    z-index: 1;
  }}

  .hero-title span {{
    background: linear-gradient(135deg, {teal}, #6ab8c0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}

  .hero-subtitle {{
    font-size: 1.1rem;
    color: {text_secondary};
    max-width: 600px;
    line-height: 1.7;
    margin-bottom: 2rem;
    position: relative;
    z-index: 1;
  }}

  /* Metrics */
  .metrics-row {{
    display: flex;
    gap: 2rem;
    margin-bottom: 2.5rem;
    position: relative;
    z-index: 1;
    flex-wrap: wrap;
  }}

  .metric-item {{
    text-align: center;
  }}

  .metric-number {{
    font-size: 2.2rem;
    font-weight: 800;
    color: {teal};
    line-height: 1;
  }}

  .metric-label {{
    font-size: 0.78rem;
    color: {text_secondary};
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .metric-divider {{
    width: 1px;
    background: {border_color};
    height: 40px;
    align-self: center;
  }}

  /* Agent Cards */
  .agents-section {{
    background: {bg_secondary};
    padding: 3rem 4rem;
    border-top: 1px solid {border_color};
  }}

  .section-label {{
    font-size: 0.75rem;
    font-weight: 600;
    color: {teal};
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
  }}

  .section-title {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {text_primary};
    margin-bottom: 0.5rem;
  }}

  .section-subtitle {{
    font-size: 0.9rem;
    color: {text_secondary};
    margin-bottom: 2rem;
  }}

  .agent-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
  }}

  .agent-card {{
    background: {bg_card};
    border: 1px solid {border_color};
    border-radius: 12px;
    padding: 1.2rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }}

  .agent-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent, {teal}, transparent);
    opacity: 0;
    transition: opacity 0.3s;
  }}

  .agent-card:hover::before {{
    opacity: 1;
  }}

  .agent-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(72,161,170,0.12);
    border-color: rgba(72,161,170,0.4);
  }}

  .agent-icon {{
    font-size: 1.8rem;
    margin-bottom: 0.6rem;
  }}

  .agent-name {{
    font-size: 0.9rem;
    font-weight: 600;
    color: {text_primary};
    margin-bottom: 0.2rem;
  }}

  .agent-role {{
    font-size: 0.75rem;
    color: {text_secondary};
    line-height: 1.5;
  }}

  .agent-status {{
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 0.15rem 0.6rem;
    border-radius: 10px;
    margin-top: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  .status-idle {{
    background: rgba(148,163,184,0.15);
    color: {text_secondary};
  }}

  .status-running {{
    background: rgba(72,161,170,0.15);
    color: {teal};
    animation: pulse-status 1.5s ease-in-out infinite;
  }}

  .status-passed {{
    background: rgba(189,227,195,0.3);
    color: #2d6a4f;
  }}

  .status-warning {{
    background: rgba(248,247,186,0.5);
    color: #7d6608;
  }}

  .status-corrected {{
    background: rgba(245,210,210,0.3);
    color: #c0392b;
  }}

  @keyframes pulse-status {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
  }}

  .judge-card {{
    background: linear-gradient(135deg,
      rgba(72,161,170,0.08),
      rgba(72,161,170,0.04));
    border: 1px solid rgba(72,161,170,0.3);
    border-radius: 12px;
    padding: 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 2rem;
  }}

  .judge-icon {{
    font-size: 2rem;
    flex-shrink: 0;
  }}

  .judge-text h4 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: {teal};
    margin-bottom: 0.2rem;
  }}

  .judge-text p {{
    font-size: 0.78rem;
    color: {text_secondary};
    margin: 0;
    line-height: 1.5;
  }}

  /* Input Section */
  .input-section {{
    background: {bg_primary};
    padding: 3rem 4rem;
    border-top: 1px solid {border_color};
  }}

  /* Go/No-Go Banner */
  .go-banner {{
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
    text-align: center;
  }}

  .go-banner h2 {{
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
  }}

  /* Result Cards */
  .result-card {{
    background: {bg_card};
    border: 1px solid {border_color};
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
  }}

  .result-card h3 {{
    font-size: 0.95rem;
    font-weight: 600;
    color: {teal};
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid {border_color};
  }}

  /* Usage counter */
  .usage-bar {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }}

  .usage-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }}

  .dot-used {{ background: {teal}; }}
  .dot-free {{ background: {border_color}; border: 1px solid rgba(72,161,170,0.3); }}

  /* Theme toggle */
  .theme-toggle {{
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 999;
    background: {bg_card};
    border: 1px solid {border_color};
    border-radius: 20px;
    padding: 0.4rem 0.8rem;
    font-size: 0.8rem;
    cursor: pointer;
    color: {text_primary};
  }}

  /* Responsive */
  @media (max-width: 768px) {{
    .hero-section {{ padding: 3rem 1.5rem; }}
    .hero-title {{ font-size: 1.8rem; }}
    .agents-section {{ padding: 2rem 1.5rem; }}
    .agent-grid {{ grid-template-columns: 1fr 1fr; }}
    .input-section {{ padding: 2rem 1.5rem; }}
    .metrics-row {{ gap: 1rem; }}
  }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Theme Toggle
# ─────────────────────────────────────────

col_toggle = st.columns([6, 1])[1]
with col_toggle:
    theme_icon = "☀️" if dark else "🌙"
    if st.button(theme_icon, key="theme_toggle", help="Toggle dark/light mode"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ─────────────────────────────────────────
# Paywall
# ─────────────────────────────────────────

if st.session_state.runs_used >= MAX_FREE_RUNS:
    st.markdown(f"""
    <div style="background:{bg_primary};min-height:100vh;display:flex;
                align-items:center;justify-content:center;padding:4rem;">
      <div style="text-align:center;max-width:500px">
        <div style="font-size:4rem;margin-bottom:1rem">🔒</div>
        <h2 style="color:{text_primary};font-size:1.8rem;font-weight:700;margin-bottom:0.5rem">
          You have used your 5 free runs
        </h2>
        <p style="color:{text_secondary};margin-bottom:2rem;line-height:1.7">
          Thank you for trying QA Workflow Orchestrator.
          This is open source — self-host it for unlimited runs.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.link_button("⭐ View on GitHub", "https://github.com/thila98/qa-workflow-orchestrator",
                      use_container_width=True)
        st.link_button("🔗 Connect on LinkedIn",
                      "https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/",
                      use_container_width=True)
    st.stop()

# ─────────────────────────────────────────
# Hero Section
# ─────────────────────────────────────────

runs_remaining = MAX_FREE_RUNS - st.session_state.runs_used

usage_dots = ""
for i in range(MAX_FREE_RUNS):
    if i < st.session_state.runs_used:
        usage_dots += f'<span class="usage-dot dot-used"></span>'
    else:
        usage_dots += f'<span class="usage-dot dot-free"></span>'

st.markdown(f"""
<div class="hero-section">
  <div class="hero-badge">🧪 AI-Powered QA Planning</div>
  <h1 class="hero-title">
    Most AI tools generate test cases.<br>
    <span>This one thinks like your entire QA team.</span>
  </h1>
  <p class="hero-subtitle">
    6 specialised AI agents analyse your requirement, assess risk,
    design a test strategy, write test cases, and produce a complete
    QA plan — with a Judge Agent validating every step.
  </p>
  <div class="metrics-row">
    <div class="metric-item">
      <div class="metric-number">6</div>
      <div class="metric-label">AI Specialists</div>
    </div>
    <div class="metric-divider"></div>
    <div class="metric-item">
      <div class="metric-number">20+</div>
      <div class="metric-label">Test Cases</div>
    </div>
    <div class="metric-divider"></div>
    <div class="metric-item">
      <div class="metric-number">90s</div>
      <div class="metric-label">Avg Runtime</div>
    </div>
    <div class="metric-divider"></div>
    <div class="metric-item">
      <div class="metric-number">$0.05</div>
      <div class="metric-label">Per Run</div>
    </div>
  </div>
  <div class="usage-bar">
    {usage_dots}
    <span style="font-size:0.78rem;color:{text_secondary};margin-left:0.3rem">
      {runs_remaining} free run{"s" if runs_remaining != 1 else ""} remaining
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Agent Pipeline Section
# ─────────────────────────────────────────

agents_data = [
    ("📋", "Requirements Analyst", "Identifies gaps, ambiguities, and quality issues before testing begins"),
    ("⚠️", "Risk Assessor", "Scores each risk area using Likelihood × Impact methodology"),
    ("🗺️", "Test Strategist", "Decides what to test, how to test it, and what to automate"),
    ("✍️", "Test Case Writer", "Generates structured test cases across all categories"),
    ("🔍", "Coverage Analyser", "Compares new tests against your existing suite to find gaps"),
    ("📄", "Report Writer", "Produces the final QA plan with go/no-go recommendation"),
]

statuses = st.session_state.agent_statuses

def get_status_html(agent_name):
    status = statuses.get(agent_name, "idle")
    if status == "idle":
        return '<span class="agent-status status-idle">Idle</span>'
    elif status == "running":
        return '<span class="agent-status status-running">⟳ Running</span>'
    elif status == "passed":
        return '<span class="agent-status status-passed">✓ Passed</span>'
    elif status == "warning":
        return '<span class="agent-status status-warning">⚡ Corrected</span>'
    elif status == "failed":
        return '<span class="agent-status status-corrected">✗ Failed</span>'
    return '<span class="agent-status status-idle">Idle</span>'

agent_cards_html = '<div class="agent-grid">'
for icon, name, role in agents_data:
    status_html = get_status_html(name)
    agent_cards_html += f"""
    <div class="agent-card">
      <div class="agent-icon">{icon}</div>
      <div class="agent-name">{name}</div>
      <div class="agent-role">{role}</div>
      {status_html}
    </div>"""
agent_cards_html += '</div>'

st.markdown(f"""
<div class="agents-section">
  <div class="section-label">How It Works</div>
  <h2 class="section-title">Your AI QA Team</h2>
  <p class="section-subtitle">
    Each agent has one specialist role. Every output is validated by the Judge Agent
    before passing to the next agent — preventing hallucination propagation.
  </p>

  <div class="judge-card">
    <div class="judge-icon">🛡️</div>
    <div class="judge-text">
      <h4>Judge Agent — Always Watching</h4>
      <p>Independently validates every agent output before it passes downstream.
         Catches hallucinations, flags gaps, and triggers automatic correction loops.
         The most important agent in the system.</p>
    </div>
  </div>

  {agent_cards_html}
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Input / Workflow Section
# ─────────────────────────────────────────

if not st.session_state.show_review_gate and not st.session_state.final_report:

    st.markdown(f"""
    <div class="input-section">
      <div class="section-label">Get Started</div>
      <h2 class="section-title">Paste Your Requirement</h2>
      <p class="section-subtitle">
        Describe the feature you want to test. The more detail you provide,
        the better your QA plan will be.
      </p>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        col_input, col_side = st.columns([3, 1])

        with col_input:
            with st.expander("💡 See example requirements"):
                examples = {
                    "User Login with Lockout": "User login with email and password. After 3 consecutive failed login attempts the account locks for 15 minutes. Users can reset their password via email. The reset link expires after 24 hours. Passwords must be at least 8 characters with one uppercase letter and one number.",
                    "File Upload": "File upload feature that accepts PDF and DOCX files up to 10MB. Files are scanned for malware before being saved. Users receive an email confirmation when upload is complete. Files are stored for 30 days then automatically deleted unless marked as permanent.",
                    "SOP Acknowledgement": "Workspace Admins can mark any published SOP as requiring acknowledgement. Users who open a flagged SOP see an Acknowledge button. Clicking opens a confirmation popup with SOP name and version. User ticks checkbox and clicks Confirm. Acknowledgement is recorded with timestamp. Users can only acknowledge once per version.",
                }
                selected = st.selectbox("Load an example:", ["Select..."] + list(examples.keys()))
                if selected and selected != "Select...":
                    if st.button("Use this example"):
                        st.session_state["example_req"] = examples[selected]
                        st.rerun()

            default_req = st.session_state.get("example_req", "")
            requirement = st.text_area(
                "Requirement or User Story",
                value=default_req,
                height=200,
                placeholder="Describe the feature you want to test...",
            )

            char_count = len(requirement.strip())
            if char_count > 0:
                if char_count < 100:
                    st.caption(f"⚠️ {char_count} characters — add more detail for better results")
                elif char_count < 400:
                    st.caption(f"✅ {char_count} characters — good")
                else:
                    st.caption(f"✅ {char_count} characters — excellent detail")

            uploaded_file = st.file_uploader(
                "📎 Existing test suite CSV (optional — for coverage gap analysis)",
                type=["csv"]
            )

            existing_suite_path = None
            if uploaded_file:
                with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    existing_suite_path = tmp.name
                st.session_state["temp_suite_path"] = existing_suite_path
                st.success(f"✅ {uploaded_file.name} uploaded")

            if "temp_suite_path" in st.session_state and not uploaded_file:
                existing_suite_path = st.session_state.get("temp_suite_path")

        with col_side:
            st.markdown(f"""
            <div style="background:{bg_card};border:1px solid {border_color};
                        border-radius:12px;padding:1.2rem;margin-top:1rem">
              <div style="font-size:0.78rem;font-weight:600;color:{teal};
                          text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.8rem">
                What you get
              </div>
              <div style="font-size:0.82rem;color:{text_secondary};line-height:2">
                ✓ Requirements analysis<br>
                ✓ Risk matrix with scores<br>
                ✓ Test strategy document<br>
                ✓ 20+ structured test cases<br>
                ✓ Coverage gap report<br>
                ✓ Go/No-Go recommendation<br>
                ✓ Downloadable HTML report
              </div>
              <div style="margin-top:1rem;padding-top:1rem;
                          border-top:1px solid {border_color};
                          font-size:0.75rem;color:{text_secondary}">
                Est. time: 90–120 seconds<br>
                Est. cost: $0.03–0.10<br>
                Agents: 4–6
              </div>
            </div>
            """, unsafe_allow_html=True)

    col_run, col_space = st.columns([1, 3])
    with col_run:
        run_button = st.button(
            "🚀 Run QA Workflow",
            disabled=st.session_state.workflow_running or not requirement.strip(),
            use_container_width=True,
            type="primary"
        )

    # ── Run Workflow ────────────────────────────────────────────────

    if run_button and requirement.strip():
        from validation.input_validator import validate_input
        input_check = validate_input(requirement)

        if not input_check.is_valid:
            st.error(f"❌ {input_check.error_message}")
        else:
            st.session_state.workflow_running = True
            st.session_state.agent_statuses = {}

            st.markdown(f"""
            <div style="background:{bg_card};border:1px solid {border_color};
                        border-radius:12px;padding:1.5rem;margin:1rem 0">
              <div style="font-size:0.85rem;font-weight:600;color:{text_primary};margin-bottom:1rem">
                🔄 Running QA Workflow...
              </div>
            """, unsafe_allow_html=True)

            progress = st.progress(0)
            status_text = st.empty()
            agent_display = st.empty()

            def update_agent_display(statuses):
                cards = ""
                for icon, name, role in agents_data:
                    status = statuses.get(name, "idle")
                    if status == "idle":
                        color = text_secondary
                        badge = "○ Waiting"
                        bg = "transparent"
                    elif status == "running":
                        color = teal
                        badge = "⟳ Running..."
                        bg = f"rgba(72,161,170,0.08)"
                    elif status == "passed":
                        color = "#2d6a4f"
                        badge = "✓ Passed"
                        bg = "rgba(189,227,195,0.15)"
                    elif status == "warning":
                        color = "#7d6608"
                        badge = "⚡ Corrected"
                        bg = "rgba(248,247,186,0.2)"
                    elif status == "skipped":
                        color = text_secondary
                        badge = "— Skipped"
                        bg = "transparent"
                    else:
                        color = text_secondary
                        badge = "○ Waiting"
                        bg = "transparent"

                    cards += f"""
                    <div style="display:flex;align-items:center;gap:0.8rem;
                                padding:0.7rem 1rem;border-radius:8px;
                                background:{bg};margin-bottom:0.3rem;
                                transition:all 0.3s ease">
                      <span style="font-size:1.2rem">{icon}</span>
                      <div style="flex:1">
                        <div style="font-size:0.82rem;font-weight:600;color:{text_primary}">{name}</div>
                      </div>
                      <span style="font-size:0.72rem;font-weight:600;color:{color}">{badge}</span>
                    </div>"""
                agent_display.markdown(
                    f'<div style="background:{bg_card};border:1px solid {border_color};border-radius:12px;padding:1rem">' + cards + "</div>",
                    unsafe_allow_html=True
                )

            current_statuses = {name: "idle" for _, name, _ in agents_data}
            update_agent_display(current_statuses)

            try:
                from main import run_workflow

                agent_names = [name for _, name, _ in agents_data[:4]]

                for i, name in enumerate(agent_names):
                    current_statuses[name] = "running"
                    update_agent_display(current_statuses)
                    status_text.markdown(f"**Running {name}...**")
                    progress.progress((i) / 6)

                result = run_workflow(
                    requirement=requirement,
                    existing_test_suite_path=existing_suite_path
                )

                if result.get("status") == "error":
                    st.error(f"❌ {result.get('message', 'Unknown error')}")
                    st.session_state.workflow_running = False
                else:
                    # Update all agent statuses from results
                    judge_results = result.get("judge_results", {})
                    for _, name, _ in agents_data[:4]:
                        judgment = judge_results.get(name, {})
                        rec = judgment.get("recommendation", "PASS")
                        if rec == "PASS":
                            current_statuses[name] = "passed"
                        elif rec == "PASS_WITH_WARNINGS":
                            current_statuses[name] = "warning"
                        else:
                            current_statuses[name] = "passed"

                    if existing_suite_path:
                        current_statuses["Coverage Analyser"] = "passed"
                    else:
                        current_statuses["Coverage Analyser"] = "skipped"

                    current_statuses["Report Writer"] = "idle"
                    update_agent_display(current_statuses)
                    progress.progress(1.0)
                    status_text.markdown("✅ **Workflow complete — ready for your review**")

                    st.session_state.runs_used += 1
                    st.session_state.current_result = result
                    st.session_state.agent_statuses = current_statuses
                    st.session_state.show_review_gate = True
                    st.session_state.workflow_running = False
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Workflow failed: {str(e)}")
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

    st.markdown(f"""
    <div style="background:{bg_primary};padding:2rem 4rem 1rem">
      <div class="section-label">Review Gate</div>
      <h2 class="section-title">Review Agent Outputs</h2>
      <p class="section-subtitle">
        Session {session_id} · AI Confidence: <strong>{conf_score:.0%}</strong> ·
        Cost: <strong>${result.get("workflow_state",{{}}).get("total_cost_usd",0):.4f}</strong>
      </p>
    </div>
    """, unsafe_allow_html=True)

    if conf_score >= 0.85:
        conf_color = "#2d6a4f"
        conf_bg = "rgba(189,227,195,0.2)"
        conf_label = "High Confidence"
    elif conf_score >= 0.70:
        conf_color = "#7d6608"
        conf_bg = "rgba(248,247,186,0.3)"
        conf_label = "Medium Confidence — Review Carefully"
    else:
        conf_color = "#c0392b"
        conf_bg = "rgba(245,210,210,0.2)"
        conf_label = "Low Confidence — Careful Review Required"

    st.markdown(f"""
    <div style="margin:0 4rem 1rem;background:{conf_bg};border-radius:10px;
                padding:1rem 1.5rem;border-left:4px solid {conf_color}">
      <strong style="color:{conf_color}">{conf_label}</strong> ·
      <span style="color:{text_secondary};font-size:0.9rem">
        {confidence.get("recommendation","")}
      </span>
    </div>
    """, unsafe_allow_html=True)

    flags = confidence.get("flags", [])
    if flags:
        with st.expander(f"⚠️ {len(flags)} validation flag(s)"):
            for flag in flags:
                if "CRITICAL" in flag or "HALLUCINATION" in flag:
                    st.error(flag)
                else:
                    st.warning(flag)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Requirements", "⚠️ Risk", "🗺️ Strategy", "✍️ Test Cases", "🔍 Coverage"
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
                st.markdown("**Gaps:**")
                for g in req.get("gaps", []):
                    st.warning(f"• {g}")
            if req.get("clarification_questions"):
                st.markdown("**Clarification needed:**")
                for q in req.get("clarification_questions", []):
                    st.info(f"• {q}")

    with tab2:
        risk = outputs.get("risk_assessment", {})
        if risk:
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall Risk", risk.get("overall_risk_level", "N/A"))
            c2.metric("Risk Areas", len(risk.get("risk_areas", [])))
            c3.metric("Critical Risks", len(risk.get("critical_risks", [])))
            st.info(risk.get("risk_summary", ""))
            import pandas as pd
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
                st.markdown("**Manual Tests:**")
                for t in strategy.get("manual_tests",[]):
                    st.markdown(f"• {t}")
            with cb:
                st.markdown("**Automation Candidates:**")
                for t in strategy.get("automated_tests",[]):
                    st.markdown(f"• {t}")

    with tab4:
        tc_data = outputs.get("test_cases", {})
        test_cases = tc_data.get("test_cases", [])
        if test_cases:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cases", len(test_cases))
            c2.metric("Complexity", tc_data.get("complexity_level","N/A").replace("_"," ").title())
            c3.metric("Batches Used", tc_data.get("batch_count","N/A"))
            st.info(tc_data.get("coverage_summary",""))
            import pandas as pd
            df = pd.DataFrame([{
                "ID": tc.get("tc_id",""),
                "Category": tc.get("category",""),
                "Title": tc.get("title",""),
                "Priority": tc.get("priority",""),
                "Type": tc.get("test_type","")
            } for tc in test_cases])
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download Test Cases CSV",
                data=csv,
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
            st.info("No existing test suite was provided. Upload a CSV on your next run to get coverage gap analysis.")

    st.divider()

    st.markdown("### ✏️ Your Review Notes")
    reviewer_notes = st.text_area(
        "Add corrections or notes for the Report Writer (optional)",
        value=st.session_state.reviewer_notes,
        height=100,
        placeholder="Add any corrections, missing scenarios, or notes..."
    )
    st.session_state.reviewer_notes = reviewer_notes

    col_approve, col_restart = st.columns(2)

    with col_approve:
        if st.button("✅ Approve and Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating final QA plan report..."):
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
        if st.button("🔄 Start Over", use_container_width=True):
            for key in ["current_result","final_report","html_report",
                        "show_review_gate","reviewer_notes","approved",
                        "temp_suite_path","example_req","agent_statuses"]:
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
        rec_bg = "rgba(189,227,195,0.2)"
        rec_icon = "✅"
    elif recommendation == "CONDITIONAL GO":
        rec_color = "#7d6608"
        rec_bg = "rgba(248,247,186,0.3)"
        rec_icon = "⚠️"
    else:
        rec_color = "#c0392b"
        rec_bg = "rgba(245,210,210,0.2)"
        rec_icon = "🚫"

    st.markdown(f"""
    <div style="background:{rec_bg};border:2px solid {rec_color};
                border-radius:12px;padding:2rem;margin:2rem 4rem 1rem;text-align:center">
      <div style="font-size:3rem">{rec_icon}</div>
      <div style="font-size:2rem;font-weight:800;color:{rec_color}">{recommendation}</div>
      <div style="color:{text_secondary};margin-top:0.5rem">
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

    st.markdown("**Executive Summary:**")
    st.info(final_report.get("executive_summary",""))

    st.markdown("**Next Steps:**")
    for i, step in enumerate(final_report.get("next_steps",[]), 1):
        st.markdown(f"{i}. {step}")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.html_report:
            st.download_button(
                "📄 Download HTML Report",
                data=st.session_state.html_report,
                file_name=f"qa_plan_{session_id}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )

    with col2:
        test_cases = outputs.get("test_cases",{}).get("test_cases",[])
        if test_cases:
            import pandas as pd
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
                "📊 Download Test Cases CSV",
                data=tc_df.to_csv(index=False),
                file_name=f"test_cases_{session_id}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col3:
        if st.button("🔄 New Analysis", use_container_width=True):
            for key in ["current_result","final_report","html_report",
                        "show_review_gate","reviewer_notes","approved",
                        "temp_suite_path","example_req","agent_statuses"]:
                if key in st.session_state:
                    del st.session_state[key]
            init_session_state()
            st.rerun()

    st.markdown(f"""
    <div style="text-align:center;color:{text_secondary};font-size:0.8rem;padding:2rem">
      Built by Thilangi Uththara De Silva ·
      <a href="https://github.com/thila98/qa-workflow-orchestrator" style="color:{teal}">GitHub</a> ·
      <a href="https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/" style="color:{teal}">LinkedIn</a>
    </div>
    """, unsafe_allow_html=True)
