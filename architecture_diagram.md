# Automaton Auditor - StateGraph Architecture

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AUTOMATON AUDITOR - DIGITAL COURTROOM                │
│                        Hierarchical LangGraph Swarm                          │
└─────────────────────────────────────────────────────────────────────────────┘

                                    START
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTEXT BUILDER                                    │
│                    Loads rubric dimensions into state                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │   REPO           │ │   DOC            │ │   VISION         │
         │   INVESTIGATOR   │ │   ANALYST        │ │   INSPECTOR      │
         │   (Code Detective)│ │   (Paperwork)   │ │   (Diagrams)     │
         │                   │ │                  │ │                   │
         │  Tools:          │ │  Tools:          │ │  Tools:          │
         │  • git clone    │ │  • PDF parse     │ │  • Image extract │
         │  • git log      │ │  • RAG-lite     │ │  • Vision LLM    │
         │  • AST parse    │ │  • Cross-ref    │ │                   │
         └──────────────────┘ └──────────────────┘ └──────────────────┘
                    │                 │                 │
                    │    FAN-OUT: Parallel Execution      │
                    │    (All 3 detectives run concurrently)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVIDENCE AGGREGATOR                                 │
│                    Fan-in: Merges evidence from all detectives             │
│                    Type: Dict[str, List[Evidence]] with operator.ior        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │   PROSECUTOR      │ │   DEFENSE        │ │   TECH LEAD     │
         │   (Critical)     │ │   (Optimistic)   │ │   (Pragmatic)   │
         │                   │ │                  │ │                   │
         │  Philosophy:     │ │  Philosophy:     │ │  Philosophy:    │
         │  "Trust No One"  │ │  "Reward Effort" │ │  "Does it work?" │
         │                   │ │                  │ │                   │
         │  Role:           │ │  Role:           │ │  Role:           │
         │  • Find gaps     │ │  • Find merit    │ │  • Evaluate      │
         │  • Security     │ │  • Intent        │ │    viability     │
         │  • Laziness     │ │  • Workarounds   │ │  • Clean code    │
         │                   │ │                  │ │                   │
         │  Output:         │ │  Output:         │ │  Output:         │
         │  JudicialOpinion │ │  JudicialOpinion │ │  JudicialOpinion │
         │  (score: 1-5)    │ │  (score: 1-5)    │ │  (score: 1-5)    │
         └──────────────────┘ └──────────────────┘ └──────────────────┘
                    │                 │                 │
                    │    FAN-OUT: Parallel Judges Analyzing Same Evidence     │
                    │    (All 3 judges receive identical evidence, produce different opinions)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHIEF JUSTICE                                      │
│                    Synthesis Engine & Conflict Resolution                    │
│                                                                              │
│   Rules:                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │ • Rule of Security: Security flaw caps score at 3                  │  │
│   │ • Rule of Evidence: Facts override opinions                         │  │
│   │ • Rule of Functionality: Tech Lead carries weight for architecture  │  │
│   │ • Rule of Dissent: Variance > 2 requires explicit dissent summary   │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│   Output: AuditReport (Markdown)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                                    END
```

## State Types on Edges

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STATE TYPE FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

START ──► (AgentState: repo_url, pdf_path, rubric_dimensions)

  │
  │  AgentState: empty evidences, opinions
  ▼
  
ContextBuilder ──► (AgentState: with rubric_dimensions populated)

  │
  │  AgentState: rubric_dimensions: List[Dict]
  ▼
  
[Detectives Fan-Out]

  │
  │  AgentState: passing rubric to each detective
  │  Each detective runs independently (parallel)
  ▼
  
RepoInvestigator ─┐
DocAnalyst      ──┼──► (AgentState: evidences accumulates via operator.ior)
VisionInspector ─┘

  │
  │  AgentState: evidences: Dict[str, List[Evidence]] 
  │              (Multiple detectives' evidence merged)
  ▼
  
EvidenceAggregator ──► (AgentState: all_evidence validated)

  │
  │  AgentState: validated evidence ready for judges
  ▼
  
[Judges Fan-Out]

  │
  │  AgentState: same evidence passed to all 3 judges
  ▼
  
Prosecutor ─┐
Defense   ──┼──► (AgentState: opinions accumulates via operator.add)
TechLead  ──┘

  │
  │  AgentState: opinions: List[JudicialOpinion]
  │              (Three distinct opinions on each criterion)
  ▼
  
ChiefJustice ──► (AgentState: final_report: AuditReport)

  │
  │  AgentState: final_report with verdict, dissent, remediation
  ▼
  
END
```

## Parallel Execution Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FAN-OUT / FAN-IN PATTERN                          │
└─────────────────────────────────────────────────────────────────────────────┘

FAN-OUT (Parallel Dispatch):
═══════════════════════════

   ┌─────────────┐
   │    node_A   │
   └──────┬──────┘
          │
          │ (dispatch to multiple nodes)
          ├──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌───────────┐      ┌───────────┐      ┌───────────┐
    │  node_B1  │      │  node_B2  │      │  node_B3  │
    │ (agent 1) │      │ (agent 2) │      │ (agent 3) │
    └───────────┘      └───────────┘      └───────────┘


FAN-IN (Synchronization):
═════════════════════════

    ┌───────────┐      ┌───────────┐      ┌───────────┐
    │  node_B1  │      │  node_B2  │      │  node_B3  │
    └──────┬─────┘      └──────┬─────┘      └──────┬─────┘
           │                  │                  │
           │ (wait for all)───┼──────────────────┤
           │                  │                  │
           ▼                  ▼                  ▼
                         ┌─────────────┐
                         │    node_C   │
                         │ (aggregator)│
                         └─────────────┘


IN OUR ARCHITECTURE:
═══════════════════

Detectives: 3 parallel agents (Repo, Doc, Vision)
            │
            ▼ fan-in
EvidenceAggregator
            │
            ▼ fan-out
Judges: 3 parallel agents (Prosecutor, Defense, TechLead)
        │
        ▼ fan-in
ChiefJustice
```

## State Reducers Explained

```python
# The key to parallel execution: State Reducers

from typing import Annotated
import operator

class AgentState(TypedDict):
    # For Dicts: use operator.ior (inclusive OR / merge)
    # This means: {"a": 1} + {"b": 2} = {"a": 1, "b": 2}
    evidences: Annotated[
        Dict[str, List[Evidence]], 
        operator.ior    # ← MERGE dicts, don't overwrite
    ]
    
    # For Lists: use operator.add
    # This means: [1, 2] + [3, 4] = [1, 2, 3, 4]
    opinions: Annotated[
        List[JudicialOpinion], 
        operator.add   # ← EXTEND lists, don't replace
    ]
```

## Why This Architecture?

| Pattern | Benefit | In Our System |
|---------|---------|---------------|
| **Fan-Out/Fan-In** | Parallelism + Synchronization | Detectives and Judges both fan-out |
| **Typed State** | Type safety, self-documenting | Pydantic models throughout |
| **Persona Separation** | Dialectical tension = better judgments | 3 distinct judge voices |
| **Deterministic Synthesis** | Reproducible, explainable verdicts | Chief Justice uses hardcoded rules |
| **Evidence-First** | Facts over opinions | Detectives gather, Judges interpret |

## LangGraph Node Types Used

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NODE TYPE REFERENCE                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. Standard Node:
   workflow.add_node("name", callable)
   
2. Conditional Edge (dynamic fan-out):
   workflow.add_conditional_edges(
       "source",
       routing_function  # Returns list of target nodes
   )
   
3. Simple Edge (direct):
   workflow.add_edge("source", "target")
   
4. Parallel Dispatch (Send):
   # For truly parallel execution within a node
   from langgraph.constants import Send
   
   def route_to_detectives(state):
       return [
           Send("repo_investigator", state),
           Send("doc_analyst", state),
           Send("vision_inspector", state)
       ]
   
   workflow.add_conditional_edges(
       "context_builder",
       route_to_detectives
   )
```
