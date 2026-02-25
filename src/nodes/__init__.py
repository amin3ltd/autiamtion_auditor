"""
Nodes package for Automaton Auditor.

Contains the agent nodes:
- detectives.py: RepoInvestigator, DocAnalyst, VisionInspector
- judges.py: Prosecutor, Defense, TechLead (placeholder for final)
- justice.py: ChiefJusticeNode (placeholder for final)
"""

from .detectives import (
    create_repo_investigator_node,
    create_doc_analyst_node,
    create_vision_inspector_node,
    create_evidence_aggregator_node,
)

__all__ = [
    "create_repo_investigator_node",
    "create_doc_analyst_node", 
    "create_vision_inspector_node",
    "create_evidence_aggregator_node",
]
