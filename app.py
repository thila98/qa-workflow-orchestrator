"""
QA Workflow Orchestrator - Streamlit App
Simple and functional. Input, run, review, download.
"""

import streamlit as st
import pandas as pd
import tempfile

st.set_page_config(
    page_title="QA Orchestrator",
    page_icon="⚡",
    layout="centered",
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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, .stApp, .stApp > div,
  div[data-testid="stAppViewContainer"],
  div[data-testid="stMain"],
  section[data-testid="stMainBlockContainer"],
  .main, .main .block-container {
    background: #0d1117 !important;
    font-family: Inter, sans-serif !important;
    color: #e6edf3 !important;
  }

  .main .block-container {
    padding: 2rem 1.5rem !important;
    max-width: 760px !important;
  }

  #MainMenu, footer, header,
  section[data-testid="stSidebar"] { display: none !important; }

  .stTextArea > div > div > textarea {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
    font-size: 0.9rem !important;
    font-family: Inter, sans-serif !important;
    line-height: 1.6 !important;
  }

  .stTextArea > div > div > textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.1) !important;
    outline: none !important;
  }

  .stTextArea > div > div > textarea::placeholder { color: #484f58 !important; }
  .stTextArea label { color: #8b949e !important; font-size: 0.8rem !important; }

  [data-testid="stFileUploader"] section {
    background: #161b22 !important;
    border: 1px dashed #30363d !important;
    border-radius: 8px !important;
  }

  [data-testid="stFileUploader"] label { color: #8b949e !important; }

  div[data-testid="stButton"] button[kind="primary"] {
    background: #7c3aed !important;
    border: none !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
  }

  div[data-testid="stButton"] button[kind="primary"]:hover {
    background: #8b5cf6 !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.4) !important;
  }

  div[data-testid="stButton"] button[kind="primary"]:disabled {
    background: #21262d !important;
    color: #484f58 !important;
  }

  div[data-testid="stButton"] button:not([kind="primary"]) {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #8b949e !important;
  }

  [data-testid="metric-container"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    padding: 0.8rem 1rem !important;
  }

  [data-testid="metric-container"] label {
    color: #484f58 !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
  }

  [data-testid="stMetricValue"] { color: #e6edf3 !important; font-weight: 700 !important; }

  .stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #21262d !important;
  }

  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #484f58 !important;
    font-size: 0.82rem !important;
  }

  .stTabs [aria-selected="true"] {
    color: #a78bfa !important;
    border-bottom: 2px solid #7c3aed !important;
  }

  [data-testid="stInfo"] {
    background: rgba(124,58,237,0.06) !important;
    border: 1px solid rgba(124,58,237,0.15) !important;
    border-radius: 8px !important;
    color: #c4b5fd !important;
  }

  [data-testid="stWarning"] {
    background: rgba(245,158,11,0.06) !important;
    border: 1px solid rgba(245,158,11,0.15) !important;
    border-radius: 8px !important;
    color: #fbbf24 !important;
  }

  .stDataFrame { border: 1px solid #21262d !important; border-radius: 8px !important; }

  [data-testid="stDownloadButton"] button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #8b949e !important;
    border-radius: 8px !important;
    width: 100% !important;
  }

  .stProgress > div { background: #21262d !important; border-radius: 2px !important; }
  .stProgress > div > div > div { background: linear-gradient(90deg, #7c3aed, #a855f7) !important; }

  .stExpander {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
  }

  details summary { color: #484f58 !important; font-size: 0.8rem !important; }

  .stSelectbox > div > div {
    background: #161b22 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
  }

  hr { border-color: #21262d !important; }
  p, .stMarkdown p { color: #8b949e !important; font-size: 0.85rem !important; }
  .stCaption p { color: #484f58 !important; font-size: 0.72rem !important; }
</style>
""", unsafe_allow_html=True)

AGENTS = [
    ("📋", "Requirements Analyst"),
    ("⚠️", "Risk Assessor"),
    ("🗺️", "Test Strategist"),
    ("✍️", "Test Case Writer"),
    ("🔍", "Coverage Analyser"),
    ("📄", "Report Writer"),
]

# Paywall
if st.session_state.runs_used >= MAX_FREE_RUNS:
    st.markdown("### 🔒 5 free runs used")
    st.markdown("QA Orchestrator is open source. Self-host it for unlimited runs.")
    st.link_button("View on GitHub",
                  "https://github.com/thila98/qa-workflow-orchestrator",
                  use_container_width=True)
    st.stop()

# Header
runs_rem = MAX_FREE_RUNS - st.session_state.runs_used
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### ⚡ QA Orchestrator")
with col2:
    st.markdown(
        f"<div style='text-align:right;padding-top:0.5rem;"
        f"font-family:JetBrains Mono,monospace;font-size:0.72rem;"
        f"color:#7c3aed'>{runs_rem} run{'s' if runs_rem != 1 else ''} free</div>",
        unsafe_allow_html=True
    )

st.caption("requirement → risk → strategy → test cases → QA plan")
st.divider()

# Input
if not st.session_state.show_review_gate and not st.session_state.final_report:

    with st.expander("Load an example requirement"):
        examples = {
            "User Login with Lockout": "User login with email and password. After 3 consecutive failed login attempts the account locks for 15 minutes. Users can reset their password via email. The reset link expires after 24 hours.",
            "SOP Acknowledgement": "Workspace Admins can mark any published SOP as requiring acknowledgement. Users who open a flagged SOP see an Acknowledge button. Clicking opens a confirmation popup. User must tick a checkbox and click Confirm. Acknowledgement recorded with timestamp. Users can only acknowledge once per version.",
            "File Upload": "File upload accepting PDF and DOCX up to 10MB. Files scanned for malware before saving. Email confirmation sent on success. Files stored 30 days then auto-deleted unless marked permanent.",
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
        placeholder="Describe the feature you want to test...",
    )

    char_c = len(requirement.strip())
    if char_c > 0:
        if char_c < 100:
            st.caption(f"⚠️ {char_c} chars — add more detail")
        else:
            st.caption(f"✓ {char_c} chars")

    uploaded = st.file_uploader(
        "Existing test suite CSV — optional, for coverage gap analysis",
        type=["csv"]
    )

    suite_path = None
    if uploaded:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as tmp:
            tmp.write(uploaded.getvalue())
            suite_path = tmp.name
        st.session_state["suite_path"] = suite_path

    if "suite_path" in st.session_state and not uploaded:
        suite_path = st.session_state.get("suite_path")

    st.markdown("")
    run_btn = st.button(
        "⚡  Run QA Workflow",
        disabled=st.session_state.workflow_running or not requirement.strip(),
        type="primary",
        use_container_width=True
    )

    if run_btn and requirement.strip():
        from validation.input_validator import validate_input
        chk = validate_input(requirement)
        if not chk.is_valid:
            st.error(f"❌ {chk.error_message}")
        else:
            st.session_state.workflow_running = True
            st.divider()
            prog = st.progress(0)
            status_ph = st.empty()
            agent_ph = st.empty()
            statuses = {name: "idle" for _, name in AGENTS}

            def show_agents(s):
                lines = []
                for emoji, name in AGENTS:
                    v = s.get(name, "idle")
                    if v == "running":   icon = "⟳"
                    elif v == "passed":  icon = "✓"
                    elif v == "warning": icon = "⚡"
                    elif v == "skipped": icon = "—"
                    else:                icon = "○"
                    lines.append(f"{icon} {emoji} {name}")
                agent_ph.code("\n".join(lines), language=None)

            show_agents(statuses)

            try:
                from main import run_workflow

                for i, (_, name) in enumerate(AGENTS[:4]):
                    statuses[name] = "running"
                    show_agents(statuses)
                    prog.progress(i * 20)
                    status_ph.caption(f"Running {name}...")

                result = run_workflow(
                    requirement=requirement,
                    existing_test_suite_path=suite_path
                )

                if result.get("status") == "error":
                    st.error(f"❌ {result.get('message','Unknown error')}")
                    st.session_state.workflow_running = False
                else:
                    jrs = result.get("judge_results", {})
                    for _, name in AGENTS[:4]:
                        rec = jrs.get(name, {}).get("recommendation", "PASS")
                        statuses[name] = "warning" if rec == "PASS_WITH_WARNINGS" else "passed"
                    statuses["Coverage Analyser"] = "passed" if suite_path else "skipped"
                    statuses["Report Writer"] = "idle"
                    show_agents(statuses)
                    prog.progress(100)
                    status_ph.success("✓ Complete — review outputs below")

                    st.session_state.runs_used += 1
                    st.session_state.current_result = result
                    st.session_state.agent_statuses = statuses
                    st.session_state.show_review_gate = True
                    st.session_state.workflow_running = False
                    st.rerun()

            except Exception as e:
                st.error(f"❌ {str(e)}")
                st.session_state.workflow_running = False

# Review Gate
elif st.session_state.show_review_gate and not st.session_state.final_report:

    result = st.session_state.current_result
    outputs = result.get("outputs", {})
    conf = result.get("confidence", {})
    sid = result.get("session_id", "")
    cs = conf.get("score", 0)
    cost = result.get("workflow_state", {}).get("total_cost_usd", 0)

    st.caption(f"session/{sid} · confidence {cs:.0%} · cost ${cost:.4f}")

    flags = conf.get("flags", [])
    if flags:
        with st.expander(f"⚠️ {len(flags)} validation flag(s)"):
            for f in flags:
                if "CRITICAL" in f or "HALLUCINATION" in f:
                    st.error(f)
                else:
                    st.warning(f)

    t1,t2,t3,t4,t5 = st.tabs([
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
                    "Risk": x.get("name",""),
                    "Category": x.get("category",""),
                    "L": x.get("likelihood",""),
                    "I": x.get("impact",""),
                    "Score": x.get("score",""),
                    "Priority": x.get("priority_level","")
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
                "ID": x.get("tc_id",""),
                "Category": x.get("category",""),
                "Title": x.get("title",""),
                "Priority": x.get("priority",""),
                "Type": x.get("test_type","")
            } for x in tcs])
            st.dataframe(df, use_container_width=True)
            st.download_button(
                "↓ Download Test Cases CSV",
                df.to_csv(index=False),
                f"test_cases_{sid}.csv",
                "text/csv",
                use_container_width=True
            )

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
    notes = st.text_area(
        "Notes for Report Writer (optional)",
        value=st.session_state.reviewer_notes,
        height=80,
        placeholder="Corrections or missing scenarios...",
        label_visibility="collapsed"
    )
    st.session_state.reviewer_notes = notes

    ca,cb = st.columns(2)
    with ca:
        if st.button("✓ Approve and Generate Report",
                    type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    from agents.report_writer import write_report
                    from tools.report_generator import generate_html_report
                    fr = write_report(
                        requirement=result.get("requirement",""),
                        all_outputs=outputs,
                        human_reviewer_notes=notes,
                        confidence_score=cs
                    )
                    html = generate_html_report(
                        requirement=result.get("requirement",""),
                        all_outputs=outputs,
                        final_report=fr,
                        confidence=conf,
                        workflow_state_data=result.get("workflow_state",{}),
                        session_id=sid
                    )
                    st.session_state.final_report = fr
                    st.session_state.html_report = html
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {str(e)}")
    with cb:
        if st.button("← Start Over", use_container_width=True):
            for k in ["current_result","final_report","html_report",
                      "show_review_gate","reviewer_notes","agent_statuses",
                      "suite_path","ex_req"]:
                st.session_state.pop(k, None)
            init_session_state()
            st.rerun()

# Final Report
elif st.session_state.final_report:

    fr = st.session_state.final_report
    result = st.session_state.current_result or {}
    sid = result.get("session_id","")
    outputs = result.get("outputs",{})
    rec = fr.get("go_no_go_recommendation","GO")

    if rec == "GO":
        rc, ri = "#10b981", "✓"
    elif rec == "CONDITIONAL GO":
        rc, ri = "#f59e0b", "⚠"
    else:
        rc, ri = "#ef4444", "✗"

    st.markdown(
        f"<div style='text-align:center;padding:1.5rem;border-radius:10px;"
        f"background:#161b22;border:1px solid #21262d;margin-bottom:1.5rem'>"
        f"<div style='font-size:2rem;font-weight:800;color:{rc}'>{ri} {rec}</div>"
        f"<div style='font-size:0.85rem;color:#64748b;margin-top:0.4rem'>"
        f"{fr.get('go_no_go_reasoning','')}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

    suite = fr.get("test_suite_summary",{})
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Test Cases", suite.get("total_test_cases","?"))
    c2.metric("High Priority", suite.get("high_priority_count","?"))
    c3.metric("Auto Candidates", suite.get("automation_candidates","?"))
    c4.metric("Confidence", f"{result.get('confidence',{}).get('score',0):.0%}")

    st.info(fr.get("executive_summary",""))

    if fr.get("next_steps"):
        st.markdown("**Next Steps**")
        for i,s in enumerate(fr["next_steps"],1):
            st.markdown(f"{i}. {s}")

    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.session_state.html_report:
            st.download_button(
                "↓ HTML Report",
                data=st.session_state.html_report,
                file_name=f"qa_plan_{sid}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
    with c2:
        tcs = outputs.get("test_cases",{}).get("test_cases",[])
        if tcs:
            df = pd.DataFrame([{
                "TC_ID": x.get("tc_id",""),
                "Category": x.get("category",""),
                "Title": x.get("title",""),
                "Precondition": x.get("precondition",""),
                "Steps": x.get("steps",""),
                "Expected Result": x.get("expected_result",""),
                "Priority": x.get("priority",""),
                "Test Type": x.get("test_type",""),
                "Risk Area": x.get("risk_area",""),
                "Req Reference": x.get("requirement_reference","")
            } for x in tcs])
            st.download_button(
                "↓ Test Cases CSV",
                data=df.to_csv(index=False),
                file_name=f"test_cases_{sid}.csv",
                mime="text/csv",
                use_container_width=True
            )
    with c3:
        if st.button("← New Analysis", use_container_width=True):
            for k in ["current_result","final_report","html_report",
                      "show_review_gate","reviewer_notes","agent_statuses",
                      "suite_path","ex_req"]:
                st.session_state.pop(k, None)
            init_session_state()
            st.rerun()
