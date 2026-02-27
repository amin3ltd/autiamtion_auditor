"""
Automaton Auditor - State Definitions

This module defines the typed state structures for the LangGraph orchestration.
Uses Pydantic for validation and LangGraph reducers for parallel execution safety.
"""

import operator
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# =============================================================================
# DETECTIVE OUTPUT - Structured Evidence Objects
# =============================================================================


class Evidence(BaseModel):
    """Represents a piece of forensic evidence collected by detective agents."""
    goal: str = Field(
        description="The investigation goal or rubric criterion being examined"
    )
    found: bool = Field(
        description="Whether the artifact or pattern was actually found"
    )
    content: Optional[str] = Field(
        default=None,
        description="The actual content or code snippet discovered"
    )
    location: str = Field(
        description="File path, commit hash, or location where evidence was found"
    )
    rationale: str = Field(
        description="The detective's reasoning for their confidence level"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )


# =============================================================================
# JUDGE OUTPUT - Structured Judicial Opinions
# =============================================================================


class JudicialOpinion(BaseModel):
    """Represents a judge's verdict on a specific rubric criterion."""
    judge: Literal["Prosecutor", "Defense", "TechLead"] = Field(
        description="Which judge persona rendered this opinion"
    )
    criterion_id: str = Field(
        description="The rubric dimension being evaluated"
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Score from 1 (failed) to 5 (masterful)"
    )
    argument: str = Field(
        description="The judge's reasoning and argumentation"
    )
    cited_evidence: List[str] = Field(
        description="References to evidence IDs that support this opinion"
    )


# =============================================================================
# CHIEF JUSTICE OUTPUT - Final Audit Report
# =============================================================================


class CriterionResult(BaseModel):
    """The final result for a single rubric criterion."""
    dimension_id: str = Field(
        description="Unique identifier for the rubric dimension"
    )
    dimension_name: str = Field(
        description="Human-readable name of the dimension"
    )
    final_score: int = Field(
        ge=1,
        le=5,
        description="The synthesized final score after conflict resolution"
    )
    judge_opinions: List[JudicialOpinion] = Field(
        description="All three judges' opinions on this criterion"
    )
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Summary of the conflict when score variance > 2"
    )
    remediation: str = Field(
        description="Specific file-level instructions for improvement"
    )


class AuditReport(BaseModel):
    """The final audit report synthesized by the Chief Justice."""
    repo_url: str = Field(
        description="The URL of the audited repository"
    )
    executive_summary: str = Field(
        description="High-level summary of the audit findings"
    )
    overall_score: float = Field(
        ge=1.0,
        le=5.0,
        description="Weighted average overall score"
    )
    criteria: List[CriterionResult] = Field(
        description="Results for each rubric dimension"
    )
    remediation_plan: str = Field(
        description="Consolidated remediation instructions"
    )


# =============================================================================
# GRAPH STATE - The Master State Container
# =============================================================================


DEFAULT_RUBRIC = [
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
    },
    {
        "id": "safe_tool_engineering",
        "name": "Safe Tool Engineering",
        "target_artifact": "github_repo"
    },
    {
        "id": "structured_output_enforcement",
        "name": "Structured Output Enforcement",
        "target_artifact": "github_repo"
    },
    {
        "id": "judicial_nuance",
        "name": "Judicial Nuance and Dialectics",
        "target_artifact": "github_repo"
    },
    {
        "id": "chief_justice_synthesis",
        "name": "Chief Justice Synthesis Engine",
        "target_artifact": "github_repo"
    },
    {
        "id": "theoretical_depth",
        "name": "Theoretical Depth (Documentation)",
        "target_artifact": "pdf_report"
    },
    {
        "id": "report_accuracy",
        "name": "Report Accuracy (Cross-Reference)",
        "target_artifact": "pdf_report"
    },
    {
        "id": "swarm_visual",
        "name": "Architectural Diagram Analysis",
        "target_artifact": "pdf_images"
    }
]


class AgentState(TypedDict):
    """
    The central state that flows through the entire LangGraph.
    
    Uses LangGraph reducers (operator.add, operator.ior) to safely handle
    parallel execution. Without reducers, parallel agents would overwrite
    each other's data.
    
    Key Design Decisions:
    - evidences: Uses operator.ior (OR) for dict merging - multiple detectives
      can add evidence without overwriting
    - opinions: Uses operator.add for list concatenation - judges append
      opinions rather than replacing
    """
    
    # Input parameters
    repo_url: str
    pdf_path: str
    rubric_dimensions: List[Dict]
    
    # Evidence collected by detectives (Dict[str, List[Evidence]])
    # Using operator.ior ensures parallel detectives don't overwrite each other
    evidences: Annotated[
        Dict[str, List[Evidence]], 
        operator.ior
    ]
    
    # Judicial opinions from judges (List[JudicialOpinion])
    # Using operator.add ensures all three judges' opinions are preserved
    opinions: Annotated[
        List[JudicialOpinion], 
        operator.add
    ]
    
    # Final output
    final_report: Optional[AuditReport]


# =============================================================================
# HELPER FUNCTIONS FOR STATE MANAGEMENT
# =============================================================================


def create_initial_state(
    repo_url: str,
    pdf_path: str,
    rubric_dimensions: Optional[List[Dict]] = None
) -> AgentState:
    """
    Factory function to create the initial state for the graph.
    
    Args:
        repo_url: GitHub repository URL to audit
        pdf_path: Path to the PDF report
        rubric_dimensions: The grading rubric as a list of dimension dicts.
                         Defaults to DEFAULT_RUBRIC if not provided.
    
    Returns:
        A properly typed initial AgentState
    """
    if rubric_dimensions is None:
        rubric_dimensions = DEFAULT_RUBRIC
    
    return {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": rubric_dimensions,
        "evidences": {},  # Empty dict - will use operator.ior to merge
        "opinions": [],   # Empty list - will use operator.add to extend
        "final_report": None
    }


def validate_state(state: AgentState) -> bool:
    """
    Validate that the state contains all required fields.
    
    Args:
        state: The AgentState to validate
    
    Returns:
        True if valid, raises ValueError otherwise
    """
    required_fields = [
        "repo_url", 
        "pdf_path", 
        "rubric_dimensions", 
        "evidences", 
        "opinions"
    ]
    
    for field in required_fields:
        if field not in state:
            raise ValueError(f"Missing required field in state: {field}")
    
    # Validate rubric dimensions have required keys
    for dim in state["rubric_dimensions"]:
        if "id" not in dim or "name" not in dim:
            raise ValueError("Each rubric dimension must have 'id' and 'name'")
    
    return True
