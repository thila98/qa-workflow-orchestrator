"""
QA Workflow Orchestrator - Dashboard v4
Electric violet. Dark. Powerful. AI-native.
"""

import streamlit as st
import pandas as pd
import tempfile

st.set_page_config(
    page_title="QA Orchestrator",
    page_icon="\u26a1",
    layout="wide",
    initial_sidebar_state="collapsed"
)

MAX_FREE_RUNS = 5

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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

  *, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: Inter, -apple-system, sans-serif !important;
  }

  html, body {
    background: #0a0a0f !important;
    color: #f1f5f9 !important;
  }

  .stApp,
  .stApp > div,
  div[data-testid="stAppViewContainer"],
  div[data-testid="stMain"],
  section[data-testid="stMainBlockContainer"],
  .main,
  .main .block-container {
    background: #0a0a0f !important;
    padding: 0 !important;
    max-width: 100% !important;
  }

  #MainMenu, footer, header,
  section[data-testid="stSidebar"] { display: none !important; }

  /* ── NAV ── */
  .qa-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 2.5rem;
    background: rgba(10,10,15,0.95);
    border-bottom: 1px solid rgba(124,58,237,0.15);
    backdrop-filter: blur(10px);
    position: sticky;
    top: 0;
    z-index: 200;
  }

  .qa-logo {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f1f5f9;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    letter-spacing: -0.02em;
  }

  .logo-icon {
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    box-shadow: 0 0 12px rgba(124,58,237,0.4);
  }

  .qa-badge {
    font-size: 0.7rem;
    font-weight: 500;
    color: #a78bfa;
    background: rgba(124,58,237,0.1);
    border: 1px solid rgba(124,58,237,0.2);
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-family: "JetBrains Mono", monospace;
  }

  /* ── HERO ── */
  .qa-hero {
    padding: 3.5rem 2.5rem 3rem;
    background: radial-gradient(ellipse 60% 50% at 50% -10%,
      rgba(124,58,237,0.12) 0%,
      transparent 70%),
      #0a0a0f;
    border-bottom: 1px solid rgba(124,58,237,0.1);
  }

  .qa-eyebrow {
    font-size: 0.68rem;
    font-weight: 600;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    margin-bottom: 1rem;
    font-family: "JetBrains Mono", monospace;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .eyebrow-line {
    display: inline-block;
    width: 20px;
    height: 1px;
    background: #7c3aed;
  }

  .qa-title {
    font-size: 2.6rem;
    font-weight: 900;
    color: #f1f5f9;
    line-height: 1.1;
    letter-spacing: -0.04em;
    margin-bottom: 0.8rem;
  }

  .qa-title .accent {
    background: linear-gradient(135deg, #a78bfa 0%, #7c3aed 50%, #6d28d9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .qa-sub {
    font-size: 0.9rem;
    color: #64748b;
    line-height: 1.7;
    max-width: 520px;
    margin-bottom: 2.5rem;
  }

  /* Usage */
  .usage-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 1.5rem;
  }

  .pip { width: 32px; height: 3px; border-radius: 2px; }
  .pip-used { background: #7c3aed; }
  .pip-free { background: #1e1e2e; border: 1px solid #2d2d3f; }
  .usage-txt { font-size: 0.68rem; color: #64748b; margin-left: 0.3rem;
               font-family: "JetBrains Mono", monospace; }

  /* Textarea */
  .stTextArea > div > div > textarea {
    background: #0f0f1a !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 0.88rem !important;
    line-height: 1.65 !important;
    padding: 1rem !important;
    transition: border-color 0.2s !important;
  }

  .stTextArea > div > div > textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.12),
                0 0 20px rgba(124,58,237,0.08) !important;
    outline: none !important;
  }

  .stTextArea > div > div > textarea::placeholder { color: #2d2d45 !important; }
  .stTextArea label { color: #64748b !important; font-size: 0.75rem !important; }

  /* File uploader */
  [data-testid="stFileUploader"] > div {
    background: #0f0f1a !important;
    border: 1px dashed #1e1e30 !important;
    border-radius: 10px !important;
  }

  [data-testid="stFileUploader"] label { color: #64748b !important; }

  /* Primary button */
  div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #6d28d9) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 2rem !important;
    letter-spacing: -0.01em !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.3) !important;
    transition: all 0.2s !important;
  }

  div[data-testid="stButton"] button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
    box-shadow: 0 4px 30px rgba(124,58,237,0.5) !important;
    transform: translateY(-1px) !important;
  }

  /* Secondary button */
  div[data-testid="stButton"] button:not([kind="primary"]) {
    background: #0f0f1a !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
  }

  div[data-testid="stButton"] button:not([kind="primary"]):hover {
    border-color: #7c3aed !important;
    color: #a78bfa !important;
  }

  /* Expander */
  .stExpander {
    background: #0f0f1a !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 8px !important;
  }

  .stExpander summary {
    color: #64748b !important;
    font-size: 0.8rem !important;
  }

  /* Selectbox */
  .stSelectbox > div > div {
    background: #0f0f1a !important;
    border-color: #1e1e30 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
  }

  /* Metrics */
  [data-testid="metric-container"] {
    background: #0f0f1a !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 8px !important;
    padding: 0.9rem 1rem !important;
  }

  [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.7rem !important; }
  [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-weight: 700 !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1e1e30 !important;
    gap: 0 !important;
  }

  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    font-size: 0.8rem !important;
    padding: 0.6rem 1rem !important;
  }

  .stTabs [aria-selected="true"] {
    color: #a78bfa !important;
    border-bottom: 2px solid #7c3aed !important;
  }

  /* Dataframe */
  .stDataFrame { border: 1px solid #1e1e30 !important; border-radius: 8px !important; }
  [data-testid="stDataFrameResizable"] { background: #0f0f1a !important; }

  /* Info box */
  [data-testid="stInfo"] {
    background: rgba(124,58,237,0.06) !important;
    border: 1px solid rgba(124,58,237,0.15) !important;
    border-radius: 8px !important;
    color: #c4b5fd !important;
  }

  /* Download button */
  [data-testid="stDownloadButton"] button {
    background: #0f0f1a !important;
    border: 1px solid #1e1e30 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
  }

  /* Divider */
  hr { border-color: #1e1e30 !important; }

  /* Caption and text */
  .stMarkdown p { color: #64748b !important; font-size: 0.82rem !important; }
  .stCaption { color: #64748b !important; }
  div[data-testid="stMarkdownContainer"] p { color: #94a3b8 !important; }

  /* Progress */
  .stProgress > div > div > div {
    background: linear-gradient(90deg, #7c3aed, #a855f7) !important;
  }

  /* ── PIPELINE SECTION ── */
  .pipeline-section {
    padding: 2rem 2.5rem;
    background: #0a0a0f;
    border-bottom: 1px solid rgba(124,58,237,0.1);
  }

  .section-eyebrow {
    font-size: 0.65rem;
    font-weight: 600;
    color: #7c3aed;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    margin-bottom: 0.4rem;
    font-family: "JetBrains Mono", monospace;
  }

  .section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.2rem;
  }

  .section-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-bottom: 1.5rem;
  }

  /* Judge */
  .judge-center { display: flex; justify-content: center; margin-bottom: 0.6rem; }

  .judge-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(124,58,237,0.08);
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 50px;
    padding: 0.45rem 1.2rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #a78bfa;
    font-family: "JetBrains Mono", monospace;
    letter-spacing: -0.01em;
  }

  .judge-pill.running {
    animation: judge-pulse 1s ease-in-out infinite;
    border-color: rgba(124,58,237,0.5);
  }

  .judge-pill.passed {
    background: rgba(16,185,129,0.08);
    border-color: rgba(16,185,129,0.3);
    color: #10b981;
  }

  .judge-pill.warning {
    background: rgba(245,158,11,0.08);
    border-color: rgba(245,158,11,0.3);
    color: #f59e0b;
  }

  @keyframes judge-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(124,58,237,0); }
    50% { box-shadow: 0 0 0 6px rgba(124,58,237,0.15); }
  }

  .connector-center { display: flex; justify-content: center; margin-bottom: 0.6rem; }
  .connector-line { width: 1px; height: 18px;
    background: linear-gradient(to bottom, rgba(124,58,237,0.4), transparent); }

  /* Agent cards */
  .agents-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.6rem;
  }

  .agent-card {
    background: #0f0f1a;
    border: 1px solid #1e1e30;
    border-radius: 8px;
    padding: 0.9rem 0.6rem;
    text-align: center;
    transition: all 0.3s;
    border-top: 2px solid transparent;
  }

  .agent-card.idle { border-top-color: #1e1e30; }

  .agent-card.running {
    border-top-color: #7c3aed;
    background: rgba(124,58,237,0.04);
    animation: card-glow 1.5s ease-in-out infinite;
  }

  @keyframes card-glow {
    0%, 100% { box-shadow: none; }
    50% { box-shadow: 0 0 24px rgba(124,58,237,0.2); }
  }

  .agent-card.passed {
    border-top-color: #10b981;
    background: rgba(16,185,129,0.03);
  }

  .agent-card.warning {
    border-top-color: #f59e0b;
    background: rgba(245,158,11,0.03);
  }

  .agent-card.skipped { opacity: 0.3; }

  .agent-emoji { font-size: 1.2rem; display: block; margin-bottom: 0.4rem; }

  .agent-name {
    font-size: 0.65rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.12rem;
    line-height: 1.3;
  }

  .agent-desc { font-size: 0.58rem; color: #3d3d55; line-height: 1.4; margin-bottom: 0.4rem; }

  .agent-badge {
    display: inline-block;
    font-size: 0.55rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-family: "JetBrains Mono", monospace;
  }

  .b-idle { background: #1e1e30; color: #3d3d55; }
  .b-running { background: rgba(124,58,237,0.15); color: #a78bfa; }
  .b-passed { background: rgba(16,185,129,0.12); color: #10b981; }
  .b-warning { background: rgba(245,158,11,0.12); color: #f59e0b; }
  .b-skipped { background: #1e1e30; color: #3d3d55; }

  /* What you get */
  .what-card {
    background: #0f0f1a;
    border: 1px solid #1e1e30;
    border-radius: 10px;
    padding: 1.2rem;
  }

  .what-title {
    font-size: 0.65rem;
    font-weight: 700;
    color: #7c3aed;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.8rem;
    font-family: "JetBrains Mono", monospace;
  }

  .what-item {
    font-size: 0.76rem;
    color: #64748b;
    padding: 0.28rem 0;
    border-bottom: 1px solid #0f0f1a;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .what-check { color: #7c3aed; font-size: 0.65rem; }

  .meta-box {
    margin-top: 0.8rem;
    padding-top: 0.8rem;
    border-top: 1px solid #1e1e30;
    font-size: 0.66rem;
    color: #3d3d55;
    font-family: "JetBrains Mono", monospace;
    line-height: 2;
  }

  @media (max-width: 768px) {
    .agents-grid { grid-template-columns: repeat(3, 1fr); }
    .qa-hero, .pipeline-section { padding: 2rem 1.5rem; }
    .qa-title { font-size: 1.8rem; }
  }
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────

AGENTS = [
    ("\U0001f4cb", "Requirements Analyst", "Gaps & ambiguities"),
    ("\u26a0\ufe0f",  "Risk Assessor",        "Likelihood x Impact"),
    ("\U0001f5fa\ufe0f", "Test Strategist",   "Strategy & priorities"),
    ("\u270d\ufe0f", "Test Case Writer",      "All test categories"),
    ("\U0001f50d", "Coverage Analyser",        "Gap vs existing suite"),
    ("\U0001f4c4", "Report Writer",            "Final QA plan"),
]

# ── Paywall ───────────────────────────────────────────────────

if st.session_state.runs_used >= MAX_FREE_RUNS:
    st.markdown("""
    <div style="min-height:100vh;background:#0a0a0f;display:flex;
                align-items:center;justify-content:center;padding:3rem">
      <div style="text-align:center;max-width:420px">
        <div style="font-size:3rem;margin-bottom:1rem">\U0001f512</div>
        <h2 style="font-size:1.6rem;font-weight:800;color:#f1f5f9;
                   letter-spacing:-0.03em;margin-bottom:0.5rem">
          5 free runs used
        </h2>
        <p style="color:#64748b;line-height:1.7;margin-bottom:2rem;font-size:0.88rem">
          QA Orchestrator is open source. Self-host it for unlimited runs.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.link_button("\u2b50  View on GitHub",
                      "https://github.com/thila98/qa-workflow-orchestrator",
                      use_container_width=True)
        st.link_button("Connect on LinkedIn",
                      "https://linkedin.com/in/thilangi-de-silva-66bb0b190/",
                      use_container_width=True)
    st.stop()

# ── Nav ───────────────────────────────────────────────────────

st.markdown("""
<div class="qa-nav">
  <div class="qa-logo">
    <div class="logo-icon">\u26a1</div>
    QA Orchestrator
  </div>
  <div class="qa-badge">6-agent AI pipeline</div>
</div>
""", unsafe_allow_html=True)

# ── Pipeline renderer ─────────────────────────────────────────

def render_pipeline(statuses):
    judge_st = statuses.get("_judge", "idle")
    if judge_st == "running":
        jc, jt = "running", "\u27f3  Validating output..."
    elif judge_st == "passed":
        jc, jt = "passed", "\u2713  All outputs validated"
    elif judge_st == "warning":
        jc, jt = "warning", "\u26a1  Corrections applied"
    else:
        jc, jt = "", "\U0001f6e1\ufe0f  Judge Agent — Always Watching"

    cards = ""
    for emoji, name, desc in AGENTS:
        s = statuses.get(name, "idle")
        if s == "running":
            badge = f'<span class="agent-badge b-running">\u27f3 running</span>'
        elif s == "passed":
            badge = f'<span class="agent-badge b-passed">\u2713 passed</span>'
        elif s == "warning":
            badge = f'<span class="agent-badge b-warning">\u26a1 corrected</span>'
        elif s == "skipped":
            badge = f'<span class="agent-badge b-skipped">\u2014 skipped</span>'
        else:
            badge = f'<span class="agent-badge b-idle">idle</span>'

        cards += f"""
        <div class="agent-card {s}">
          <span class="agent-emoji">{emoji}</span>
          <div class="agent-name">{name}</div>
          <div class="agent-desc">{desc}</div>
          {badge}
        </div>"""

    return f"""
    <div class="pipeline-section">
      <div class="section-eyebrow">Live Agent Pipeline</div>
      <div class="section-title">Watch your AI QA team work in real time</div>
      <div class="section-sub">Agents animate only when running. Static when idle.</div>
      <div class="judge-center">
        <div class="judge-pill {jc}">{jt}</div>
      </div>
      <div class="connector-center">
        <div class="connector-line"></div>
      </div>
      <div class="agents-grid">{cards}</div>
    </div>"""

pipeline_ph = st.empty()
pipeline_ph.markdown(render_pipeline(st.session_state.agent_statuses), unsafe_allow_html=True)

# ── Hero + Input ──────────────────────────────────────────────

if not st.session_state.show_review_gate and not st.session_state.final_report:

    runs_rem = MAX_FREE_RUNS - st.session_state.runs_used
    pips = "".join([
        f'<div class="pip pip-{"used" if i < st.session_state.runs_used else "free"}"></div>'
        for i in range(MAX_FREE_RUNS)
    ])

    st.markdown(f"""
    <div class="qa-hero">
      <div class="qa-eyebrow">
        <span class="eyebrow-line"></span>
        AI-Powered QA Planning
      </div>
      <h1 class="qa-title">
        Most AI tools generate test cases.<br>
        <span class="accent">This one thinks like your entire QA team.</span>
      </h1>
      <p class="qa-sub">
        6 specialist agents analyse your requirement, assess risk, design strategy,
        write test cases, check coverage, and produce a complete QA plan —
        with automatic correction loops at every step.
      </p>
      <div class="usage-row">
        {pips}
        <span class="usage-txt">{runs_rem} free run{"s" if runs_rem != 1 else ""} remaining</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_main, col_side = st.columns([3, 1])

    with col_main:
        with st.expander("Load an example requirement"):
            examples = {
                "User Login with Lockout": "User login with email and password. After 3 consecutive failed login attempts the account locks for 15 minutes. Users can reset their password via email. The reset link expires after 24 hours. Passwords must be at least 8 characters with one uppercase and one number.",
                "SOP Acknowledgement": "Workspace Admins can mark any published SOP as requiring acknowledgement. Users who open a flagged SOP see an Acknowledge button. Clicking opens a confirmation popup with SOP name and version. User ticks checkbox and clicks Confirm. Acknowledgement is recorded with timestamp. Users can only acknowledge once per version. If SOP is updated, all users must re-acknowledge.",
                "File Upload Feature": "File upload feature accepting PDF and DOCX files up to 10MB. Files scanned for malware before saving. Email confirmation sent on successful upload. Files stored for 30 days then auto-deleted unless marked permanent. Authenticated users only.",
            }
            sel = st.selectbox("Pick one:", ["Select..."] + list(examples.keys()),
                               label_visibility="collapsed")
            if sel and sel != "Select...":
                if st.button("Use this example"):
                    st.session_state["ex_req"] = examples[sel]
                    st.rerun()

        requirement = st.text_area(
            "Your requirement",
            value=st.session_state.get("ex_req", ""),
            height=180,
            placeholder="Describe the feature you want to test...\n\nThe more detail you provide, the better the test cases.",
            label_visibility="visible"
        )

        char_c = len(requirement.strip())
        if char_c > 0:
            if char_c < 100:
                st.caption(f"\u26a0\ufe0f {char_c} chars — add more detail")
            else:
                st.caption(f"\u2713 {char_c} chars")

        uploaded = st.file_uploader(
            "Existing test suite CSV — optional, enables coverage gap analysis",
            type=["csv"]
        )

        suite_path = None
        if uploaded:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                suite_path = tmp.name
            st.session_state["suite_path"] = suite_path
            st.success(f"\u2713 {uploaded.name}")

        if "suite_path" in st.session_state and not uploaded:
            suite_path = st.session_state.get("suite_path")

        run_btn = st.button(
            "\u26a1  Run QA Workflow",
            disabled=st.session_state.workflow_running or not requirement.strip(),
            type="primary"
        )

    with col_side:
        st.markdown("""
        <div class="what-card">
          <div class="what-title">What you get</div>
          <div class="what-item"><span class="what-check">\u2192</span> Requirements gap analysis</div>
          <div class="what-item"><span class="what-check">\u2192</span> Risk matrix with scores</div>
          <div class="what-item"><span class="what-check">\u2192</span> Test strategy document</div>
          <div class="what-item"><span class="what-check">\u2192</span> 20+ structured test cases</div>
          <div class="what-item"><span class="what-check">\u2192</span> Coverage gap report</div>
          <div class="what-item"><span class="what-check">\u2192</span> Go / No-Go recommendation</div>
          <div class="what-item"><span class="what-check">\u2192</span> Downloadable HTML report</div>
          <div class="meta-box">
            time &nbsp;&nbsp;90–120s<br>
            cost &nbsp;&nbsp;$0.03–0.10<br>
            agents  4–6
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Run ──────────────────────────────────────────────────

    if run_btn and requirement.strip():
        from validation.input_validator import validate_input
        chk = validate_input(requirement)
        if not chk.is_valid:
            st.error(f"\u274c {chk.error_message}")
        else:
            st.session_state.workflow_running = True
            prog = st.progress(0)
            status_ph = st.empty()
            statuses = {name: "idle" for _, name, _ in AGENTS}
            statuses["_judge"] = "idle"

            def upd(s, p=0):
                pipeline_ph.markdown(render_pipeline(s), unsafe_allow_html=True)
                prog.progress(p)

            try:
                from main import run_workflow

                for i, (_, name, _) in enumerate(AGENTS[:4]):
                    statuses[name] = "running"
                    statuses["_judge"] = "running"
                    upd(statuses, i * 15 // 100)
                    status_ph.caption(f"Running {name}...")

                result = run_workflow(
                    requirement=requirement,
                    existing_test_suite_path=suite_path
                )

                if result.get("status") == "error":
                    st.error(f"\u274c {result.get('message','Unknown error')}")
                    st.session_state.workflow_running = False
                else:
                    jrs = result.get("judge_results", {})
                    for _, name, _ in AGENTS[:4]:
                        rec = jrs.get(name, {}).get("recommendation", "PASS")
                        statuses[name] = "warning" if rec == "PASS_WITH_WARNINGS" else "passed"

                    statuses["Coverage Analyser"] = "passed" if suite_path else "skipped"
                    statuses["Report Writer"] = "idle"
                    has_warn = any(v == "warning" for k, v in statuses.items() if k != "_judge")
                    statuses["_judge"] = "warning" if has_warn else "passed"

                    upd(statuses, 1)
                    status_ph.success("\u2713 Workflow complete — review outputs below")

                    st.session_state.runs_used += 1
                    st.session_state.current_result = result
                    st.session_state.agent_statuses = statuses
                    st.session_state.show_review_gate = True
                    st.session_state.workflow_running = False
                    st.rerun()

            except Exception as e:
                st.error(f"\u274c {str(e)}")
                st.session_state.workflow_running = False

# ── Review Gate ───────────────────────────────────────────────

elif st.session_state.show_review_gate and not st.session_state.final_report:

    result = st.session_state.current_result
    outputs = result.get("outputs", {})
    conf = result.get("confidence", {})
    sid = result.get("session_id", "")
    cs = conf.get("score", 0)
    cost = result.get("workflow_state", {}).get("total_cost_usd", 0)

    st.markdown(f"""
    <div style="padding:1.5rem 2.5rem;background:#0a0a0f;border-bottom:1px solid #1e1e30">
      <div style="font-size:0.65rem;font-weight:600;color:#7c3aed;text-transform:uppercase;
                  letter-spacing:0.15em;margin-bottom:0.3rem;font-family:JetBrains Mono,monospace">
        Human Review Gate
      </div>
      <div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;margin-bottom:0.2rem">
        Review agent outputs before generating your report
      </div>
      <div style="font-size:0.75rem;color:#64748b;font-family:JetBrains Mono,monospace">
        session/{sid} &nbsp;·&nbsp; confidence {cs:.0%} &nbsp;·&nbsp; cost ${cost:.4f}
      </div>
    </div>
    """, unsafe_allow_html=True)

    flags = conf.get("flags", [])
    if flags:
        with st.expander(f"\u26a0\ufe0f {len(flags)} validation flag(s)"):
            for f in flags:
                if "CRITICAL" in f or "HALLUCINATION" in f:
                    st.error(f)
                else:
                    st.warning(f)

    t1, t2, t3, t4, t5 = st.tabs([
        "Requirements", "Risk", "Strategy", "Test Cases", "Coverage"
    ])

    with t1:
        r = outputs.get("requirements_analysis", {})
        if r:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Quality", f"{r.get('quality_score','?')}/10")
            c2.metric("Gaps", len(r.get("gaps",[])))
            c3.metric("Ambiguities", len(r.get("ambiguities",[])))
            c4.metric("Testable", "Yes" if r.get("is_testable") else "No")
            st.info(r.get("summary",""))
            for g in r.get("gaps",[]): st.warning(f"• {g}")
            for q in r.get("clarification_questions",[]): st.info(f"? {q}")

    with t2:
        r = outputs.get("risk_assessment", {})
        if r:
            c1,c2,c3 = st.columns(3)
            c1.metric("Overall Risk", r.get("overall_risk_level","?"))
            c2.metric("Risk Areas", len(r.get("risk_areas",[])))
            c3.metric("Critical", len(r.get("critical_risks",[])))
            st.info(r.get("risk_summary",""))
            ra = r.get("risk_areas",[])
            if ra:
                df = pd.DataFrame([{
                    "Risk": x.get("name",""), "Category": x.get("category",""),
                    "L": x.get("likelihood",""), "I": x.get("impact",""),
                    "Score": x.get("score",""), "Priority": x.get("priority_level","")
                } for x in ra])
                st.dataframe(df, use_container_width=True)

    with t3:
        r = outputs.get("test_strategy", {})
        if r:
            c1,c2,c3 = st.columns(3)
            c1.metric("Est. Cases", r.get("estimated_test_cases","?"))
            c2.metric("Est. Hours", r.get("estimated_hours","?"))
            c3.metric("Security", "Required" if r.get("security_testing_required") else "No")
            st.info(r.get("strategy_summary",""))
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**Manual**")
                for t in r.get("manual_tests",[]): st.markdown(f"• {t}")
            with cb:
                st.markdown("**Automate**")
                for t in r.get("automated_tests",[]): st.markdown(f"• {t}")

    with t4:
        tc = outputs.get("test_cases", {})
        tcs = tc.get("test_cases", [])
        if tcs:
            c1,c2,c3 = st.columns(3)
            c1.metric("Total Cases", len(tcs))
            c2.metric("Complexity", tc.get("complexity_level","?").replace("_"," ").title())
            c3.metric("Batches", tc.get("batch_count","?"))
            st.info(tc.get("coverage_summary",""))
            df = pd.DataFrame([{
                "ID": x.get("tc_id",""), "Category": x.get("category",""),
                "Title": x.get("title",""), "Priority": x.get("priority",""),
                "Type": x.get("test_type","")
            } for x in tcs])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download CSV", df.to_csv(index=False),
                             f"test_cases_{sid}.csv", "text/csv")

    with t5:
        cov = outputs.get("coverage_analysis", {})
        if cov and not cov.get("skipped"):
            c1,c2 = st.columns(2)
            c1.metric("Coverage", cov.get("coverage_estimate","?"))
            c2.metric("Adding Value", cov.get("new_tests_adding_value","?"))
            st.info(cov.get("coverage_summary",""))
        else:
            st.info("No existing test suite uploaded. Add a CSV next run for coverage gap analysis.")

    st.divider()
    notes = st.text_area("Notes for Report Writer (optional)",
                        value=st.session_state.reviewer_notes, height=80,
                        placeholder="Corrections or missing scenarios...",
                        label_visibility="collapsed")
    st.session_state.reviewer_notes = notes

    ca, cb = st.columns(2)
    with ca:
        if st.button("\u2713  Approve and Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    from agents.report_writer import write_report
                    from tools.report_generator import generate_html_report
                    fr = write_report(requirement=result.get("requirement",""),
                                     all_outputs=outputs, human_reviewer_notes=notes,
                                     confidence_score=cs)
                    html = generate_html_report(requirement=result.get("requirement",""),
                                               all_outputs=outputs, final_report=fr,
                                               confidence=conf,
                                               workflow_state_data=result.get("workflow_state",{}),
                                               session_id=sid)
                    st.session_state.final_report = fr
                    st.session_state.html_report = html
                    st.rerun()
                except Exception as e:
                    st.error(f"\u274c {str(e)}")
    with cb:
        if st.button("\u2190  Start Over", use_container_width=True):
            for k in ["current_result","final_report","html_report","show_review_gate",
                      "reviewer_notes","agent_statuses","suite_path","ex_req"]:
                st.session_state.pop(k, None)
            init_session_state()
            st.rerun()

# ── Final Report ──────────────────────────────────────────────

elif st.session_state.final_report:

    fr = st.session_state.final_report
    result = st.session_state.current_result or {}
    sid = result.get("session_id","")
    outputs = result.get("outputs",{})
    rec = fr.get("go_no_go_recommendation","GO")

    if rec == "GO":
        rc, rb, ri = "#10b981", "rgba(16,185,129,0.08)", "\u2713"
    elif rec == "CONDITIONAL GO":
        rc, rb, ri = "#f59e0b", "rgba(245,158,11,0.08)", "\u26a0"
    else:
        rc, rb, ri = "#ef4444", "rgba(239,68,68,0.08)", "\u00d7"

    st.markdown(f"""
    <div style="background:{rb};border:1px solid {rc}33;border-radius:10px;
                padding:1.5rem 2rem;margin:1.5rem 2.5rem;text-align:center">
      <div style="font-size:2rem;margin-bottom:0.3rem">{ri}</div>
      <div style="font-size:1.6rem;font-weight:800;color:{rc};letter-spacing:-0.03em">{rec}</div>
      <div style="font-size:0.85rem;color:#64748b;margin-top:0.4rem">
        {fr.get("go_no_go_reasoning","")}
      </div>
    </div>
    """, unsafe_allow_html=True)

    suite = fr.get("test_suite_summary",{})
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Test Cases", suite.get("total_test_cases","?"))
    c2.metric("High Priority", suite.get("high_priority_count","?"))
    c3.metric("Auto Candidates", suite.get("automation_candidates","?"))
    c4.metric("Confidence", f"{result.get('confidence',{}).get('score',0):.0%}")

    st.markdown("**Executive Summary**")
    st.info(fr.get("executive_summary",""))

    if fr.get("next_steps"):
        st.markdown("**Next Steps**")
        for i, s in enumerate(fr["next_steps"], 1):
            st.markdown(f"{i}. {s}")

    st.divider()
    ca, cb, cc = st.columns(3)

    with ca:
        if st.session_state.html_report:
            st.download_button("\u2193  Download HTML Report",
                             data=st.session_state.html_report,
                             file_name=f"qa_plan_{sid}.html", mime="text/html",
                             use_container_width=True, type="primary")
    with cb:
        tcs = outputs.get("test_cases",{}).get("test_cases",[])
        if tcs:
            df = pd.DataFrame([{
                "TC_ID": x.get("tc_id",""), "Category": x.get("category",""),
                "Title": x.get("title",""), "Precondition": x.get("precondition",""),
                "Steps": x.get("steps",""), "Expected Result": x.get("expected_result",""),
                "Priority": x.get("priority",""), "Test Type": x.get("test_type",""),
                "Risk Area": x.get("risk_area",""),
                "Req Reference": x.get("requirement_reference","")
            } for x in tcs])
            st.download_button("\u2193  Download Test Cases CSV",
                             data=df.to_csv(index=False),
                             file_name=f"test_cases_{sid}.csv", mime="text/csv",
                             use_container_width=True)
    with cc:
        if st.button("\u2190  New Analysis", use_container_width=True):
            for k in ["current_result","final_report","html_report","show_review_gate",
                      "reviewer_notes","agent_statuses","suite_path","ex_req"]:
                st.session_state.pop(k, None)
            init_session_state()
            st.rerun()

    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1rem;font-size:0.72rem;color:#3d3d55;
                font-family:JetBrains Mono,monospace">
      built by thilangi uththara de silva &nbsp;·&nbsp;
      <a href="https://github.com/thila98/qa-workflow-orchestrator"
         style="color:#7c3aed">github</a> &nbsp;·&nbsp;
      <a href="https://linkedin.com/in/thilangi-de-silva-66bb0b190/"
         style="color:#7c3aed">linkedin</a>
    </div>
    """, unsafe_allow_html=True)
