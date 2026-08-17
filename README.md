# QA Workflow Orchestrator

> Most AI tools generate test cases. This one thinks like your entire QA team.

A production-quality multi-agent AI system that takes a software requirement and produces a complete, validated QA strategy in 90 seconds — including requirements gap analysis, risk assessment, test strategy, structured test cases, coverage analysis, and a go/no-go recommendation.

**Live demo:** https://app-workflow-orchestrator-hf6rfamvvpcpgswappti89r.streamlit.app  
**Landing page:** https://thila98.github.io/qa-orchestrator-ui  
**Built by:** [Thilangi Uththara De Silva](https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/) — Senior QA Engineer

---

## What it does

Paste a software requirement. The system runs 6 specialist AI agents in sequence, each validated by a Judge Agent before passing to the next. You review the outputs at a mandatory human gate, then approve to generate a downloadable QA plan.

Requirement → Agent 1 → Judge → Agent 2 → Judge → Agent 3 → Judge
→ Agent 4 → Judge → Agent 5 → Human Review Gate → Agent 6 → Report


**Output includes:**
- Requirements gap analysis with quality score
- Risk matrix with Likelihood × Impact scoring
- Test strategy with manual vs automation split
- 20+ structured test cases across all categories
- Coverage gap analysis (if existing test suite uploaded)
- Go / No-Go recommendation with reasoning
- Downloadable HTML report + CSV test cases

---

## The 6 Agents

| Agent | Role | Human equivalent |
|-------|------|-----------------|
| Requirements Analyst | Finds gaps, ambiguities, quality issues | BA at sprint kickoff |
| Risk Assessor | Scores risks using Likelihood × Impact | QA Lead + Tech Lead |
| Test Strategist | Decides what to test and how | Test Architect |
| Test Case Writer | Writes all test cases across all categories | Senior QA Engineer |
| Coverage Analyser | Compares against existing test suite | QA Lead review |
| Report Writer | Produces final QA plan with go/no-go | QA Lead documentation |

**+ Judge Agent** — runs after every agent, catches hallucinations, triggers automatic correction loops before output passes downstream.

---

## 10 Industry Problems Solved

| # | Problem | Solution |
|---|---------|----------|
| 1 | Hallucination propagation | Judge Agent validates every output before passing downstream |
| 2 | Runaway loops and cost explosion | 3 retry max + 60s timeout + circuit breaker at $0.50 |
| 3 | Silent failures | Independent verification + confidence scoring + human gate |
| 4 | Context window drift | Full risk matrix passed agent to agent, no information lost |
| 5 | Prompt injection | Input sanitisation + system prompt separation |
| 6 | Non-determinism | Temperature=0 + Pydantic output schemas on every agent |
| 7 | Agent-to-agent hallucination | Agent 3 forbidden from inventing risk scores — references Agent 2 exactly |
| 8 | Over-engineering | 6 agents max, supervisor pattern, no peer-to-peer communication |
| 9 | No observability | Langfuse integration + Rich terminal logging + session JSON |
| 10 | No human in the loop | Mandatory human review gate — cannot be bypassed |

---

## Adaptive Complexity

The Test Case Writer adapts to requirement complexity automatically:

| Complexity | Batches | Cases per batch | Total |
|------------|---------|-----------------|-------|
| Simple | 3 | 8 | ~24 |
| Medium | 3 | 6 | ~18 |
| Complex | 4 | 5 | ~20 |
| Very Complex | 5 | 4 | ~20 |

Each batch is a separate API call — no JSON truncation, no cut-off test cases.

---

## Tech Stack

Python 3.11 — Core language
Claude API — claude-sonnet-4-6, temperature=0
CrewAI — Multi-agent orchestration
Pydantic v2 — Output schema validation
DeepEval — LLM output quality validation
Langfuse — Observability
Streamlit — Web dashboard
Rich — Terminal logging
pytest — Test runner
GitHub Actions — CI/CD


---

## Project Structure

qa-workflow-orchestrator/
├── agents/
│ ├── requirements_analyst.py # Agent 1
│ ├── risk_assessor.py # Agent 2
│ ├── test_strategist.py # Agent 3
│ ├── test_case_writer.py # Agent 4 — adaptive chunked generation
│ ├── coverage_analyser.py # Agent 5
│ ├── report_writer.py # Agent 6
│ └── judge_agent.py # Validates every agent output
├── validation/
│ ├── input_validator.py # User input validation
│ ├── output_validator.py # Agent output validation
│ └── guardrails.py # Cost, retry, timeout controls
├── tools/
│ ├── csv_reader.py # Reads existing test suite CSV
│ ├── report_generator.py # Generates HTML report
│ └── confidence_scorer.py # Calculates workflow confidence
├── tests/
│ ├── test_agents.py # Agent quality tests
│ ├── test_validators.py # Validator unit tests
│ └── test_edge_cases.py # Edge case scenarios
├── app.py # Streamlit dashboard
├── main.py # CLI orchestrator
└── requirements.txt


---

## Run Locally

### Prerequisites
- Python 3.11+
- Anthropic API key

### Setup

```bash
git clone https://github.com/thila98/qa-workflow-orchestrator
cd qa-workflow-orchestrator

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

### Run the dashboard

```bash
streamlit run app.py
```

### Run via CLI

```bash
python main.py
```

### Run tests

```bash
pytest tests/ -v
```

---

## Usage

1. Open the dashboard
2. Paste your software requirement
3. Optionally upload an existing test suite CSV for coverage gap analysis
4. Click **Run QA Workflow**
5. Watch 6 agents work in real time — each validated by the Judge Agent
6. Review outputs at the human gate — add notes or corrections
7. Approve to generate your final QA plan
8. Download HTML report and test cases CSV

**Free tier:** 5 runs free. Self-host for unlimited.

---

## Cost per run

| Requirement complexity | Approx cost |
|----------------------|-------------|
| Simple | $0.02 – 0.04 |
| Medium | $0.04 – 0.08 |
| Complex | $0.08 – 0.15 |
| Very complex | $0.15 – 0.35 |

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
MAX_COST_USD=0.50
MAX_RETRIES=3
AGENT_TIMEOUT_SECONDS=60
TEMPERATURE=0
```

---

## Safety Controls

- **Cost circuit breaker** — stops workflow if total API cost exceeds $0.50
- **Retry limit** — max 3 retries per agent before failing gracefully
- **Agent timeout** — 60 second timeout per agent call
- **Input sanitisation** — validates and cleans user input before processing
- **Judge Agent** — rejects hallucinated outputs before they reach the next agent

---

## Built by

**Thilangi Uththara De Silva** — Senior QA Engineer  
Galle, Sri Lanka  

[Portfolio](https://thila98.github.io/thilangi-portfolio) · [GitHub](https://github.com/thila98) · [LinkedIn](https://www.linkedin.com/in/thilangi-de-silva-66bb0b190/)

---

*Open source under MIT licence. Self-host for unlimited runs.*
