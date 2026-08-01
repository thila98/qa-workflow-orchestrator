"""
Report Generator
----------------
Converts the final QA plan report from Agent 6
into a downloadable HTML file.

The HTML report is the deliverable that gets shared with
developers, product managers, and stakeholders.
It is self-contained - one file, no dependencies,
opens in any browser.

Design principles:
- Professional and clean - looks like a real QA document
- Readable on screen and when printed
- Colour coded by risk level and go/no-go status
- Includes all agent outputs in organised sections
- Shows confidence scores transparently
"""

import json
import os
from datetime import datetime


def generate_html_report(
    requirement: str,
    all_outputs: dict,
    final_report: dict,
    confidence: dict,
    workflow_state_data: dict,
    session_id: str
) -> str:
    """
    Generates a complete HTML report from all workflow outputs.

    Args:
        requirement: Original requirement text
        all_outputs: All agent outputs
        final_report: Output from Agent 6 (Report Writer)
        confidence: Confidence score data
        workflow_state_data: Workflow metadata
        session_id: Unique session identifier

    Returns:
        HTML string ready to save as a file
    """

    # Determine colours based on go/no-go recommendation
    recommendation = final_report.get("go_no_go_recommendation", "GO")
    if recommendation == "GO":
        rec_color = "#22c55e"
        rec_bg = "#f0fdf4"
    elif recommendation == "CONDITIONAL GO":
        rec_color = "#f59e0b"
        rec_bg = "#fffbeb"
    else:
        rec_color = "#ef4444"
        rec_bg = "#fef2f2"

    # Confidence colour
    conf_score = confidence.get("score", 0)
    if conf_score >= 0.85:
        conf_color = "#22c55e"
    elif conf_score >= 0.70:
        conf_color = "#f59e0b"
    else:
        conf_color = "#ef4444"

    # Format test cases table
    test_cases = all_outputs.get("test_cases", {}).get("test_cases", [])
    tc_rows = ""
    for tc in test_cases:
        priority = tc.get("priority", "Medium")
        priority_color = (
            "#ef4444" if priority == "High"
            else "#f59e0b" if priority == "Medium"
            else "#22c55e"
        )
        tc_rows += f"""
        <tr>
            <td style="font-weight:600;color:#6b7280">{tc.get("tc_id","")}</td>
            <td><span style="background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:12px;font-size:0.8rem">{tc.get("category","")}</span></td>
            <td>{tc.get("title","")}</td>
            <td><span style="color:{priority_color};font-weight:600">{priority}</span></td>
            <td style="color:#6b7280;font-size:0.85rem">{tc.get("test_type","Manual")}</td>
        </tr>"""

    # Format key risks
    risks_html = ""
    for risk in final_report.get("key_risks", []):
        level = risk.get("level", "Medium")
        risk_color = (
            "#ef4444" if level in ["Critical", "High"]
            else "#f59e0b" if level == "Medium"
            else "#22c55e"
        )
        risks_html += f"""
        <div style="border-left:4px solid {risk_color};padding:12px 16px;margin:8px 0;background:#f9fafb;border-radius:0 8px 8px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <strong>{risk.get("risk","")}</strong>
                <span style="color:{risk_color};font-weight:600;font-size:0.85rem">{level}</span>
            </div>
            <p style="margin:4px 0 0;color:#6b7280;font-size:0.9rem">{risk.get("mitigation","")}</p>
        </div>"""

    # Format action items
    actions_html = ""
    for i, action in enumerate(final_report.get("action_items", []), 1):
        priority = action.get("priority", "Medium")
        priority_color = (
            "#ef4444" if priority == "High"
            else "#f59e0b" if priority == "Medium"
            else "#22c55e"
        )
        actions_html += f"""
        <tr>
            <td style="color:#6b7280;font-size:0.85rem">{i}</td>
            <td>{action.get("action","")}</td>
            <td style="color:#6b7280">{action.get("owner","")}</td>
            <td><span style="color:{priority_color};font-weight:600">{priority}</span></td>
        </tr>"""

    # Format confidence flags
    flags_html = ""
    for flag in confidence.get("flags", []):
        flag_color = "#ef4444" if "CRITICAL" in flag or "HALLUCINATION" in flag else "#f59e0b"
        flags_html += f'<li style="color:{flag_color};margin:4px 0">{flag}</li>'

    if not flags_html:
        flags_html = '<li style="color:#22c55e">No issues flagged by the AI validation system</li>'

    # Format entry/exit criteria
    def format_criteria(items):
        return "".join([
            f'<li style="margin:4px 0;padding:4px 0;border-bottom:1px solid #f3f4f6">{item}</li>'
            for item in items
        ])

    # Test suite summary
    suite_summary = final_report.get("test_suite_summary", {})
    by_category = suite_summary.get("by_category", {})
    category_bars = ""
    total = suite_summary.get("total_test_cases", len(test_cases)) or 1
    for cat, count in by_category.items():
        pct = int((count / total) * 100)
        category_bars += f"""
        <div style="margin:6px 0">
            <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:2px">
                <span>{cat}</span><span style="font-weight:600">{count}</span>
            </div>
            <div style="background:#e5e7eb;border-radius:4px;height:8px">
                <div style="background:#3b82f6;width:{pct}%;height:8px;border-radius:4px"></div>
            </div>
        </div>"""

    generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QA Plan Report - Session {session_id}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:#1f2937; background:#f9fafb; line-height:1.6; }}
  .container {{ max-width:1100px; margin:0 auto; padding:24px; }}
  .header {{ background:linear-gradient(135deg,#1e40af,#3b82f6); color:white; padding:32px; border-radius:12px; margin-bottom:24px; }}
  .header h1 {{ font-size:1.8rem; margin-bottom:8px; }}
  .header p {{ opacity:0.85; font-size:0.95rem; }}
  .card {{ background:white; border-radius:12px; padding:24px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .card h2 {{ font-size:1.1rem; color:#1e40af; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #e0f2fe; }}
  .badge {{ display:inline-block; padding:4px 12px; border-radius:20px; font-size:0.8rem; font-weight:600; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.9rem; }}
  th {{ background:#f3f4f6; padding:10px 12px; text-align:left; font-weight:600; color:#6b7280; font-size:0.8rem; text-transform:uppercase; }}
  td {{ padding:10px 12px; border-bottom:1px solid #f3f4f6; }}
  tr:last-child td {{ border-bottom:none; }}
  .metric {{ text-align:center; padding:16px; background:#f9fafb; border-radius:8px; }}
  .metric .value {{ font-size:2rem; font-weight:700; color:#1e40af; }}
  .metric .label {{ font-size:0.8rem; color:#6b7280; margin-top:4px; }}
  ul {{ padding-left:20px; }}
  li {{ margin:4px 0; }}
  @media print {{
    body {{ background:white; }}
    .container {{ padding:0; }}
  }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <h1>QA Plan Report</h1>
    <p>Session {session_id} &nbsp;|&nbsp; Generated {generated_at} &nbsp;|&nbsp; AI Confidence: <strong>{conf_score:.0%}</strong></p>
  </div>

  <!-- Go/No-Go Banner -->
  <div style="background:{rec_bg};border:2px solid {rec_color};border-radius:12px;padding:20px 24px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between">
    <div>
      <div style="font-size:0.8rem;color:#6b7280;text-transform:uppercase;font-weight:600;margin-bottom:4px">Testing Recommendation</div>
      <div style="font-size:1.8rem;font-weight:700;color:{rec_color}">{recommendation}</div>
      <div style="color:#374151;margin-top:4px;font-size:0.95rem">{final_report.get("go_no_go_reasoning","")}</div>
    </div>
    <div style="font-size:3rem">{
      "✅" if recommendation == "GO"
      else "⚠️" if recommendation == "CONDITIONAL GO"
      else "🚫"
    }</div>
  </div>

  <!-- Metrics Row -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px">
    <div class="metric">
      <div class="value">{suite_summary.get("total_test_cases", len(test_cases))}</div>
      <div class="label">Test Cases</div>
    </div>
    <div class="metric">
      <div class="value" style="color:{
        "#ef4444" if final_report.get("test_suite_summary",{{}}).get("total_test_cases",0) and
        suite_summary.get("high_priority_count",0) else "#1e40af"
      }">{suite_summary.get("high_priority_count","N/A")}</div>
      <div class="label">High Priority</div>
    </div>
    <div class="metric">
      <div class="value">{suite_summary.get("automation_candidates","N/A")}</div>
      <div class="label">Auto Candidates</div>
    </div>
    <div class="metric">
      <div class="value" style="color:{conf_color}">{conf_score:.0%}</div>
      <div class="label">AI Confidence</div>
    </div>
  </div>

  <!-- Executive Summary -->
  <div class="card">
    <h2>Executive Summary</h2>
    <p style="color:#374151;line-height:1.8">{final_report.get("executive_summary","").replace(chr(10),"<br>")}</p>
  </div>

  <!-- Requirement -->
  <div class="card">
    <h2>Requirement</h2>
    <div style="background:#f9fafb;border-left:4px solid #3b82f6;padding:16px;border-radius:0 8px 8px 0;font-size:0.95rem;color:#374151">
      {requirement}
    </div>
    <div style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap">
      <span>Quality Score: <strong>{all_outputs.get("requirements_analysis",{{}}).get("quality_score","N/A")}/10</strong></span>
      <span>|</span>
      <span>Risk Level: <strong style="color:{
        "#ef4444" if all_outputs.get("risk_assessment",{{}}).get("overall_risk_level") in ["High","Critical"]
        else "#f59e0b" if all_outputs.get("risk_assessment",{{}}).get("overall_risk_level") == "Medium"
        else "#22c55e"
      }">{all_outputs.get("risk_assessment",{{}}).get("overall_risk_level","Unknown")}</strong></span>
    </div>
  </div>

  <!-- Two column: Risks and Test Coverage -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">

    <div class="card" style="margin-bottom:0">
      <h2>Key Risks</h2>
      {risks_html if risks_html else "<p style='color:#6b7280'>No critical risks identified.</p>"}
    </div>

    <div class="card" style="margin-bottom:0">
      <h2>Test Coverage by Category</h2>
      {category_bars if category_bars else "<p style='color:#6b7280'>Category breakdown not available.</p>"}
    </div>

  </div>

  <!-- Entry and Exit Criteria -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
    <div class="card" style="margin-bottom:0">
      <h2>Entry Criteria</h2>
      <ul style="color:#374151">
        {format_criteria(final_report.get("entry_criteria",[]))}
      </ul>
    </div>
    <div class="card" style="margin-bottom:0">
      <h2>Exit Criteria</h2>
      <ul style="color:#374151">
        {format_criteria(final_report.get("exit_criteria",[]))}
      </ul>
    </div>
  </div>

  <!-- Test Cases Table -->
  <div class="card">
    <h2>Generated Test Cases ({len(test_cases)} total)</h2>
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Category</th>
            <th>Title</th>
            <th>Priority</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          {tc_rows}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Action Items -->
  <div class="card">
    <h2>Action Items</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Action</th>
          <th>Owner</th>
          <th>Priority</th>
        </tr>
      </thead>
      <tbody>
        {actions_html}
      </tbody>
    </table>
  </div>

  <!-- AI Validation -->
  <div class="card">
    <h2>AI Validation Summary</h2>
    <div style="background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:12px">
      <div style="font-weight:600;margin-bottom:4px">Confidence Grade: {confidence.get("grade","N/A")} ({conf_score:.0%})</div>
      <div style="color:#6b7280;font-size:0.9rem">{confidence.get("recommendation","")}</div>
    </div>
    <div>
      <div style="font-weight:600;margin-bottom:8px;font-size:0.9rem">Validation Flags:</div>
      <ul style="list-style:none;padding:0">
        {flags_html}
      </ul>
    </div>
  </div>

  <!-- Next Steps -->
  <div class="card">
    <h2>Next Steps</h2>
    <ol style="color:#374151;padding-left:20px">
      {"".join([f"<li style='margin:8px 0'>{step}</li>" for step in final_report.get("next_steps",[])])}
    </ol>
  </div>

  <!-- Footer -->
  <div style="text-align:center;color:#9ca3af;font-size:0.8rem;padding:24px 0">
    Generated by QA Workflow Orchestrator &nbsp;|&nbsp;
    Session {session_id} &nbsp;|&nbsp;
    {generated_at} &nbsp;|&nbsp;
    <a href="https://github.com/thila98/qa-workflow-orchestrator" style="color:#3b82f6">GitHub</a>
  </div>

</div>
</body>
</html>"""

    return html


def save_report(html: str, session_id: str, output_dir: str = "reports") -> str:
    """
    Saves the HTML report to the reports directory.

    Args:
        html: The HTML string to save
        session_id: Session ID for the filename
        output_dir: Directory to save reports in

    Returns:
        Path to the saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"qa_plan_{session_id}_{timestamp}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def save_session_json(data: dict, session_id: str, output_dir: str = "reports") -> str:
    """
    Saves the complete session data as JSON for replay and history.

    Args:
        data: Complete workflow output dictionary
        session_id: Session ID for the filename
        output_dir: Directory to save session data in

    Returns:
        Path to the saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{session_id}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath
