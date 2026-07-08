# Autonomous Document Agent

An autonomous AI agent that reads a natural-language request, **plans its own
task list**, executes each task, and produces a **polished Microsoft Word
(.docx)** business document — proposals, project plans, meeting minutes,
technical designs, SOPs, and more.

Built with **LangGraph**, **FastAPI**, **Groq** (free-tier Llama 3.3 70B),
**python-docx**, **Streamlit**, and **asyncio**.

---

## Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure your free Groq key (https://console.groq.com/keys)
cp .env.example .env      # then edit GROQ_API_KEY

# 3a. Run the Streamlit UI (recommended — shows every step visually)
streamlit run streamlit_app.py

# 3b. Run the two required demos directly (no server needed)
python demo.py

# 3c. Or run the API
uvicorn app.main:app --reload
# POST http://127.0.0.1:8000/agent   {"request": "..."}
# Interactive docs at http://127.0.0.1:8000/docs
```

### Example API call

```bash
curl -X POST http://127.0.0.1:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"request":"Create a project plan for launching a food-ordering app with timeline, roles, milestones and budget."}'
```

The response contains the agent's `document_type`, `title`, the self-generated
`plan` + `task_list`, any `warnings`, and a `download_url`. Fetch the file:

```bash
curl -OJ http://127.0.0.1:8000/documents/<filename>.docx
```

---

## Architecture

```
                 POST /agent  {"request": "..."}
                          │
                          ▼
   ┌───────── DocumentAgent (agent.py) via LangGraph ─────────┐
   │                                                          │
   │  1. validate_node   validate + normalise request (cheap) │
   │  2. plan_node       LLM → ExecutionPlan (doc type, title,│
   │                     assumptions, task list)  ◀── PLAN    │
   │  3. execute_node    asyncio.gather over tasks → content  │
   │                     (per-section retry + recovery)       │
   │  4. render_node     python-docx → polished .docx         │
   │  5. respond_node    plan + task list + warnings + link   │
   └──────────────────────────────────────────────────────────┘
                          │
   llm.py  ──►  Groq (primary: llama-3.3-70b, fallback: llama-3.1-8b)
                retry + model fallback + robust JSON extraction
```

| Module              | Responsibility                                             |
|---------------------|------------------------------------------------------------|
| `streamlit_app.py`  | **Streamlit UI** — real-time step-by-step visualization     |
| `main.py`           | FastAPI routes: `/agent`, `/documents/{file}`, `/health`   |
| `agent.py`          | **LangGraph StateGraph** orchestrating the full pipeline    |
| `planner.py`        | **Autonomous multi-step planning** (the agent's brain)      |
| `executor.py`       | Concurrent task execution + per-section recovery            |
| `document.py`       | Polished .docx rendering (cover, headings, banded tables)   |
| `llm.py`            | Groq wrapper: retries, model fallback, JSON parsing         |
| `guardrails.py`     | Deterministic input validation                              |
| `models.py`         | Pydantic contracts shared across all stages                 |
| `config.py`         | Env-driven settings (swap model/provider in one place)      |

**Why plan/execute are separate:** the plan is an inspectable, testable artefact
we orchestrate work over. That separation is what makes this an *agent* rather
than a single prompt — the agent decides the structure, then carries it out.

---

## The one engineering improvement — **Multi-step planning**
*(with error-handling & retry/fallback as supporting robustness)*

**What:** The agent never uses a fixed template. Given a request, the Planner
(`planner.py`) autonomously decides the document *type*, *title*, *audience*,
the *assumptions* it must make when information is missing, and an *ordered list
of sections* — each a discrete task with its own instruction and layout hint
(`paragraph` / `bullets` / `table`). The Executor then fans out over that plan.

**Why I chose it:** Planning is the capability that most directly separates an
"autonomous agent" from a chatbot, and it's exactly what the complex/ambiguous
test case demands: the agent must *decide its own execution plan and make
reasonable assumptions*. It also makes the system extensible — richer documents
just mean richer plans, no new code paths.

**How it improves the agent:**
- Handles vague requests by explicitly surfacing assumptions in the document.
- Produces the right structure per document type instead of one rigid layout.
- The plan is the natural unit for concurrency (`asyncio.gather`) and for the
  graceful-degradation logic (a bad section is isolated, not fatal).

Supporting robustness so the autonomous pipeline doesn't crash on the first
imperfect model output: `llm.py` retries each call, **falls back** from the
70B model to an 8B model, and extracts JSON even when wrapped in prose/fences;
`executor.py` degrades a single failed section to a placeholder + warning rather
than failing the whole request; `guardrails.py` rejects bad input up front.

---

## Two test inputs (see `demo.py`)

1. **Standard business request** — *"Create a project plan for launching a
   food-ordering app with a timeline, team roles, milestones, and a budget."*
   → The agent produces a 7-section **Project Plan** with timeline, roles and
   budget **tables**.

2. **Complex / ambiguous request** — a leadership-offsite AI-strategy document
   that is under-specified (no budget numbers) and self-contradictory ("fit on
   one page but be comprehensive"). → The agent picks the **Executive Brief**
   format, decides its own structure, and records explicit **assumptions**
   (including how it reconciles the one-page-vs-comprehensive conflict).

---

## Talking points for the video

- **Debugging insight.** LLMs intermittently return JSON wrapped in prose or
  ```json fences, or occasionally invalid JSON — which crashed parsing on some
  runs. Root cause: relying on the raw string being pure JSON. Fix: enable
  Groq's JSON mode *and* a layered extractor (raw → fenced → outer-braces) plus
  retry/fallback in `LLMClient._parse_json` / `_with_resilience`. The pipeline
  went from occasionally failing to consistently succeeding.

- **Tradeoff — Autonomous planning vs deterministic workflows.** I let the LLM
  design the document structure rather than hard-coding templates. Cost: less
  predictable output and dependence on model quality. Benefit: it handles *any*
  document type and genuinely ambiguous requests. I mitigated the downside with
  strict Pydantic coercion, safe default plans, and per-section recovery — so
  autonomy never means fragility.

- **Scalability.** Sections execute concurrently; the LLM layer is swappable via
  `config.py` (Groq → Ollama/Gemini in one file); stages are decoupled and
  independently testable (`tests/test_agent.py` runs fully offline with a stub).

---

## Streamlit Dashboard

The Streamlit UI provides a premium, dark-themed dashboard that visualises every
step of the LangGraph pipeline in real-time:

- **Live pipeline progress bar** — each node lights up as it completes
- **Sidebar graph flow** — vertical LangGraph workflow with live status
- **Step-by-step cards** — validation, planning (with assumptions), concurrent
  execution (with section content previews + tables), rendering, and response
- **One-click download** of the generated `.docx`
- **Example requests** for quick testing

```bash
streamlit run streamlit_app.py
```

---

## Tests

```bash
python -m pytest -q          # or:  python tests/test_agent.py
```

Offline tests (no API key needed) cover guardrails, the full plan→render
pipeline via an injected stub LLM, and the graceful-degradation path.

---

## Print LangGraph Flow (CLI)

```bash
pip install grandalf
python -c "from app.agent import DocumentAgent; print(DocumentAgent()._graph.get_graph().draw_ascii())"
```
