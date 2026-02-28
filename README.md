# Automaton Auditor

A deep LangGraph swarm for autonomous governance and quality assurance of AI-generated code.

## Overview

The Automaton Auditor is a hierarchical multi-agent system inspired by the "Digital Courtroom" concept. It orchestrates specialized detective agents to collect forensic evidence, judge agents with distinct personas to render verdicts, and a Chief Justice to synthesize final decisions.

## Interactive Starfield Visualization

A calming interactive starfield visualization is included in [`starfield.html`](starfield.html). Open this file in a web browser to experience:

- **Multi-layer parallax stars** - 400 stars across 3 depth layers
- **Mouse gesture controls** - Stars drift smoothly following your cursor movement
- **Twinkling animation** - Gentle twinkling effect for a calming atmosphere
- **Touch support** - Works on mobile devices with touch gestures

## Architecture

![High-Level AI Agentic System Architecture](high-level%20AI%20agentic%20system%20architecture.png)

![LangChain Product Ecosystem](langchain%20product%20ecosystem.png)

### Digital Courtroom Architecture

The system implements a "Digital Courtroom" with:

1. **Detective Layer** (Fan-Out)
   - **RepoInvestigator**: Analyzes Git history, state management, graph orchestration
   - **DocAnalyst**: Evaluates PDF reports for theoretical depth and accuracy
   - **VisionInspector**: Analyzes architecture diagrams (requires vision LLM)

2. **Judicial Layer** (Fan-Out)
   - **Prosecutor**: Critical lens - looks for flaws, security issues
   - **Defense**: Optimistic lens - rewards effort and intent
   - **TechLead**: Pragmatic lens - evaluates architectural soundness

3. **Chief Justice** (Fan-In)
   - Deterministic conflict resolution
   - Security override rules
   - Dissent summarization

### State Management

The system uses **LangGraph reducers** for safe parallel execution:
- `operator.ior` for dictionary merge (prevents evidence overwriting)
- `operator.add` for list concatenation (preserves all judge opinions)

## Project Structure

```
autiamtion_auditor/
├── src/
│   ├── state.py              # Pydantic state definitions
│   ├── graph.py              # LangGraph orchestration
│   ├── llm_providers.py      # Multi-provider LLM abstraction
│   ├── lm_studio.py          # LM Studio integration
│   ├── langsmith_tracing.py  # LangSmith tracing integration
│   ├── tools/
│   │   ├── repo_tools.py    # Git & AST analysis
│   │   └── doc_tools.py     # PDF parsing
│   └── nodes/
│       ├── detectives.py     # Detective agents
│       ├── judges.py         # Judge agents (with structured output)
│       └── justice.py        # Chief Justice synthesis
├── dashboard/                # Web dashboard
│   ├── main.py              # FastAPI server
│   ├── app.py               # Streamlit dashboard
│   └── export_utils.py      # Report export utilities
├── tests/                   # Test suite
│   ├── test_state.py
│   ├── test_llm_providers.py
│   ├── test_integration.py
│   └── test_export.py
├── audit/                   # Audit reports
│   ├── report_onself_generated/
│   ├── report_onpeer_generated/
│   └── report_bypeer_received/
├── reports/                 # Evaluation reports
│   ├── report.md
│   └── rubric.json
├── starfield.html          # Interactive starfield visualization
├── Dockerfile               # Containerized deployment
├── docker-compose.yml       # Docker orchestration
├── pyproject.toml          # Dependencies
├── .env.example            # Environment variables
└── README.md               # This file
```

## Setup

### Option 1: Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and configure:
   ```bash
   # For OpenAI (requires API key)
   OPENAI_API_KEY=sk-...
   
   # For LM Studio (local, free)
   LM_STUDIO_URL=http://localhost:1234/v1
   LM_MODEL=gemma-3-4b
   
   # LangSmith Tracing (optional but recommended)
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=ls-...
   LANGCHAIN_PROJECT=automaton-auditor
   ```

3. (Optional) Using LM Studio for local models:
   - Download LM Studio from https://lmstudio.ai/
   - Load a model (e.g., llama3.2, gemma-3-4b)
   - Start the local server (click "Start Server" in LM Studio)

4. Run the auditor:
   ```python
   from src.graph import run_auditor
   from src.lm_studio import create_lm_studio_llm
   
   # Create LLM using LM Studio
   llm = create_lm_studio_llm(model_name="gemma-3-4b")
   
   # Define rubric dimensions for evaluation
   rubric_dimensions = [
       {
           "id": "git_forensic_analysis",
           "name": "Git Forensic Analysis",
           "target_artifact": "github_repo",
           "forensic_instruction": "Run 'git log --oneline --reverse' and check commit progression"
       },
       {
           "id": "state_management_rigor",
           "name": "State Management Rigor",
           "target_artifact": "github_repo",
           "forensic_instruction": "Check for Pydantic models and Annotated reducers in state.py"
       },
       {
           "id": "graph_orchestration",
           "name": "Graph Orchestration",
           "target_artifact": "github_repo",
           "forensic_instruction": "Verify parallel fan-out/fan-in in graph.py"
       }
   ]
   
   # Run the auditor
   result = run_auditor(
       repo_url="https://github.com/your-org/your-repo",
       pdf_path="./report.pdf",
       rubric_dimensions=rubric_dimensions,
       llm=llm
   )
   
   # Access results
   if result.get("final_report"):
       print(f"Overall Score: {result['final_report'].overall_score}/5.0")
   ```

### Option 2: Docker

1. Build the container:
   ```bash
   docker build -t automaton-auditor .
   ```

2. Run with Docker Compose:
   ```bash
   docker-compose up
   ```

3. Access the dashboard at http://localhost:8000

## LLM Providers

The Automaton Auditor supports multiple LLM providers through [`src/llm_providers.py`](src/llm_providers.py):

| Provider | Type | API Key Required | Vision Support |
|----------|------|------------------|----------------|
| LM Studio | Local | No | No |
| Ollama | Local | No | No |
| OpenAI | Cloud | Yes | Yes |
| Anthropic (Claude) | Cloud | Yes | Yes |
| Google Gemini | Cloud | Yes | Yes |
| Azure OpenAI | Cloud | Yes | Yes |
| Cohere | Cloud | Yes | No |
| Hugging Face | Cloud | Yes | No |

### Using LLM Providers

```python
from src.llm_providers import create_llm, LLMProvider

# Use LM Studio (local)
llm = create_llm(
    LLMProvider.LM_STUDIO,
    model="llama3.2:latest",
    base_url="http://localhost:1234/v1"
)

# Use OpenAI
llm = create_llm(
    LLMProvider.OPENAI,
    model="gpt-4o",
    api_key="sk-..."
)

# Use Anthropic Claude
llm = create_llm(
    LLMProvider.ANTHROPIC,
    model="claude-sonnet-4-20250514",
    api_key="sk-..."
)
```

## LangSmith Integration

LangSmith provides debugging, monitoring, and tracing for complex multi-agent flows.

### Configuration

Add to your `.env`:
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_PROJECT=automaton-auditor
```

### Viewing Traces

After running an audit, visit https://smith.langchain.com to view:
- All node executions
- LLM calls and responses
- State transitions
- Performance metrics

### LangSmith Module

The [`src/langsmith_tracing.py`](src/langsmith_tracing.py) module provides:
- `get_langsmith_config()` - Get configuration from environment
- `is_langsmith_enabled()` - Check if tracing is enabled
- `AuditRunTracker` - Track audit runs with metadata
- `get_langsmith_dashboard_url()` - Get dashboard link

## Web Dashboard

A web dashboard is available for running audits and viewing results:

### FastAPI Dashboard

```bash
python dashboard/main.py
```

Access at: http://localhost:8000

### Streamlit Dashboard

```bash
streamlit run dashboard/app.py
```

Features:
- Provider selection and health checks
- Rubric dimension configuration
- Audit execution with progress tracking
- Results visualization
- Report export (Markdown, JSON, HTML, Text)

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run integration tests:
```bash
pytest tests/test_integration.py -v
```

### Test Results

```
======================= 18 passed in 0.26s =======================

tests/test_integration.py::TestChiefJusticeSynthesis - 7 passed
tests/test_integration.py::TestGraphCreation - 3 passed
tests/test_integration.py::TestEndToEndWorkflow - 4 passed
tests/test_integration.py::TestParallelExecution - 2 passed
tests/test_integration.py::TestErrorHandling - 2 passed
```

## Dialectical Synthesis

The system demonstrates true dialectical synthesis - three distinct perspectives evaluating the same evidence:

```
=== JUDGE OPINIONS ===
- Prosecutor: Graph Orchestration - Score: 1/5
  "This evidence presents several concerning aspects..."

- Defense: Graph Orchestration - Score: 5/5
  "This evidence demonstrates a surprisingly sophisticated attempt..."

- Tech Lead: Graph Orchestration - Score: 5/5
  "Does it actually work? The confidence score of 0.8..."
```

The Chief Justice resolves conflicts using deterministic rules:
- **Security Override**: Security flaws cap score at 3
- **Fact Supremacy**: Evidence overrules opinions
- **Functionality Weight**: Tech Lead confirmation carries highest weight
- **Dissent Requirement**: Variance > 2 requires explicit dissent

## Dependencies

- `langgraph` - Multi-agent orchestration
- `langchain-core` - LangChain core
- `langchain-openai` - OpenAI integration
- `langchain-anthropic` - Anthropic Claude
- `langsmith` - Tracing and monitoring
- `pydantic` - State validation
- `pypdf` - PDF parsing
- `python-dotenv` - Environment variables
- `fastapi` - Web dashboard API
- `uvicorn` - ASGI server

## License

MIT License
