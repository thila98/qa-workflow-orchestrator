"""
QA Workflow Orchestrator - Dashboard v5
Headline + Input FIRST. Pipeline SECOND.
Full width. Bold. Confident.
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
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

  *, *::before, *::after { box-sizing: border-box; }

  html, body,
  .stApp,
  .stApp > div,
  div[data-testid="stAppViewContainer"],
  div[data-testid="stMain"],
  section[data-testid="stMainBlockContainer"],
  .main,
  .main .block-container {
    background: #08080f !important;
    font-family: Inter, sans-serif !important;
    padding: 0 !important;
    max-width: 100% !important;
    color: #f1f5f9 !important;
  }

  #MainMenu, footer, header,
  section[data-testid="stSidebar"],
  div[data-testid="collapsedControl"] { display: none !important; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #08080f; }
  ::-webkit-scrollbar-thumb { background: #2d1b69; border-radius: 3px; }

  /* ── NAV ── */
  .qa-nav {
    background: #08080f;
    border-bottom: 1px solid #1a1a2e;
    padding: 1rem 3rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .qa-logo {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    font-size: 1rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.02em;
  }

  .logo-box {
    width: 30px;
    height: 30px;
    background: linear-gradient(135deg, #7c3aed, #a855f7);
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    box-shadow: 0 0 16px rgba(124,58,237,0.5);
  }

  .nav-right {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }

  .nav-link {
    font-size: 0.78rem;
    color: #475569;
    text-decoration: none;
    transition: color 0.2s;
  }

  .nav-link:hover { color: #a78bfa; }

  .nav-runs {
    font-size: 0.72rem;
    font-weight: 600;
    color: #a78bfa;
    background: rgba(124,58,237,0.12);
    border: 1px solid rgba(124,58,237,0.25);
    padding: 0.25rem 0.8rem;
    border-radius: 20px;
    font-family: "JetBrains Mono", monospace;
  }

  /* ── HERO ── */
  .qa-hero {
    background: radial-gradient(ellipse 80% 60% at 50% 0%,
      rgba(124,58,237,0.15) 0%,
      rgba(124,58,237,0.04) 40%,
      transparent 70%),
      #08080f;
    padding: 4rem 3rem 3.5rem;
    border-bottom: 1px solid #1a1a2e;
  }

  .hero-inner {
    max-width: 1100px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 340px;
    gap: 3rem;
    align-items: start;
  }

  .hero-left {}

  .hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.68rem;
    font-weight: 600;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 1.2rem;
    font-family: "JetBrains Mono", monospace;
  }

  .tag-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #7c3aed;
    animation: dot-blink 2s ease-in-out infinite;
  }

  @keyframes dot-blink {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }

  .hero-title {
    font-size: 2.8rem;
    font-weight: 900;
    color: #f1f5f9;
    line-height: 1.1;
    letter-spacing: -0.04em;
    margin-bottom: 1rem;
  }

  .hero-title .violet {
    background: linear-gradient(135deg, #c4b5fd 0%, #a78bfa 40%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .hero-desc {
    font-size: 0.95rem;
    color: #64748b;
    line-height: 1.7;
    max-width: 520px;
    margin-bottom: 2rem;
  }

  /* Stat strip */
  .stat-strip {
    display: flex;
    gap: 2rem;
    padding: 1.2rem 0;
    border-top: 1px solid #1a1a2e;
    border-bottom: 1px solid #1a1a2e;
    margin-bottom: 2rem;
  }

  .stat-item { text-align: left; }

  .stat-num {
    font-size: 1.6rem;
    font-weight: 800;
    color: #a78bfa;
    line-height: 1;
    letter-spacing: -0.03em;
  }

  .stat-lbl {
    font-size: 0.65rem;
    font-weight: 600;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.2rem;
    font-family: "JetBrains Mono", monospace;
  }

  /* Input area */
  .input-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
    font-family: "JetBrains Mono", monospace;
  }

  .stTextArea > div > div > textarea {
    background: #0d0d1a !important;
    border: 1.5px solid #1e1e35 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 0.9rem !important;
    line-height: 1.65 !important;
    padding: 1rem 1.1rem !important;
    font-family: Inter, sans-serif !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    resize: vertical !important;
  }

  .stTextArea > div > div > textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.15),
                0 0 30px rgba(124,58,237,0.08) !important;
    outline: none !important;
  }

  .stTextArea > div > div > textarea::placeholder {
    color: #252540 !important;
    font-style: italic !important;
  }

  .stTextArea label { display: none !important; }

  /* File uploader */
  [data-testid="stFileUploader"] section {
    background: #0d0d1a !important;
    border: 1.5px dashed #1e1e35 !important;
    border-radius: 10px !important;
    padding: 0.8rem !important;
    transition: border-color 0.2s !important;
  }

  [data-testid="stFileUploader"] section:hover {
    border-color: #7c3aed !important;
  }

  [data-testid="stFileUploader"] label {
    color: #475569 !important;
    font-size: 0.78rem !important;
  }

  [data-testid="stFileUploaderDropzoneInstructions"] {
    color: #334155 !important;
    font-size: 0.75rem !important;
  }

  /* Run button */
  div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 2rem !important;
    letter-spacing: -0.01em !important;
    box-shadow: 0 4px 24px rgba(124,58,237,0.35) !important;
    transition: all 0.2s !important;
    width: 100% !important;
  }

  div[data-testid="stButton"] button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
    box-shadow: 0 6px 30px rgba(124,58,237,0.5) !important;
    transform: translateY(-2px) !important;
  }

  div[data-testid="stButton"] button[kind="primary"]:disabled {
    background: #1e1e35 !important;
    box-shadow: none !important;
    color: #334155 !important;
    transform: none !important;
  }

  /* Secondary button */
  div[data-testid="stButton"] button:not([kind="primary"]) {
    background: #0d0d1a !important;
    border: 1px solid #1e1e35 !important;
    border-radius: 8px !important;
    color: #64748b !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
  }

  div[data-testid="stButton"] button:not([kind="primary"]):hover {
    border-color: #7c3aed !important;
    color: #a78bfa !important;
  }

  /* What you get card */
  .what-card {
    background: #0d0d1a;
    border: 1px solid #1e1e35;
    border-radius: 12px;
    padding: 1.5rem;
    position: sticky;
    top: 80px;
  }

  .what-title {
    font-size: 0.65rem;
    font-weight: 700;
    color: #7c3aed;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 1rem;
    font-family: "JetBrains Mono", monospace;
  }

  .what-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0;
    border-bottom: 1px solid #12121f;
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .what-row:last-of-type { border-bottom: none; }
  .what-arr { color: #7c3aed; font-size: 0.7rem; flex-shrink: 0; }

  .what-meta {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #1e1e35;
    font-size: 0.65rem;
    color: #334155;
    font-family: "JetBrains Mono", monospace;
    line-height: 2;
  }

  /* Usage pips */
  .usage-wrap {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    margin-bottom: 1rem;
  }

  .u-pip { width: 36px; height: 3px; border-radius: 2px; }
  .u-used { background: #7c3aed; }
  .u-free { background: #1a1a2e; }
  .u-txt { font-size: 0.68rem; color: #334155; margin-left: 0.4rem;
           font-family: "JetBrains Mono", monospace; }

  /* Expander */
  .stExpander {
    background: #0d0d1a !important;
    border: 1px solid #1e1e35 !important;
    border-radius: 8px !important;
    margin-bottom: 0.8rem !important;
  }

  details summary {
    color: #475569 !important;
    font-size: 0.78rem !important;
    padding: 0.6rem 0.8rem !important;
  }

  .stSelectbox > div { background: #0d0d1a !important; border-color: #1e1e35 !important; }
  .stSelectbox label { color: #475569 !important; font-size: 0.75rem !important; }

  /* ── PIPELINE SECTION ── */
  .pipeline-section {
    background: #08080f;
    padding: 2.5rem 3rem;
    border-bottom: 1px solid #1a1a2e;
  }

  .pipe-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 1.5rem;
  }

  .pipe-title-group {}

  .pipe-eyebrow {
    font-size: 0.65rem;
    font-weight: 600;
    color: #7c3aed;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    margin-bottom: 0.3rem;
    font-family: "JetBrains Mono", monospace;
  }

  .pipe-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.02em;
  }

  /* Judge bar */
  .judge-bar {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    background: #0d0d1a;
    border: 1px solid rgba(124,58,237,0.2);
    border-radius: 8px;
    padding: 0.7rem 1.2rem;
    margin-bottom: 1rem;
  }

  .judge-icon { font-size: 1rem; }

  .judge-info { flex: 1; }

  .judge-name {
    font-size: 0.78rem;
    font-weight: 600;
    color: #a78bfa;
    font-family: "JetBrains Mono", monospace;
  }

  .judge-desc {
    font-size: 0.68rem;
    color: #334155;
    margin-top: 0.1rem;
  }

  .judge-status-badge {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-family: "JetBrains Mono", monospace;
  }

  .js-idle { background: #1a1a2e; color: #334155; }
  .js-running { background: rgba(124,58,237,0.15); color: #a78bfa;
                animation: badge-pulse 1s ease-in-out infinite; }
  .js-passed { background: rgba(16,185,129,0.12); color: #10b981; }
  .js-warning { background: rgba(245,158,11,0.12); color: #f59e0b; }

  @keyframes badge-pulse {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
  }

  /* Agent cards */
  .agents-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.7rem;
  }

  .a-card {
    background: #0d0d1a;
    border: 1px solid #1e1e35;
    border-radius: 10px;
    padding: 1rem 0.8rem;
    text-align: center;
    transition: all 0.3s ease;
    border-top: 3px solid transparent;
    position: relative;
    overflow: hidden;
  }

  .a-card::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: transparent;
    transition: background 0.3s;
  }

  .a-card.idle { border-top-color: #1e1e35; }

  .a-card.running {
    border-top-color: #7c3aed;
    background: linear-gradient(180deg, rgba(124,58,237,0.06) 0%, #0d0d1a 100%);
    animation: a-run 1.8s ease-in-out infinite;
  }

  @keyframes a-run {
    0%, 100% { box-shadow: 0 0 0 0 rgba(124,58,237,0); }
    50% { box-shadow: 0 0 30px rgba(124,58,237,0.25); }
  }

  .a-card.passed {
    border-top-color: #10b981;
    background: linear-gradient(180deg, rgba(16,185,129,0.05) 0%, #0d0d1a 100%);
  }

  .a-card.warning {
    border-top-color: #f59e0b;
    background: linear-gradient(180deg, rgba(245,158,11,0.05) 0%, #0d0d1a 100%);
  }

  .a-card.skipped { opacity: 0.25; }

  .a-num {
    font-size: 0.6rem;
    font-weight: 700;
    color: #2d2d45;
    font-family: "JetBrains Mono", monospace;
    margin-bottom: 0.4rem;
  }

  .a-emoji { font-size: 1.4rem; display: block; margin-bottom: 0.5rem; }

  .a-name {
    font-size: 0.72rem;
    font-weight: 700;
    color: #e2e8f0;
    line-height: 1.3;
    margin-bottom: 0.2rem;
  }

  .a-role {
    font-size: 0.62rem;
    color: #2d2d45;
    line-height: 1.4;
    margin-bottom: 0.5rem;
  }

  .a-badge {
    display: inline-block;
    font-size: 0.58rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-family: "JetBrains Mono", monospace;
  }

  .ab-idle { background: #12121f; color: #2d2d45; }
  .ab-running { background: rgba(124,58,237,0.2); color: #c4b5fd; }
  .ab-passed { background: rgba(16,185,129,0.15); color: #34d399; }
  .ab-warning { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .ab-skipped { background: #12121f; color: #2d2d45; }

  /* Review gate */
  .review-header {
    background: #08080f;
    border-bottom: 1px solid #1a1a2e;
    padding: 1.5rem 3rem;
  }

  .review-eyebrow {
    font-size: 0.65rem;
    font-weight: 600;
    color: #7c3aed;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    margin-bottom: 0.3rem;
    font-family: "JetBrains Mono", monospace;
  }

  .review-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.2rem;
  }

  .review-meta {
    font-size: 0.72rem;
    color: #334155;
    font-family: "JetBrains Mono", monospace;
  }

  /* Metrics */
  [data-testid="metric-container"] {
    background: #0d0d1a !important;
    border: 1px solid #1e1e35 !important;
    border-radius: 8px !important;
    padding: 0.9rem 1rem !important;
  }

  [data-testid="metric-container"] label {
    color: #334155 !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: "JetBrains Mono", monospace !important;
  }

  [data-testid="stMetricValue"] {
    color: #e2e8f0 !important;
    font-weight: 700 !important;
    font-size: 1.4rem !important;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1a1a2e !important;
    gap: 0 !important;
    padding: 0 3rem !important;
  }

  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #334155 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 0.7rem 1.2rem !important;
    border-bottom: 2px solid transparent !important;
  }

  .stTabs [aria-selected="true"] {
    color: #a78bfa !important;
    border-bottom: 2px solid #7c3aed !important;
  }

  .stTabs [data-testid="stTabContent"] {
    background: #08080f !important;
    padding: 1.5rem 3rem !important;
  }

  /* Dataframe */
  .stDataFrame iframe {
    background: #0d0d1a !important;
    border: 1px solid #1e1e35 !important;
    border-radius: 8px !important;
  }

  /* Info */
  [data-testid="stInfo"] {
    background: rgba(124,58,237,0.06) !important;
    border: 1px solid rgba(124,58,237,0.15) !important;
    border-radius: 8px !important;
    color: #c4b5fd !important;
    font-size: 0.85rem !important;
  }

  [data-testid="stWarning"] {
    background: rgba(245,158,11,0.06) !important;
    border: 1px solid rgba(245,158,11,0.15) !important;
    border-radius: 8px !important;
    color: #fbbf24 !important;
    font-size: 0.82rem !important;
  }

  /* Download */
  [data-testid="stDownloadButton"] button {
    background: #0d0d1a !important;
    border: 1px solid #1e1e35 !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
  }

  [data-testid="stDownloadButton"] button:hover {
    border-color: #7c3aed !important;
    color: #a78bfa !important;
  }

  /* Divider */
  hr { border-color: #1a1a2e !important; margin: 1.5rem 0 !important; }

  /* Text */
  p, .stMarkdown p { color: #64748b !important; font-size: 0.85rem !important; }
  .stCaption p { color: #334155 !important; font-size: 0.72rem !important; }

  /* Progress */
  .stProgress > div > div > div {
    background: linear-gradient(90deg, #7c3aed, #a855f7) !important;
    border-radius: 2px !important;
  }

  .stProgress > div {
    background: #1a1a2e !important;
    border-radius: 2px !important;
  }

  /* Go/No-Go */
  .gonogo {
    border-radius: 12px;
    padding: 1.8rem 2rem;
    margin: 1.5rem 0;
    text-align: center;
  }

  .gonogo-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
  .gonogo-rec { font-size: 1.8rem; font-weight: 900; letter-spacing: -0.03em; }
  .gonogo-reason { font-size: 0.85rem; color: #64748b; margin-top: 0.5rem; }

  @media (max-width: 900px) {
    .hero-inner { grid-template-columns: 1fr; }
    .agents-row { grid-template-columns: repeat(3, 1fr); }
    .qa-hero, .pipeline-section { padding: 2rem 1.5rem; }
    .stTabs [data-baseweb="tab-list"] { padding: 0 1.5rem !important; }
    .stTabs [data-testid="stTabContent"] { padding: 1rem 1.5rem !important; }
  }
</style>
""", unsafe_allow_html=True)

# ── Agents data ───────────────────────────────────────────────

AGENTS = [
    ("\U0001f4cb", "Requirements Analyst", "Gaps & ambiguities"),
    ("\u26a0\ufe0f",  "Risk Assessor",        "Likelihood x impact"),
    ("\U0001f5fa\ufe0f", "Test Strategist",   "Strategy & scope"),
    ("\u270d\ufe0f", "Test Case Writer",      "All test categories"),
    ("\U0001f50d", "Coverage Analyser",        "Gap vs existing tests"),
    ("\U0001f4c4", "Report Writer",            "Final QA plan"),
]

# ── Paywall ───────────────────────────────────────────────────

if st.session_state.runs_used >= MAX_FREE_RUNS:
    st.markdown("""
    <div style="min-height:100vh;background:#08080f;display:flex;
                align-items:center;justify-content:center">
      <div style="text-align:center;max-width:400px;padding:3rem">
        <div style="font-size:3rem;margin-bottom:1.2rem">\U0001f512</div>
        <h2 style="font-size:1.7rem;font-weight:900;color:#f1f5f9;
                   letter-spacing:-0.04em;margin-bottom:0.6rem">
          5 free runs used
        </h2>
        <p style="color:#475569;line-height:1.7;margin-bottom:2rem;font-size:0.9rem">
          QA Orchestrator is open source.<br>
          Self-host it for unlimited runs.
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

runs_rem = MAX_FREE_RUNS - st.session_state.runs_used

st.markdown(f"""
<div class="qa-nav">
  <div class="qa-logo">
    <div class="logo-box">\u26a1</div>
    QA Orchestrator
  </div>
  <div class="nav-right">
    <a href="https://github.com/thila98/qa-workflow-orchestrator"
       class="nav-link" target="_blank">GitHub</a>
    <a href="https://linkedin.com/in/thilangi-de-silva-66bb0b190/"
       class="nav-link" target="_blank">LinkedIn</a>
    <span class="nav-runs">{runs_rem} run{"s" if runs_rem != 1 else ""} free</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Pipeline renderer ─────────────────────────────────────────

def render_pipeline(statuses):
    js = statuses.get("_judge", "idle")
    if js == "running":
        jc, jt = "js-running", "\u27f3 Validating..."
    elif js == "passed":
        jc, jt = "js-passed", "\u2713 All outputs validated"
    elif js == "warning":
        jc, jt = "js-warning", "\u26a1 Corrections applied"
    else:
        jc, jt = "js-idle", "Watching"

    cards = ""
    for i, (emoji, name, role) in enumerate(AGENTS, 1):
        s = statuses.get(name, "idle")
        if s == "running":
            b = f'<span class="a-badge ab-running">\u27f3 running</span>'
        elif s == "passed":
            b = f'<span class="a-badge ab-passed">\u2713 passed</span>'
        elif s == "warning":
            b = f'<span class="a-badge ab-warning">\u26a1 corrected</span>'
        elif s == "skipped":
            b = f'<span class="a-badge ab-skipped">\u2014 skipped</span>'
        else:
            b = f'<span class="a-badge ab-idle">idle</span>'

        cards += f"""
        <div class="a-card {s}">
          <div class="a-num">0{i}</div>
          <span class="a-emoji">{emoji}</span>
          <div class="a-name">{name}</div>
          <div class="a-role">{role}</div>
          {b}
        </div>"""

    return f"""
    <div class="pipeline-section">
      <div class="pipe-header">
        <div class="pipe-title-group">
          <div class="pipe-eyebrow">Live Agent Pipeline</div>
          <div class="pipe-title">Watch your AI QA team work in real time</div>
        </div>
      </div>
      <div class="judge-bar">
        <div class="judge-icon">\U0001f6e1\ufe0f</div>
        <div class="judge-info">
          <div class="judge-name">Judge Agent</div>
          <div class="judge-desc">
            Independently validates every agent output before it passes downstream.
            Catches hallucinations, flags gaps, triggers automatic correction loops.
          </div>
        </div>
        <span class="judge-status-badge {jc}">{jt}</span>
      </div>
      <div class="agents-row">{cards}</div>
    </div>"""

pipeline_ph = st.empty()

# ── Main layout ───────────────────────────────────────────────

if not st.session_state.show_review_gate and not st.session_state.final_report:

    pips = "".join([
        f'<div class="u-pip u-{"used" if i < st.session_state.runs_used else "free"}"></div>'
        for i in range(MAX_FREE_RUNS)
    ])

    st.markdown(f"""
    <div class="qa-hero">
      <div class="hero-inner">
        <div class="hero-left">
          <div class="hero-tag">
            <span class="tag-dot"></span>
            6-Agent AI Pipeline
          </div>
          <h1 class="hero-title">
            Most AI tools<br>generate test cases.<br>
            <span class="violet">This one thinks<br>like your entire QA team.</span>
          </h1>
          <p class="hero-desc">
            6 specialist agents analyse your requirement, assess risk, design strategy,
            write test cases, check coverage, and produce a complete QA plan —
            with automatic correction loops at every step.
          </p>
          <div class="stat-strip">
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
              <div class="stat-lbl">Avg Time</div>
            </div>
            <div class="stat-item">
              <div class="stat-num">$0.05</div>
              <div class="stat-lbl">Per Run</div>
            </div>
          </div>
          <div class="usage-wrap">
            {pips}
            <span class="u-txt">{runs_rem} free run{"s" if runs_rem != 1 else ""} remaining</span>
          </div>
        </div>

        <div class="hero-right" style="padding-top:0.5rem">
          <!-- input rendered by Streamlit below -->
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Input column layout
    col_left, col_right = st.columns([3, 1.2])

    with col_left:
        with st.expander("\u25b6  Load an example requirement"):
            examples = {
                "User Login with Lockout": "User login with email and password. After 3 consecutive failed login attempts the account locks for 15 minutes. Users can reset their password via email. The reset link expires after 24 hours. Passwords must be at least 8 characters with one uppercase and one number.",
                "SOP Acknowledgement": "Workspace Admins can mark any published SOP as requiring acknowledgement. Users who open a flagged SOP see an Acknowledge button. Clicking opens a confirmation popup with SOP name and version. User must tick a checkbox and click Confirm. Acknowledgement is recorded with timestamp. Users can only acknowledge once per version. If SOP is updated, all users must re-acknowledge.",
                "File Upload": "File upload accepting PDF and DOCX up to 10MB. Files scanned for malware before saving. Email confirmation sent on success. Files stored 30 days then auto-deleted unless marked permanent. Authenticated users only.",
            }
            sel = st.selectbox("Example:", ["Select..."] + list(examples.keys()),
                              label_visibility="collapsed")
            if sel and sel != "Select...":
                if st.button("Load this example"):
                    st.session_state["ex_req"] = examples[sel]
                    st.rerun()

        requirement = st.text_area(
            "req",
            value=st.session_state.get("ex_req", ""),
            height=200,
            placeholder="Describe the feature you want to test...\n\nThe more specific you are, the better the QA plan.",
            label_visibility="collapsed"
        )

        char_c = len(requirement.strip())
        if char_c > 0:
            if char_c < 100:
                st.caption(f"\u26a0\ufe0f {char_c} characters — add more detail for better results")
            else:
                st.caption(f"\u2713 {char_c} characters")

        st.file_uploader(
            "Existing test suite CSV — optional, enables coverage gap analysis",
            type=["csv"],
            key="csv_upload"
        )

        uploaded = st.session_state.get("csv_upload")
        suite_path = None
        if uploaded:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                suite_path = tmp.name
            st.session_state["suite_path"] = suite_path

        if "suite_path" in st.session_state and not uploaded:
            suite_path = st.session_state.get("suite_path")

        run_btn = st.button(
            "\u26a1  Run QA Workflow",
            disabled=st.session_state.workflow_running or not requirement.strip(),
            type="primary",
            use_container_width=True
        )

    with col_right:
        st.markdown("""
        <div class="what-card">
          <div class="what-title">What you get</div>
          <div class="what-row"><span class="what-arr">\u2192</span>Requirements gap analysis</div>
          <div class="what-row"><span class="what-arr">\u2192</span>Risk matrix with scores</div>
          <div class="what-row"><span class="what-arr">\u2192</span>Test strategy document</div>
          <div class="what-row"><span class="what-arr">\u2192</span>20+ structured test cases</div>
          <div class="what-row"><span class="what-arr">\u2192</span>Coverage gap report</div>
          <div class="what-row"><span class="what-arr">\u2192</span>Go / No-Go recommendation</div>
          <div class="what-row"><span class="what-arr">\u2192</span>Downloadable HTML report</div>
          <div class="what-meta">
            time &nbsp;&nbsp;&nbsp;90–120s<br>
            cost &nbsp;&nbsp;&nbsp;$0.03–0.10<br>
            agents &nbsp;4–6
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Pipeline (idle state)
    pipeline_ph.markdown(render_pipeline(st.session_state.agent_statuses), unsafe_allow_html=True)

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
                    upd(statuses, int(i * 20))
                    status_ph.caption(f"Agent {i+1}/4: {name}...")

                result = run_workflow(requirement=requirement, existing_test_suite_path=suite_path)

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

                    upd(statuses, 100)
                    status_ph.success("\u2713 Complete — review your outputs below")

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

    pipeline_ph.markdown(render_pipeline(st.session_state.agent_statuses), unsafe_allow_html=True)

    result = st.session_state.current_result
    outputs = result.get("outputs", {})
    conf = result.get("confidence", {})
    sid = result.get("session_id", "")
    cs = conf.get("score", 0)
    cost = result.get("workflow_state", {}).get("total_cost_usd", 0)

    st.markdown(f"""
    <div class="review-header">
      <div class="review-eyebrow">Human Review Gate</div>
      <div class="review-title">Review agent outputs before generating your report</div>
      <div class="review-meta">
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

    t1,t2,t3,t4,t5 = st.tabs(["Requirements","Risk","Strategy","Test Cases","Coverage"])

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
            ca,cb = st.columns(2)
            with ca:
                st.markdown("**Manual**")
                for t in r.get("manual_tests",[]): st.markdown(f"• {t}")
            with cb:
                st.markdown("**Automate**")
                for t in r.get("automated_tests",[]): st.markdown(f"• {t}")

    with t4:
        tc = outputs.get("test_cases", {})
        tcs = tc.get("test_cases",[])
        if tcs:
            c1,c2,c3 = st.columns(3)
            c1.metric("Total", len(tcs))
            c2.metric("Complexity", tc.get("complexity_level","?").replace("_"," ").title())
            c3.metric("Batches", tc.get("batch_count","?"))
            st.info(tc.get("coverage_summary",""))
            df = pd.DataFrame([{
                "ID": x.get("tc_id",""), "Category": x.get("category",""),
                "Title": x.get("title",""), "Priority": x.get("priority",""),
                "Type": x.get("test_type","")
            } for x in tcs])
            st.dataframe(df, use_container_width=True)
            st.download_button("\u2193 Download CSV", df.to_csv(index=False),
                             f"test_cases_{sid}.csv", "text/csv",
                             use_container_width=True)

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

    ca,cb = st.columns(2)
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

    pipeline_ph.markdown(render_pipeline(st.session_state.agent_statuses), unsafe_allow_html=True)

    fr = st.session_state.final_report
    result = st.session_state.current_result or {}
    sid = result.get("session_id","")
    outputs = result.get("outputs",{})
    rec = fr.get("go_no_go_recommendation","GO")

    if rec == "GO":
        rc,rb,ri = "#10b981","rgba(16,185,129,0.08)","\u2713"
        rb_border = "rgba(16,185,129,0.2)"
    elif rec == "CONDITIONAL GO":
        rc,rb,ri = "#f59e0b","rgba(245,158,11,0.06)","\u26a0"
        rb_border = "rgba(245,158,11,0.2)"
    else:
        rc,rb,ri = "#ef4444","rgba(239,68,68,0.06)","\u00d7"
        rb_border = "rgba(239,68,68,0.2)"

    st.markdown(f"""
    <div style="background:{rb};border:1px solid {rb_border};border-radius:12px;
                padding:2rem;margin:2rem 3rem 1rem;text-align:center">
      <div style="font-size:2.5rem;margin-bottom:0.3rem">{ri}</div>
      <div style="font-size:2rem;font-weight:900;color:{rc};letter-spacing:-0.04em">{rec}</div>
      <div style="font-size:0.88rem;color:#475569;margin-top:0.5rem;max-width:500px;
                  margin-left:auto;margin-right:auto;line-height:1.6">
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
        for i,s in enumerate(fr["next_steps"],1):
            st.markdown(f"{i}. {s}")

    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.session_state.html_report:
            st.download_button("\u2193  Download HTML Report",
                             data=st.session_state.html_report,
                             file_name=f"qa_plan_{sid}.html", mime="text/html",
                             use_container_width=True, type="primary")
    with c2:
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
    with c3:
        if st.button("\u2190  New Analysis", use_container_width=True):
            for k in ["current_result","final_report","html_report","show_review_gate",
                      "reviewer_notes","agent_statuses","suite_path","ex_req"]:
                st.session_state.pop(k, None)
            init_session_state()
            st.rerun()

    st.markdown("""
    <div style="text-align:center;padding:2.5rem 0 1.5rem;
                font-size:0.68rem;color:#1e1e35;
                font-family:JetBrains Mono,monospace;letter-spacing:0.05em">
      built by thilangi uththara de silva &nbsp;·&nbsp;
      <a href="https://github.com/thila98/qa-workflow-orchestrator"
         style="color:#7c3aed;text-decoration:none">github</a>
      &nbsp;·&nbsp;
      <a href="https://linkedin.com/in/thilangi-de-silva-66bb0b190/"
         style="color:#7c3aed;text-decoration:none">linkedin</a>
    </div>
    """, unsafe_allow_html=True)
