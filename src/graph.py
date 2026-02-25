"""
Automaton Auditor - LangGraph Orchestration

This module defines the StateGraph for the Digital Courtroom.
Shows the fan-out/fan-in pattern for both detectives and judges.

Architecture:
    START
      │
      ▼
┌─────────────────┐
│  ContextBuilder │ ─── Loads rubric dimensions
└────────┬────────┘
         │
         ▼ (FAN-OUT: Parallel execution)
┌───────────────────────────────────────────┐
│  RepoInvestigator  │  DocAnalyst  │ Vision │
└───────────────────────────────────────────┘
         │
         ▼ (FAN-IN: Aggregation)
┌─────────────────────┐
│  EvidenceAggregator │ ─── Merges all evidence
└──────────┬──────────┘
           │
           ▼ (FAN-OUT: Judges analyze same evidence)
┌─────────────────────────────────────────────┐
│  Prosecutor  │  Defense  │  TechLead        │
└─────────────────────────────────────────────┘
           │
           ▼ (FAN-IN)
┌─────────────────────┐
│   ChiefJustice     │ ─── Synthesis & Verdict
└──────────┬──────────┘
           │
           ▼
         END
"""

from typing import List, Dict, Optional

from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from .state import AgentState, create_initial_state, AuditReport


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================


def create_auditor_graph(
    llm=None,
    vision_llm=None,
    rubric_dimensions: Optional[List[Dict]] = None
) -> StateGraph:
    """
    Create the Automaton Auditor StateGraph.
    
    This graph implements the "Digital Courtroom" architecture with:
    1. Parallel detective execution (fan-out)
    2. Evidence aggregation (fan-in)
    3. Parallel judge execution (fan-out)
    4. Chief Justice synthesis (fan-in)
    
    Args:
        llm: LLM for judge nodes
        vision_llm: Vision LLM for diagram analysis
        rubric_dimensions: The grading rubric
    
    Returns:
        Compiled LangGraph StateGraph
    """
    from .nodes.detectives import (
        create_repo_investigator_node,
        create_doc_analyst_node,
        create_vision_inspector_node,
        create_evidence_aggregator_node,
    )
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("context_builder", lambda state: state)
    workflow.add_node(
        "repo_investigator", 
        create_repo_investigator_node(llm)
    )
    workflow.add_node(
        "doc_analyst", 
        create_doc_analyst_node(llm)
    )
    workflow.add_node(
        "vision_inspector", 
        create_vision_inspector_node(vision_llm)
    )
    workflow.add_node(
        "evidence_aggregator", 
        create_evidence_aggregator_node()
    )
    
    # Note: Judges and ChiefJustice are placeholder for final submission
    # They would be added in Phase 3/4
    
    # Set entry point
    workflow.set_entry_point("context_builder")
    
    # ==========================================================================
    # PHASE 1: Detectives Fan-Out
    # ==========================================================================
    # The context_builder sends to all three detectives in parallel
    workflow.add_edge("context_builder", "repo_investigator")
    workflow.add_edge("context_builder", "doc_analyst")
    workflow.add_edge("context_builder", "vision_inspector")
    
    # ==========================================================================
    # PHASE 2: Evidence Aggregation Fan-In
    # ==========================================================================
    # All detectives must complete before aggregation
    workflow.add_edge("repo_investigator", "evidence_aggregator")
    workflow.add_edge("doc_analyst", "evidence_aggregator")
    workflow.add_edge("vision_inspector", "evidence_aggregator")
    
    # Note: In a full implementation, we'd add conditional edges here
    # to handle cases where evidence collection fails
    
    # ==========================================================================
    # PHASE 3 & 4: Judges and ChiefJustice (Placeholder)
    # ==========================================================================
    # These would be added in the final submission:
    #
    # workflow.add_node("prosecutor", create_prosecutor_node(llm))
    # workflow.add_node("defense", create_defense_node(llm))
    # workflow.add_node("tech_lead", create_tech_lead_node(llm))
    # workflow.add_node("chief_justice", create_chief_justice_node(llm))
    #
    # # Judges fan-out
    # workflow.add_edge("evidence_aggregator", "prosecutor")
    # workflow.add_edge("evidence_aggregator", "defense")
    # workflow.add_edge("evidence_aggregator", "tech_lead")
    #
    # # Judges fan-in
    # workflow.add_edge("prosecutor", "chief_justice")
    # workflow.add_edge("defense", "chief_justice")
    # workflow.add_edge("tech_lead", "chief_justice")
    #
    # workflow.add_edge("chief_justice", END)
    
    # For interim: end after evidence aggregation
    workflow.add_edge("evidence_aggregator", END)
    
    return workflow.compile()


def create_advanced_auditor_graph(
    llm=None,
    vision_llm=None,
    rubric_dimensions: Optional[List[Dict]] = None
) -> StateGraph:
    """
    Create an advanced version with proper Send() for fan-out.
    
    This version uses langgraph's Send() to dynamically dispatch
    to parallel branches, which is cleaner for variable numbers
    of parallel agents.
    
    Args:
        llm: LLM for judge nodes
        vision_llm: Vision LLM for diagram analysis
        rubric_dimensions: The grading rubric
    
    Returns:
        Compiled LangGraph StateGraph
    """
    from .nodes.detectives import (
        create_repo_investigator_node,
        create_doc_analyst_node,
        create_vision_inspector_node,
        create_evidence_aggregator_node,
    )
    
    def should_run_detective(detective_name: str):
        """Helper to create detective run functions."""
        def run_detective(state: AgentState):
            if detective_name == "repo_investigator":
                return create_repo_investigator_node(llm)(state)
            elif detective_name == "doc_analyst":
                return create_doc_analyst_node(llm)(state)
            elif detective_name == "vision_inspector":
                return create_vision_inspector_node(vision_llm)(state)
            return {}
        return run_detective
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("context_builder", lambda state: state)
    workflow.add_node("evidence_aggregator", create_evidence_aggregator_node())
    
    # Add detective nodes dynamically
    for detective in ["repo_investigator", "doc_analyst", "vision_inspector"]:
        workflow.add_node(detective, should_run_detective(detective))
    
    # Set entry point
    workflow.set_entry_point("context_builder")
    
    # Use conditional edges for fan-out
    # This allows all detectives to run in parallel
    workflow.add_conditional_edges(
        "context_builder",
        lambda state: ["repo_investigator", "doc_analyst", "vision_inspector"]
    )
    
    # All detectives fan-in to evidence aggregator
    workflow.add_edge("repo_investigator", "evidence_aggregator")
    workflow.add_edge("doc_analyst", "evidence_aggregator")
    workflow.add_edge("vision_inspector", "evidence_aggregator")
    
    # End after aggregation (interim submission)
    workflow.add_edge("evidence_aggregator", END)
    
    return workflow.compile()


# =============================================================================
# GRAPH EXECUTION
# =============================================================================


def run_auditor(
    repo_url: str,
    pdf_path: str,
    rubric_dimensions: List[Dict],
    llm=None,
    vision_llm=None
) -> AgentState:
    """
    Run the auditor graph against a target repository and PDF.
    
    Args:
        repo_url: GitHub repository URL to audit
        pdf_path: Path to the PDF report
        rubric_dimensions: The grading rubric
        llm: Optional LLM for enhanced analysis
        vision_llm: Optional vision LLM for diagram analysis
    
    Returns:
        Final AgentState with evidence collected
    """
    # Create initial state
    initial_state = create_initial_state(
        repo_url=repo_url,
        pdf_path=pdf_path,
        rubric_dimensions=rubric_dimensions
    )
    
    # Create and run the graph
    graph = create_auditor_graph(llm, vision_llm, rubric_dimensions)
    
    result = graph.invoke(initial_state)
    
    return result


# =============================================================================
# EXAMPLE USAGE
# =============================================================================


if __name__ == "__main__":
    # Example rubric dimensions
    sample_rubric = [
        {
            "id": "git_forensic_analysis",
            "name": "Git Forensic Analysis",
            "target_artifact": "github_repo"
        },
        {
            "id": "state_management_rigor",
            "name": "State Management Rigor", 
            "target_artifact": "github_repo"
        },
        {
            "id": "graph_orchestration",
            "name": "Graph Orchestration Architecture",
            "target_artifact": "github_repo"
        }
    ]
    
    # This would run the graph (requires actual repo and PDF)
    # result = run_auditor(
    #     repo_url="https://github.com/example/repo",
    #     pdf_path="./report.pdf",
    #     rubric_dimensions=sample_rubric
    # )
    # print(result)
    
    print("Graph definition created. Run with actual repo and PDF to execute.")
