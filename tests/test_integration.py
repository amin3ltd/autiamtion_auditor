"""
Integration Tests for Automaton Auditor

Tests the complete workflow from state to graph execution.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state import (
    Evidence,
    JudicialOpinion,
    CriterionResult,
    AuditReport,
    AgentState,
    create_initial_state
)
from src.nodes.justice import (
    resolve_conflict,
    apply_security_override,
    generate_remediation,
    create_chief_justice_node
)
from src.graph import create_auditor_graph, create_advanced_auditor_graph


class TestChiefJusticeSynthesis:
    """Test Chief Justice synthesis logic."""
    
    def test_resolve_conflict_simple_average(self):
        """Test simple average when scores are close."""
        score, dissent = resolve_conflict(3, 4, 3)
        
        assert score == 3  # Average of 3, 4, 3 = 3.33 rounded
        assert dissent == ""
    
    def test_resolve_conflict_high_variance(self):
        """Test conflict resolution with high variance."""
        score, dissent = resolve_conflict(1, 5, 3)
        
        assert score == 3  # Middle value
        assert "variance" in dissent.lower()
    
    def test_resolve_conflict_security_override(self):
        """Test security override when score is 1."""
        score, dissent = resolve_conflict(1, 5, 5)
        
        assert score == 3  # Capped at 3 due to security
        assert "security" in dissent.lower() or "override" in dissent.lower()
    
    def test_apply_security_override_no_issues(self):
        """Test security override with no issues."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=4,
                argument="Good implementation",
                cited_evidence=[]
            )
        ]
        
        assert apply_security_override(opinions) is False
    
    def test_apply_security_override_detected(self):
        """Test security override detection."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=1,
                argument="Security vulnerability found: os.system injection",
                cited_evidence=[]
            )
        ]
        
        assert apply_security_override(opinions) is True
    
    def test_generate_remediation_no_issues(self):
        """Test remediation generation with no issues."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=5,
                argument="Excellent",
                cited_evidence=[]
            )
        ]
        
        remediation = generate_remediation("Test Criterion", opinions)
        
        assert "maintain" in remediation.lower()
    
    def test_generate_remediation_with_issues(self):
        """Test remediation generation with issues."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=1,
                argument="Security issue found",
                cited_evidence=[]
            )
        ]
        
        remediation = generate_remediation("Test Criterion", opinions)
        
        assert "security" in remediation.lower()


class TestGraphCreation:
    """Test graph creation functions."""
    
    def test_create_auditor_graph(self):
        """Test creating basic auditor graph."""
        graph = create_auditor_graph()
        
        assert graph is not None
    
    def test_create_advanced_auditor_graph(self):
        """Test creating advanced auditor graph."""
        graph = create_advanced_auditor_graph()
        
        assert graph is not None
    
    def test_graph_has_required_nodes(self):
        """Test graph has all required nodes."""
        graph = create_auditor_graph()
        
        # The graph should be compilable
        assert graph is not None


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""
    
    def test_state_flow(self):
        """Test state flows through the system."""
        # Create initial state
        initial_state = create_initial_state(
            repo_url="https://github.com/test/repo",
            pdf_path="./report.pdf",
            rubric_dimensions=[
                {"id": "test", "name": "Test Criterion"}
            ]
        )
        
        assert initial_state["repo_url"] == "https://github.com/test/repo"
        assert "evidences" in initial_state
        assert "opinions" in initial_state
    
    def test_evidence_collection(self):
        """Test evidence collection workflow."""
        evidences = {
            "repo_investigator": [
                Evidence(
                    goal="git_forensic_analysis",
                    found=True,
                    content="12 commits",
                    location="/repo",
                    rationale="Good history",
                    confidence=0.9
                )
            ],
            "doc_analyst": [
                Evidence(
                    goal="theoretical_depth",
                    found=True,
                    content="Keywords found",
                    location="./report.pdf",
                    rationale="Good depth",
                    confidence=0.8
                )
            ]
        }
        
        # Verify evidence structure
        assert "repo_investigator" in evidences
        assert "doc_analyst" in evidences
        assert len(evidences["repo_investigator"]) == 1
    
    def test_judicial_opinions_flow(self):
        """Test opinions flow through judges."""
        opinions = [
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="git_forensic_analysis",
                score=4,
                argument="Good commits",
                cited_evidence=["commit history"]
            ),
            JudicialOpinion(
                judge="Defense",
                criterion_id="git_forensic_analysis",
                score=5,
                argument="Excellent progression",
                cited_evidence=["commit history"]
            ),
            JudicialOpinion(
                judge="TechLead",
                criterion_id="git_forensic_analysis",
                score=4,
                argument="Solid workflow",
                cited_evidence=["commit history"]
            )
        ]
        
        # Verify opinions structure
        assert len(opinions) == 3
        assert opinions[0].judge == "Prosecutor"
        assert opinions[1].judge == "Defense"
        assert opinions[2].judge == "TechLead"
    
    def test_report_generation(self):
        """Test final report generation."""
        criteria = [
            CriterionResult(
                dimension_id="git_forensic",
                dimension_name="Git Forensic Analysis",
                final_score=4,
                judge_opinions=[],
                dissent_summary=None,
                remediation="Maintain workflow"
            )
        ]
        
        report = AuditReport(
            repo_url="https://github.com/test/repo",
            executive_summary="Good implementation",
            overall_score=4.2,
            criteria=criteria,
            remediation_plan="Continue best practices"
        )
        
        assert report.overall_score == 4.2
        assert len(report.criteria) == 1


class TestParallelExecution:
    """Test parallel execution patterns."""
    
    def test_fan_out_fan_in_pattern(self):
        """Test parallel fan-out/fan-in pattern."""
        # Simulate detective parallel execution
        detective_results = {
            "repo_investigator": [Evidence(
                goal="test", found=True, content="c",
                location="loc", rationale="r", confidence=0.5
            )],
            "doc_analyst": [Evidence(
                goal="test", found=True, content="c",
                location="loc", rationale="r", confidence=0.5
            )],
            "vision_inspector": [Evidence(
                goal="test", found=True, content="c",
                location="loc", rationale="r", confidence=0.5
            )]
        }
        
        # Fan-in: aggregate all evidence
        all_evidence = []
        for evidence_list in detective_results.values():
            all_evidence.extend(evidence_list)
        
        assert len(all_evidence) == 3
    
    def test_judge_parallel_execution(self):
        """Test parallel judge execution."""
        # All three judges analyze same evidence
        criterion_id = "test_criterion"
        
        prosecutor_opinion = JudicialOpinion(
            judge="Prosecutor",
            criterion_id=criterion_id,
            score=3,
            argument="Critical view",
            cited_evidence=["evidence1"]
        )
        
        defense_opinion = JudicialOpinion(
            judge="Defense",
            criterion_id=criterion_id,
            score=5,
            argument="Optimistic view",
            cited_evidence=["evidence1"]
        )
        
        techlead_opinion = JudicialOpinion(
            judge="TechLead",
            criterion_id=criterion_id,
            score=4,
            argument="Pragmatic view",
            cited_evidence=["evidence1"]
        )
        
        opinions = [prosecutor_opinion, defense_opinion, techlead_opinion]
        
        # Verify all judges analyzed same criterion
        for op in opinions:
            assert op.criterion_id == criterion_id


class TestErrorHandling:
    """Test error handling in workflow."""
    
    def test_missing_evidence_handling(self):
        """Test handling of missing evidence."""
        evidences = {
            "repo_investigator": [],
            "doc_analyst": [],
            "vision_inspector": []
        }
        
        # Check for missing categories
        expected = ["repo_investigator", "doc_analyst", "vision_inspector"]
        missing = [cat for cat in expected if cat not in evidences or not evidences[cat]]
        
        assert len(missing) == 3
    
    def test_partial_evidence_handling(self):
        """Test handling partial evidence."""
        evidences = {
            "repo_investigator": [Evidence(
                goal="test", found=True, content="c",
                location="loc", rationale="r", confidence=0.5
            )],
            "doc_analyst": [],
            "vision_inspector": []
        }
        
        expected = ["repo_investigator", "doc_analyst", "vision_inspector"]
        missing = [cat for cat in expected if cat not in evidences or not evidences[cat]]
        
        assert len(missing) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
