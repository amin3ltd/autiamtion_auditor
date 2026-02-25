"""
Automaton Auditor

A deep LangGraph swarm for autonomous governance and quality assurance.

This package implements the "Digital Courtroom" architecture:
- Detective Layer: Forensic analysis agents
- Judicial Layer: Dialectical judge personas  
- Supreme Court: Synthesis and final verdict
"""

from .state import (
    AgentState,
    Evidence,
    JudicialOpinion,
    CriterionResult,
    AuditReport,
    create_initial_state,
    validate_state,
)

from .graph import (
    create_auditor_graph,
    run_auditor,
)

__version__ = "0.1.0"

__all__ = [
    # State
    "AgentState",
    "Evidence", 
    "JudicialOpinion",
    "CriterionResult",
    "AuditReport",
    "create_initial_state",
    "validate_state",
    # Graph
    "create_auditor_graph",
    "run_auditor",
]
