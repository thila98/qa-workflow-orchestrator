"""
QA Workflow Orchestrator - Streamlit Dashboard
-----------------------------------------------
The main user interface for the QA Workflow Orchestrator.

This dashboard allows QA engineers to:
1. Paste or type a software requirement
2. Optionally upload an existing test suite CSV
3. Run the full AI agent workflow
4. Review each agent output with confidence scores
5. Add notes and corrections (human review gate)
6. Generate and download the final QA plan report

Usage counter:
- Each user gets 5 free workflow runs
- Tracked in browser session state
- After 5 runs a friendly paywall screen is shown
- Users can self-host for unlimited runs (link to GitHub)
"""

import streamlit as st
import json
import os
import tempfile
from datetime import datetime

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="QA Workflow Orchestrator",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# Constants
# ─────────────────────────────────────────

MAX_FREE_RUNS = 5
PRIMARY_COLOR = "#3b82f6"
SUCCESS_COLOR = "#22c55e"
WARNING_COLOR = "#f59e0b"
DANGER_COLOR = "#ef4444"

# ─────────────────────────────────────────
# Session State Initialisation
# ─────────────────────────────────────────

def init_session_state():
    """Initialise all session state variables on first load."""
    defaults = {
        "runs_used": 0,
        "current_result": None,
        "final_report": None,
        "html_report": None,
        "workflow_running": False,
        "show_review_gate": False,
        "reviewer_notes": "",
        "approved": False,
        "active_tab": "input",
        "error_message": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ─────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────

st.markdown("""
<style>
    /* Main container */
    .main .block-container { padding-top: 2rem; max-width: 1200px; }

    /* Hide Streamlit default elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Agent status cards */
    .agent-card {
        background: white;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    .agent-running {
        border-left: 4px solid #3b82f6;
        animation: pulse 2s infinite;
    }

    .agent-done {
        border-left: 4px solid #22c55e;
    }

    .agent-failed {
        border-left: 4px solid #ef4444;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    /* Go/No-Go banner */
    .go-banner {
        padding: 20px 24px;
        border-radius: 10px;
        margin: 16px 0;
        font-size: 1.4rem;
        font-weight: 700;
        text-align: center;
    }

    /* Usage counter */
    .usage-counter {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 0.9rem;
    }

    /* Confidence badge */
    .confidence-high { color: #22c55e; font-weight: 700; }
    .confidence-medium { color: #f59e0b; font-weight: 700; }
    .confidence-low { color: #ef4444; font-weight: 700; }

    /* Section headers */
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1e40af;
        padding-bottom: 8px;
        border-bottom: 2px solid #e0f2fe;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Header
# ─────────────────────────────────────────

col_title, col_runs = st.columns([3, 1])

with col_title:
    st.markdown("# 🧪 QA Workflow Orchestrator")
    st.markdown("*AI-powered QA planning — from requirement to complete test strategy*")

with col_runs:
    runs_remaining = MAX_FREE_RUNS - st.session_state.runs_used
    if runs_remaining > 1:
        runs_color = SUCCESS_COLOR
        runs_emoji = "✅"
    elif runs_remaining == 1:
        runs_color = WARNING_COLOR
        runs_emoji = "⚠️"
    else:
        runs_color = DANGER_COLOR
        runs_emoji = "🚫"

    st.markdown(f"""
    <div class="usage-counter">
        {runs_emoji} <strong>{runs_remaining} free run{'s' if runs_remaining != 1 else ''} remaining</strong><br>
        <span style="color:#6b7280;font-size:0.8rem">5 runs free · Self-host for unlimited</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────
# Paywall Screen
# ─────────────────────────────────────────

if st.session_state.runs_used >= MAX_FREE_RUNS:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
        <div style="font-size:4rem;margin-bottom:16px">🔒</div>
        <h2 style="color:#1e40af;margin-bottom:8px">You have used your 5 free runs</h2>
        <p style="color:#6b7280;font-size:1rem;max-width:500px;margin:0 auto 32px">
            Thank you for trying QA Workflow Orchestrator!
            This is an open source project — you can self-host it for unlimited runs.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.link_button(
            "⭐ View Source on GitHub",
            "https://github.com/thila98/qa-workflow-orchestrator",
            use_container_width=True
        )
        st.link_button(
            "🔗 Connect on LinkedIn",
            "https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/",
            use_container_width=True
        )
        st.markdown("""
        <div style="text-align:center;margin-top:24px;color:#6b7280;font-size:0.85rem">
            Built by Thilangi Uththara De Silva · Senior QA Engineer
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    st.markdown("**About this tool**")
    st.markdown("""
    This tool uses 6 specialised AI agents to transform
    a software requirement into a complete QA strategy:

    1. 📋 Requirements Analyst
    2. ⚠️ Risk Assessor
    3. 🗺️ Test Strategist
    4. ✍️ Test Case Writer
    5. 🔍 Coverage Analyser *(optional)*
    6. 📄 Report Writer

    A **Judge Agent** validates every output before
    it passes to the next agent — preventing
    hallucination propagation.
    """)

    st.divider()

    st.markdown("**Safety Controls**")
    st.info(
        "Max API cost per run: $0.50\n\n"
        "Max retries per agent: 3\n\n"
        "Agent timeout: 60 seconds"
    )

    st.divider()

    st.markdown("**Resources**")
    st.markdown("[📁 GitHub Repository](https://github.com/thila98/qa-workflow-orchestrator)")
    st.markdown("[🔗 LinkedIn](https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/)")
    st.markdown("[📚 Knowledge Base](https://thila98.github.io/qa-knowledge-base)")

# ─────────────────────────────────────────
# Main Content - Input Tab
# ─────────────────────────────────────────

if not st.session_state.show_review_gate and not st.session_state.final_report:

    st.markdown("### 📝 Enter Your Requirement")

    # Example requirements
    with st.expander("💡 See example requirements"):
        examples = {
            "User Login with Lockout": """User login with email and password.
After 3 consecutive failed login attempts the account locks for 15 minutes.
Users can reset their password via email.
The reset link expires after 24 hours.
Passwords must be at least 8 characters with one uppercase letter and one number.""",

            "File Upload Feature": """File upload feature that accepts PDF and DOCX files up to 10MB.
Files are scanned for malware before being saved.
Users receive an email confirmation when upload is complete.
Files are stored for 30 days then automatically deleted unless marked as permanent.
Only authenticated users can upload files.""",

            "Password Reset Flow": """Password reset flow via email.
User enters their email address on the forgot password page.
System sends a reset link that expires after 24 hours.
Link can only be used once.
After reset, all other active sessions are logged out.
New password cannot be the same as the last 3 passwords."""
        }

        selected = st.selectbox("Load an example:", ["Select..."] + list(examples.keys()))
        if selected and selected != "Select...":
            if st.button("Use this example"):
                st.session_state["example_requirement"] = examples[selected]
                st.rerun()

    # Requirement text area
    default_req = st.session_state.get("example_requirement", "")
    requirement = st.text_area(
        "Requirement or User Story",
        value=default_req,
        height=180,
        placeholder="Describe the feature you want to test...",
        help="The more detail you provide, the better the test cases will be."
    )

    # Character counter
    char_count = len(requirement.strip())
    if char_count > 0:
        if char_count < 50:
            st.caption(f"⚠️ {char_count} characters — more detail recommended")
        elif char_count < 200:
            st.caption(f"✅ {char_count} characters — good, more detail helps")
        else:
            st.caption(f"✅ {char_count} characters — great detail")

    st.markdown("### 📎 Existing Test Suite *(optional)*")
    uploaded_file = st.file_uploader(
        "Upload your current test suite CSV for coverage gap analysis",
        type=["csv"],
        help="If you upload an existing test suite, Agent 5 will compare new test cases against it and identify gaps and duplicates."
    )

    existing_suite_path = None
    if uploaded_file:
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False
        ) as tmp:
            tmp.write(uploaded_file.getvalue())
            existing_suite_path = tmp.name
        st.success(f"✅ Uploaded: {uploaded_file.name}")
        st.session_state["temp_suite_path"] = existing_suite_path

    # Store suite path in session
    if "temp_suite_path" in st.session_state and not uploaded_file:
        # File was uploaded in a previous interaction
        existing_suite_path = st.session_state.get("temp_suite_path")

    st.divider()

    # Run button
    col_run, col_info = st.columns([2, 3])

    with col_run:
        run_disabled = st.session_state.workflow_running or not requirement.strip()
        run_button = st.button(
            "🚀 Run QA Workflow",
            disabled=run_disabled,
            use_container_width=True,
            type="primary"
        )

    with col_info:
        st.markdown("""
        <div style="padding:8px 0;color:#6b7280;font-size:0.85rem">
            Estimated time: 60-90 seconds<br>
            Estimated cost: $0.02 - $0.05<br>
            Agents: 4-6 (depending on options)
        </div>
        """, unsafe_allow_html=True)

    # ── Run the workflow ───────────────────────────────────────────────

    if run_button and requirement.strip():
        st.session_state.workflow_running = True
        st.session_state.error_message = None

        # Import here to avoid circular imports
        from validation.input_validator import validate_input

        # Quick input validation before starting
        input_check = validate_input(requirement)
        if not input_check.is_valid:
            st.error(f"❌ {input_check.error_message}")
            st.session_state.workflow_running = False
            st.stop()

        # Show progress
        st.markdown("---")
        st.markdown("### 🔄 Running Agents...")

        progress_container = st.container()

        with progress_container:
            agent_statuses = {
                "Requirements Analyst": "⏳ Waiting",
                "Risk Assessor": "⏳ Waiting",
                "Test Strategist": "⏳ Waiting",
                "Test Case Writer": "⏳ Waiting",
                "Coverage Analyser": "⏳ Waiting" if existing_suite_path else "⏭️ Skipped",
                "Judge Agent": "🔍 Running after each agent",
                "Report Writer": "⏳ After your review"
            }

            status_placeholder = st.empty()

            def update_status(agent_name, status):
                agent_statuses[agent_name] = status
                status_md = ""
                for name, stat in agent_statuses.items():
                    if "✅" in stat:
                        icon = "🟢"
                    elif "Running" in stat or "⏳" == stat[:2]:
                        icon = "🔵"
                    elif "❌" in stat:
                        icon = "🔴"
                    elif "⏭️" in stat:
                        icon = "⚪"
                    else:
                        icon = "⚫"
                    status_md += f"{icon} **{name}**: {stat}\n\n"
                status_placeholder.markdown(status_md)

            update_status("Requirements Analyst", "✅ Done")

            try:
                from main import run_workflow

                # Update statuses as we go
                update_status("Requirements Analyst", "🔵 Running...")

                result = run_workflow(
                    requirement=requirement,
                    existing_test_suite_path=existing_suite_path
                )

                if result.get("status") == "error":
                    st.error(f"❌ {result.get('message', 'Unknown error')}")
                    st.session_state.workflow_running = False
                else:
                    # Update all to done
                    for agent in ["Requirements Analyst", "Risk Assessor",
                                  "Test Strategist", "Test Case Writer"]:
                        update_status(agent, "✅ Done")

                    if existing_suite_path:
                        update_status("Coverage Analyser", "✅ Done")

                    # Increment usage counter
                    st.session_state.runs_used += 1

                    # Store result and show review gate
                    st.session_state.current_result = result
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

    st.markdown(f"### 🔍 Human Review Gate — Session {session_id}")

    # Confidence banner
    conf_score = confidence.get("score", 0)
    conf_grade = confidence.get("grade", "?")
    if conf_score >= 0.85:
        conf_bg = "#f0fdf4"
        conf_border = "#22c55e"
        conf_label = "High Confidence"
    elif conf_score >= 0.70:
        conf_bg = "#fffbeb"
        conf_border = "#f59e0b"
        conf_label = "Medium Confidence"
    else:
        conf_bg = "#fef2f2"
        conf_border = "#ef4444"
        conf_label = "Low Confidence — Review Carefully"

    st.markdown(f"""
    <div style="background:{conf_bg};border:2px solid {conf_border};border-radius:10px;
                padding:16px 20px;margin-bottom:20px">
        <strong>AI Confidence: {conf_score:.0%} (Grade {conf_grade}) — {conf_label}</strong><br>
        <span style="color:#6b7280;font-size:0.9rem">{confidence.get("recommendation","")}</span>
    </div>
    """, unsafe_allow_html=True)

    # Show confidence flags if any
    flags = confidence.get("flags", [])
    if flags:
        with st.expander(f"⚠️ {len(flags)} validation flag(s) detected"):
            for flag in flags:
                if "CRITICAL" in flag or "HALLUCINATION" in flag:
                    st.error(flag)
                else:
                    st.warning(flag)

    # Agent outputs in tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Requirements",
        "⚠️ Risk Assessment",
        "🗺️ Test Strategy",
        "✍️ Test Cases",
        "🔍 Coverage"
    ])

    with tab1:
        req_analysis = outputs.get("requirements_analysis", {})
        if req_analysis:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Quality Score", f"{req_analysis.get('quality_score', 'N/A')}/10")
                st.metric("Is Testable", "Yes" if req_analysis.get("is_testable") else "No")
            with col2:
                st.metric("Gaps Found", len(req_analysis.get("gaps", [])))
                st.metric("Needs Clarification", "Yes" if req_analysis.get("needs_clarification") else "No")

            st.markdown("**Summary:**")
            st.info(req_analysis.get("summary", "Not available"))

            if req_analysis.get("gaps"):
                st.markdown("**Gaps Identified:**")
                for gap in req_analysis.get("gaps", []):
                    st.warning(f"• {gap}")

            if req_analysis.get("ambiguities"):
                st.markdown("**Ambiguities:**")
                for amb in req_analysis.get("ambiguities", []):
                    st.warning(f"• {amb}")

    with tab2:
        risk = outputs.get("risk_assessment", {})
        if risk:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Overall Risk", risk.get("overall_risk_level", "N/A"))
            with col2:
                st.metric("Risk Areas", len(risk.get("risk_areas", [])))
            with col3:
                st.metric("Critical Risks", len(risk.get("critical_risks", [])))

            st.markdown("**Risk Summary:**")
            st.info(risk.get("risk_summary", "Not available"))

            st.markdown("**Risk Matrix:**")
            risk_areas = risk.get("risk_areas", [])
            if risk_areas:
                import pandas as pd
                risk_df = pd.DataFrame([{
                    "Risk Area": r.get("name", ""),
                    "Category": r.get("category", ""),
                    "Likelihood": r.get("likelihood", ""),
                    "Impact": r.get("impact", ""),
                    "Score": r.get("score", ""),
                    "Priority": r.get("priority_level", "")
                } for r in risk_areas])
                st.dataframe(risk_df, use_container_width=True)

    with tab3:
        strategy = outputs.get("test_strategy", {})
        if strategy:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Estimated Test Cases", strategy.get("estimated_test_cases", "N/A"))
                st.metric("Estimated Hours", strategy.get("estimated_hours", "N/A"))
            with col2:
                st.metric("Security Testing", "Required" if strategy.get("security_testing_required") else "Not Required")
                st.metric("Performance Testing", "Required" if strategy.get("performance_testing_required") else "Not Required")

            st.markdown("**Strategy Summary:**")
            st.info(strategy.get("strategy_summary", "Not available"))

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Manual Tests:**")
                for t in strategy.get("manual_tests", []):
                    st.markdown(f"• {t}")
            with col_b:
                st.markdown("**Automation Candidates:**")
                for t in strategy.get("automated_tests", []):
                    st.markdown(f"• {t}")

    with tab4:
        test_cases_data = outputs.get("test_cases", {})
        test_cases = test_cases_data.get("test_cases", [])

        if test_cases:
            st.metric("Total Test Cases", len(test_cases))
            st.markdown("**Coverage Summary:**")
            st.info(test_cases_data.get("coverage_summary", "Not available"))

            import pandas as pd
            tc_df = pd.DataFrame([{
                "ID": tc.get("tc_id", ""),
                "Category": tc.get("category", ""),
                "Title": tc.get("title", ""),
                "Priority": tc.get("priority", ""),
                "Type": tc.get("test_type", "")
            } for tc in test_cases])
            st.dataframe(tc_df, use_container_width=True)

            # Download as CSV
            csv_data = tc_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Test Cases as CSV",
                data=csv_data,
                file_name=f"test_cases_{session_id}.csv",
                mime="text/csv"
            )

    with tab5:
        coverage = outputs.get("coverage_analysis", {})
        if coverage:
            if coverage.get("skipped"):
                st.info(f"Coverage analysis skipped: {coverage.get('reason', '')}")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Coverage Estimate", coverage.get("coverage_estimate", "N/A"))
                    st.metric("New Tests Adding Value", coverage.get("new_tests_adding_value", "N/A"))
                with col2:
                    st.metric("Potential Duplicates", coverage.get("new_tests_duplicating", "N/A"))
                    st.metric("Existing Suite Size", coverage.get("existing_suite_count", "N/A"))

                st.markdown("**Coverage Summary:**")
                st.info(coverage.get("coverage_summary", "Not available"))

                if coverage.get("gaps"):
                    st.markdown("**Coverage Gaps:**")
                    for gap in coverage.get("gaps", []):
                        st.warning(f"• {gap.get('scenario', gap)}")
        else:
            st.info("No existing test suite was provided for comparison.")

    # ── Human Review Notes and Approval ───────────────────────────────

    st.divider()
    st.markdown("### ✏️ Your Review")
    st.markdown(
        "Review the agent outputs above. Add any corrections or notes below, "
        "then approve to generate the final report."
    )

    reviewer_notes = st.text_area(
        "Notes and corrections (optional)",
        value=st.session_state.reviewer_notes,
        height=100,
        placeholder="Add any corrections, missing test cases, or notes for the report writer...",
        key="review_notes_input"
    )
    st.session_state.reviewer_notes = reviewer_notes

    col_approve, col_restart = st.columns(2)

    with col_approve:
        if st.button("✅ Approve and Generate Report", type="primary", use_container_width=True):
            st.session_state.approved = True
            st.session_state.show_review_gate = False

            # Generate final report
            with st.spinner("Generating final QA plan report..."):
                try:
                    from agents.report_writer import write_report
                    from tools.report_generator import generate_html_report, save_report, save_session_json

                    final_report = write_report(
                        requirement=result.get("requirement", ""),
                        all_outputs=outputs,
                        human_reviewer_notes=reviewer_notes,
                        confidence_score=conf_score
                    )

                    # Generate HTML report
                    html = generate_html_report(
                        requirement=result.get("requirement", ""),
                        all_outputs=outputs,
                        final_report=final_report,
                        confidence=confidence,
                        workflow_state_data=result.get("workflow_state", {}),
                        session_id=session_id
                    )

                    st.session_state.final_report = final_report
                    st.session_state.html_report = html
                    st.session_state.current_result = result
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to generate report: {str(e)}")

    with col_restart:
        if st.button("🔄 Start Over", use_container_width=True):
            # Clear everything except run count
            for key in ["current_result", "final_report", "html_report",
                        "show_review_gate", "reviewer_notes", "approved",
                        "temp_suite_path", "example_requirement"]:
                if key in st.session_state:
                    del st.session_state[key]
            init_session_state()
            st.rerun()

# ─────────────────────────────────────────
# Final Report Screen
# ─────────────────────────────────────────

elif st.session_state.final_report:

    final_report = st.session_state.final_report
    result = st.session_state.current_result
    session_id = result.get("session_id", "") if result else ""

    # Go/No-Go banner
    recommendation = final_report.get("go_no_go_recommendation", "GO")
    if recommendation == "GO":
        banner_color = "#22c55e"
        banner_bg = "#f0fdf4"
        banner_icon = "✅"
    elif recommendation == "CONDITIONAL GO":
        banner_color = "#f59e0b"
        banner_bg = "#fffbeb"
        banner_icon = "⚠️"
    else:
        banner_color = "#ef4444"
        banner_bg = "#fef2f2"
        banner_icon = "🚫"

    st.markdown(f"""
    <div style="background:{banner_bg};border:2px solid {banner_color};border-radius:12px;
                padding:20px 24px;margin-bottom:20px;text-align:center">
        <div style="font-size:2.5rem">{banner_icon}</div>
        <div style="font-size:1.6rem;font-weight:700;color:{banner_color}">{recommendation}</div>
        <div style="color:#374151;margin-top:8px">{final_report.get("go_no_go_reasoning","")}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📄 QA Plan Report")

    # Executive summary
    st.markdown("**Executive Summary:**")
    st.info(final_report.get("executive_summary", "Not available"))

    # Metrics
    suite = final_report.get("test_suite_summary", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Test Cases", suite.get("total_test_cases", "N/A"))
    col2.metric("High Priority", suite.get("high_priority_count", "N/A"))
    col3.metric("Auto Candidates", suite.get("automation_candidates", "N/A"))
    col4.metric("Go/No-Go", recommendation)

    # Download buttons
    st.divider()
    st.markdown("### 📥 Download")

    col_html, col_csv, col_new = st.columns(3)

    with col_html:
        if st.session_state.html_report:
            st.download_button(
                label="📄 Download HTML Report",
                data=st.session_state.html_report,
                file_name=f"qa_plan_{session_id}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )

    with col_csv:
        # CSV of test cases
        outputs = result.get("outputs", {}) if result else {}
        test_cases = outputs.get("test_cases", {}).get("test_cases", [])
        if test_cases:
            import pandas as pd
            tc_df = pd.DataFrame([{
                "TC_ID": tc.get("tc_id", ""),
                "Category": tc.get("category", ""),
                "Title": tc.get("title", ""),
                "Precondition": tc.get("precondition", ""),
                "Steps": tc.get("steps", ""),
                "Expected Result": tc.get("expected_result", ""),
                "Priority": tc.get("priority", ""),
                "Test Type": tc.get("test_type", ""),
                "Risk Area": tc.get("risk_area", "")
            } for tc in test_cases])
            st.download_button(
                label="📊 Download Test Cases CSV",
                data=tc_df.to_csv(index=False),
                file_name=f"test_cases_{session_id}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with col_new:
        if st.button("🔄 New Analysis", use_container_width=True):
            for key in ["current_result", "final_report", "html_report",
                        "show_review_gate", "reviewer_notes", "approved",
                        "temp_suite_path", "example_requirement"]:
                if key in st.session_state:
                    del st.session_state[key]
            init_session_state()
            st.rerun()

    # Next steps
    st.markdown("### 🚀 Next Steps")
    for i, step in enumerate(final_report.get("next_steps", []), 1):
        st.markdown(f"{i}. {step}")

    # Action items
    st.markdown("### ✅ Action Items")
    action_items = final_report.get("action_items", [])
    if action_items:
        import pandas as pd
        actions_df = pd.DataFrame([{
            "Action": a.get("action", ""),
            "Owner": a.get("owner", ""),
            "Priority": a.get("priority", "")
        } for a in action_items])
        st.dataframe(actions_df, use_container_width=True)

    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#9ca3af;font-size:0.8rem'>"
        "Built by Thilangi Uththara De Silva · "
        "<a href='https://github.com/thila98/qa-workflow-orchestrator' style='color:#3b82f6'>GitHub</a> · "
        "<a href='https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/' style='color:#3b82f6'>LinkedIn</a>"
        "</div>",
        unsafe_allow_html=True
    )
