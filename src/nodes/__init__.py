"""
Nodes package for Automaton Auditor.

Contains the agent nodes:
- detectives.py: RepoInvestigator, DocAnalyst, VisionInspector
- judges.py: Prosecutor, Defense, TechLead
- justice.py: ChiefJusticeNode
"""

from .detectives import (
    create_repo_investigator_node,
    create_doc_analyst_node,
    create_vision_inspector_node,
    create_evidence_aggregator_node,
)

from .judges import (
    create_prosecutor_node,
    create_defense_node,
    create_tech_lead_node,
)

from .justice import (
    create_chief_justice_node,
)

__all__ = [
    # Detectives
    "create_repo_investigator_node",
    "create_doc_analyst_node", 
    "create_vision_inspector_node",
    "create_evidence_aggregator_node",
    # Judges
    "create_prosecutor_node",
    "create_defense_node",
    "create_tech_lead_node",
    # Justice
    "create_chief_justice_node",
]
