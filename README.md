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

## Architecture Decision Rationale

![High-Level AI Agentic System Architecture](high-level%20AI%20agentic%20system%20architecture.png)

![LangChain Product Ecosystem](langchain%20product%20ecosystem.png)

### Why Pydantic for State Typing?

We chose Pydantic (BaseModel) over plain Python dictionaries for several critical reasons:

1. **Runtime Validation**: Pydantic automatically validates data at runtime. When evidence flows through the graph, we guarantee type correctness without manual validation at every step.

2. **IDE Support**: With Pydantic models, IDEs provide autocomplete, type checking, and refactoring support. This is crucial for a complex multi-agent system where state structures can become intricate.

3. **Schema Documentation**: The Pydantic models serve as self-documenting schemas. `Evidence.goal`, `JudicialOpinion.score`, etc. make the data structure immediately understandable.

4. **Serialization**: Pydantic models serialize to JSON effortlessly, which is essential for:
   - LangSmith tracing
   - Debugging state at any point
   - Storing audit reports

**Trade-off Considered**: We initially considered TypedDict for better TypeScript-like static typing. However, TypedDict only provides structural typing at static analysis time. Pydantic's runtime validation was more important for our use case where data flows through multiple LLM calls.

### Why AST Parsing for Forensic Analysis?

We use Python's `ast` module instead of regex or simple text matching for several reasons:

1. **Structural Understanding**: AST parsing understands Python's actual syntax structure. We can distinguish between a `StateGraph` instantiation vs. a string containing "StateGraph".

2. **Robustness**: Regex is brittle. Code formatting, comments, or string literals can break regex patterns. AST parsing is immune to such issues.

3. **Precision**: With AST, we can extract:
   - Exact class inheritance (`BaseModel`, `TypedDict`)
   - Function call arguments and their values
   - Import statements
   - Decorator applications

4. **Future-Proof**: AST parsing will work regardless of code formatting changes, as long as the Python syntax remains valid.

**Trade-off Considered**: AST parsing requires the target code to be syntactically valid Python. For code with syntax errors, we fall back to text-based analysis.

### Why Sandboxing for Git Operations?

Security is paramount when cloning and analyzing unknown repositories:

1. **Isolation**: Using `tempfile.TemporaryDirectory()` ensures the cloned repository never touches the main filesystem.

2. **Cleanup**: Temporary directories are automatically cleaned up, even if the analysis crashes.

3. **No Auth Leaks**: We never store credentials in the cloned repository.

**Trade-off Considered**: Sandboxing adds overhead. For the interim submission, we accept this trade-off for security.

## Gap Analysis and Forward Plan

### Known Gaps (Interim Submission)

| Gap | Description | Priority |
|-----|-------------|----------|
| Judges Not Implemented | Only detective layer is functional | High |
| Chief Justice Missing | Synthesis engine not yet built | High |
| VisionInspector Placeholder | Diagram analysis requires vision LLM | Medium |
| Cross-Reference Incomplete | Claim verification needs repo access | Medium |
| No Retry Logic | Failed nodes don't retry | Low |

### Forward Plan: Judicial Layer

The judicial layer implements the "Dialectical Synthesis" model where three judges analyze the same evidence from different perspectives:

#### Persona Differentiation

1. **Prosecutor (Critical Lens)**
   - System prompt emphasizes skepticism and finding flaws
   - Charges "Orchestration Fraud" for missing parallelism
   - Charges "Hallucination Liability" for unvalidated outputs
   - Always argues for lower scores when evidence is weak

2. **Defense Attorney (Optimistic Lens)**
   - System prompt emphasizes effort and intent
   - Looks for "Spirit of the Law" even when implementation is imperfect
   - Argues for higher scores based on:
     - Creative workarounds
     - Deep understanding in documentation
     - Commit history showing iteration

3. **Tech Lead (Pragmatic Lens)**
   - System prompt focuses on practical viability
   - Evaluates:
     - Code cleanliness
     - Maintainability
     - Actual functionality
   - Acts as tie-breaker between Prosecution and Defense

#### Conflict Resolution Strategy

The Chief Justice uses deterministic rules (not LLM interpretation):

1. **Rule of Security**: If Prosecutor identifies a confirmed security vulnerability, score is capped at 3 regardless of Defense arguments.

2. **Rule of Evidence**: If Defense claims "Deep Metacognition" but Detective evidence shows the artifact is missing, Defense is overruled.

3. **Rule of Functionality**: If Tech Lead confirms architecture is modular and workable, this carries highest weight for "Architecture" criterion.

4. **Rule of Dissent**: If score variance > 2 (e.g., Prosecutor=1, Defense=5), explicit dissent summary required.

### Forward Plan: Synthesis Engine

The ChiefJusticeNode will:

1. Collect all three JudicialOpinion objects per criterion
2. Apply hardcoded deterministic rules for conflict resolution
3. Generate structured Markdown report with:
   - Executive Summary
   - Criterion-by-criterion breakdown
   - Dissent summaries where applicable
   - Specific file-level remediation instructions

## Project Structure

```
autiamtion_auditor/
├── src/
│   ├── state.py          # Pydantic state definitions
│   ├── graph.py          # LangGraph orchestration
│   ├── tools/
│   │   ├── repo_tools.py  # Git & AST analysis
│   │   └── doc_tools.py   # PDF parsing
│   └── nodes/
│       ├── detectives.py  # Detective agents
│       └── judges.py      # Judge agents (placeholder)
├── starfield.html        # Interactive starfield visualization
├── pyproject.toml        # Dependencies
├── .env.example          # Environment variables
└── README.md             # This file
```

## Setup

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Copy `.env.example` to `.env` and add your API keys:
   ```
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-...
   ```

3. Run the auditor:
   ```python
   from src.graph import run_auditor
   
   result = run_auditor(
       repo_url="https://github.com/amin3ltd/autiamtion_auditor",
       pdf_path="./report.pdf",
       rubric_dimensions=[...]
   )
   ```

## Dependencies

- `langgraph` - Multi-agent orchestration
- `pydantic` - State validation
- `pypdf` - PDF parsing
- `Pillow` - Image extraction (optional)
- `python-dotenv` - Environment variables

## LangSmith Integration

Set `LANGCHAIN_TRACING_V2=true` and configure `LANGCHAIN_API_KEY` to enable LangSmith tracing for debugging complex multi-agent flows.

## License

MIT License
