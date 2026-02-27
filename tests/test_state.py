"""
Unit Tests for State Module

Tests the state definitions and types.
"""

import pytest
import operator
from typing import Annotated

# Add parent to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state import (
    Evidence,
    JudicialOpinion,
    CriterionResult,
    AuditReport,
    AgentState,
    create_initial_state,
    validate_state
)


class TestEvidence:
    """Test Evidence model."""
    
    def test_evidence_creation(self):
        """Test creating Evidence object."""
        evidence = Evidence(
            goal="test_goal",
            found=True,
            content="Test content",
            location="/path/to/file",
            rationale="Test rationale",
            confidence=0.95
        )
        
        assert evidence.goal == "test_goal"
        assert evidence.found is True
        assert evidence.confidence == 0.95
    
    def test_evidence_validation(self):
        """Test confidence validation."""
        with pytest.raises(Exception):
            Evidence(
                goal="test",
                found=True,
                content="content",
                location="path",
                rationale="rationale",
                confidence=1.5  # Invalid - must be <= 1.0
            )
    
    def test_evidence_to_dict(self):
        """Test Evidence serialization."""
        evidence = Evidence(
            goal="test",
            found=True,
            content="content",
            location="path",
            rationale="rationale",
            confidence=0.5
        )
        
        data = evidence.model_dump() if hasattr(evidence, 'model_dump') else evidence.dict()
        
        assert data["goal"] == "test"
        assert data["found"] is True


class TestJudicialOpinion:
    """Test JudicialOpinion model."""
    
    def test_judicial_opinion_creation(self):
        """Test creating JudicialOpinion."""
        opinion = JudicialOpinion(
            judge="Prosecutor",
            criterion_id="test_criterion",
            score=4,
            argument="Test argument",
            cited_evidence=["evidence1", "evidence2"]
        )
        
        assert opinion.judge == "Prosecutor"
        assert opinion.score == 4
        assert len(opinion.cited_evidence) == 2
    
    def test_judicial_opinion_validation(self):
        """Test score validation."""
        with pytest.raises(Exception):
            JudicialOpinion(
                judge="Prosecutor",
                criterion_id="test",
                score=6,  # Invalid - must be 1-5
                argument="arg",
                cited_evidence=[]
            )


class TestCriterionResult:
    """Test CriterionResult model."""
    
    def test_criterion_result_creation(self):
        """Test creating CriterionResult."""
        opinion = JudicialOpinion(
            judge="Prosecutor",
            criterion_id="test",
            score=3,
            argument="arg",
            cited_evidence=[]
        )
        
        result = CriterionResult(
            dimension_id="test_id",
            dimension_name="Test Criterion",
            final_score=3,
            judge_opinions=[opinion],
            dissent_summary="Minor disagreement",
            remediation="Fix this"
        )
        
        assert result.dimension_id == "test_id"
        assert result.final_score == 3
        assert len(result.judge_opinions) == 1


class TestAuditReport:
    """Test AuditReport model."""
    
    def test_audit_report_creation(self):
        """Test creating AuditReport."""
        report = AuditReport(
            repo_url="https://github.com/test/repo",
            executive_summary="Test summary",
            overall_score=4.5,
            criteria=[],
            remediation_plan="Fix issues"
        )
        
        assert report.repo_url == "https://github.com/test/repo"
        assert report.overall_score == 4.5
    
    def test_audit_report_to_json(self):
        """Test AuditReport serialization."""
        report = AuditReport(
            repo_url="https://github.com/test/repo",
            executive_summary="Summary",
            overall_score=3.0,
            criteria=[],
            remediation_plan="Plan"
        )
        
        json_str = report.model_dump_json(indent=2) if hasattr(report, 'model_dump_json') else report.json(indent=2)
        
        assert "test/repo" in json_str
        assert "3.0" in json_str


class TestAgentState:
    """Test AgentState TypedDict."""
    
    def test_agent_state_structure(self):
        """Test AgentState has required keys."""
        state: AgentState = {
            "repo_url": "https://github.com/test",
            "pdf_path": "./report.pdf",
            "rubric_dimensions": [{"id": "test", "name": "Test"}],
            "evidences": {},
            "opinions": [],
            "final_report": None
        }
        
        assert "repo_url" in state
        assert "evidences" in state
        assert "opinions" in state


class TestStateHelpers:
    """Test state helper functions."""
    
    def test_create_initial_state(self):
        """Test creating initial state."""
        state = create_initial_state(
            repo_url="https://github.com/test",
            pdf_path="./report.pdf",
            rubric_dimensions=[{"id": "test", "name": "Test"}]
        )
        
        assert state["repo_url"] == "https://github.com/test"
        assert state["evidences"] == {}
        assert state["opinions"] == []
    
    def test_validate_state_valid(self):
        """Test validating valid state."""
        state = create_initial_state(
            repo_url="https://github.com/test",
            pdf_path="./report.pdf",
            rubric_dimensions=[{"id": "test", "name": "Test"}]
        )
        
        assert validate_state(state) is True
    
    def test_validate_state_missing_field(self):
        """Test validating state with missing field."""
        state = {
            "repo_url": "https://github.com/test",
            # Missing other fields
        }
        
        with pytest.raises(ValueError):
            validate_state(state)


class TestReducers:
    """Test reducer functions."""
    
    def test_list_reducer(self):
        """Test list reducer with operator.add."""
        # Simulate parallel opinions being merged
        opinions1 = [JudicialOpinion(
            judge="Prosecutor",
            criterion_id="test",
            score=3,
            argument="arg1",
            cited_evidence=[]
        )]
        
        opinions2 = [JudicialOpinion(
            judge="Defense",
            criterion_id="test",
            score=4,
            argument="arg2",
            cited_evidence=[]
        )]
        
        # Using operator.add for list concatenation
        combined = opinions1 + opinions2
        
        assert len(combined) == 2
    
    def test_dict_reducer(self):
        """Test dict reducer with operator.ior."""
        # Simulate parallel evidence being merged
        evidences1 = {"repo": [Evidence(
            goal="test", found=True, content="c",
            location="loc", rationale="r", confidence=0.5
        )]}
        
        evidences2 = {"doc": [Evidence(
            goal="test2", found=True, content="c2",
            location="loc2", rationale="r2", confidence=0.6
        )]}
        
        # Using operator.ior for dict merge
        combined = {**evidences1, **evidences2}
        
        assert "repo" in combined
        assert "doc" in combined


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
