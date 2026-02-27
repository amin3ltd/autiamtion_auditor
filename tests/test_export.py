"""
Unit Tests for Export Utilities

Tests the export functionality for different formats.
"""

import pytest
import tempfile
import json
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.export_utils import (
    export_to_markdown,
    export_to_text,
    export_to_json,
    generate_video_script,
    generate_html_report,
    save_export
)
from src.state import (
    Evidence,
    JudicialOpinion,
    CriterionResult,
    AuditReport
)


@pytest.fixture
def sample_evidence():
    """Create sample evidence for testing."""
    return {
        "repo_investigator": [
            Evidence(
                goal="git_forensic_analysis",
                found=True,
                content="12 commits found",
                location="/repo",
                rationale="Good progression",
                confidence=0.95
            )
        ],
        "doc_analyst": [
            Evidence(
                goal="theoretical_depth",
                found=True,
                content="Keywords: Dialectical Synthesis",
                location="./report.pdf",
                rationale="Deep understanding",
                confidence=0.85
            )
        ]
    }


@pytest.fixture
def sample_opinions():
    """Create sample opinions for testing."""
    return [
        JudicialOpinion(
            judge="Prosecutor",
            criterion_id="git_forensic_analysis",
            score=4,
            argument="Good commit history",
            cited_evidence=["git log"]
        ),
        JudicialOpinion(
            judge="Defense",
            criterion_id="git_forensic_analysis",
            score=5,
            argument="Excellent progression",
            cited_evidence=["git log"]
        ),
        JudicialOpinion(
            judge="TechLead",
            criterion_id="git_forensic_analysis",
            score=4,
            argument="Solid workflow",
            cited_evidence=["git log"]
        )
    ]


@pytest.fixture
def sample_report():
    """Create sample report for testing."""
    return AuditReport(
        repo_url="https://github.com/test/repo",
        executive_summary="Good implementation with minor improvements needed.",
        overall_score=4.2,
        criteria=[
            CriterionResult(
                dimension_id="git_forensic_analysis",
                dimension_name="Git Forensic Analysis",
                final_score=4,
                judge_opinions=[],
                dissent_summary=None,
                remediation="Maintain current workflow"
            )
        ],
        remediation_plan="1. Continue best practices\n2. Add more tests"
    )


class TestMarkdownExport:
    """Test Markdown export functionality."""
    
    def test_export_to_markdown(self, sample_report, sample_evidence, sample_opinions):
        """Test Markdown export."""
        md = export_to_markdown(sample_report, sample_evidence, sample_opinions)
        
        assert "Automaton Auditor Report" in md
        assert "github.com" in md
        assert "4.2" in md
        assert "Executive Summary" in md
    
    def test_markdown_has_sections(self, sample_report, sample_evidence, sample_opinions):
        """Test Markdown has required sections."""
        md = export_to_markdown(sample_report, sample_evidence, sample_opinions)
        
        assert "##" in md  # Section headers
        assert "Score Overview" in md
        assert "Detailed Analysis" in md


class TestTextExport:
    """Test text export functionality."""
    
    def test_export_to_text(self, sample_report, sample_evidence, sample_opinions):
        """Test text export."""
        text = export_to_text(sample_report, sample_evidence, sample_opinions)
        
        assert "AUTOMATON AUDITOR REPORT" in text
        assert "Repository:" in text
        assert "Score:" in text
    
    def test_text_format(self, sample_report, sample_evidence, sample_opinions):
        """Test text format."""
        text = export_to_text(sample_report, sample_evidence, sample_opinions)
        
        assert "=" * 40 in text  # Section separators


class TestJSONExport:
    """Test JSON export functionality."""
    
    def test_export_to_json(self, sample_report, sample_evidence, sample_opinions):
        """Test JSON export."""
        json_str = export_to_json(sample_report, sample_evidence, sample_opinions)
        
        # Should be valid JSON
        data = json.loads(json_str)
        
        assert "metadata" in data
        assert "report" in data
        assert "evidences" in data
        assert "opinions" in data
    
    def test_json_metadata(self, sample_report, sample_evidence, sample_opinions):
        """Test JSON metadata."""
        json_str = export_to_json(sample_report, sample_evidence, sample_opinions)
        
        data = json.loads(json_str)
        
        assert data["metadata"]["repo_url"] == "https://github.com/test/repo"
        assert data["metadata"]["overall_score"] == 4.2


class TestVideoScript:
    """Test video script generation."""
    
    def test_generate_video_script(self, sample_report, sample_evidence, sample_opinions):
        """Test video script generation."""
        script = generate_video_script(sample_report, sample_evidence, sample_opinions)
        
        assert "AUTOMATON AUDITOR" in script
        assert "INTRO" in script
        assert "OVERVIEW" in script
        assert "SYSTEM ARCHITECTURE" in script
    
    def test_video_script_has_sections(self, sample_report, sample_evidence, sample_opinions):
        """Test video script has required sections."""
        script = generate_video_script(sample_report, sample_evidence, sample_opinions)
        
        assert "EVIDENCE COLLECTION" in script
        assert "JUDGE DELIBERATIONS" in script
        assert "FINAL VERDICT" in script
        assert "REMEDIATION" in script


class TestHTMLReport:
    """Test HTML report generation."""
    
    def test_generate_html_report(self, sample_report, sample_evidence, sample_opinions):
        """Test HTML report generation."""
        html = generate_html_report(sample_report, sample_evidence, sample_opinions)
        
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "Automaton Auditor Report" in html
    
    def test_html_has_styling(self, sample_report, sample_evidence, sample_opinions):
        """Test HTML has styling."""
        html = generate_html_report(sample_report, sample_evidence, sample_opinions)
        
        assert "<style>" in html
        assert ".score-" in html
        assert ".judge-" in html


class TestSaveExport:
    """Test save export functionality."""
    
    def test_save_markdown(self, sample_report, sample_evidence, sample_opinions):
        """Test saving Markdown export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = save_export(
                ["markdown"],
                tmpdir,
                sample_report,
                sample_evidence,
                sample_opinions
            )
            
            assert "markdown" in saved
            assert Path(saved["markdown"]).exists()
    
    def test_save_multiple_formats(self, sample_report, sample_evidence, sample_opinions):
        """Test saving multiple formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = save_export(
                ["markdown", "text", "json", "html"],
                tmpdir,
                sample_report,
                sample_evidence,
                sample_opinions
            )
            
            assert "markdown" in saved
            assert "text" in saved
            assert "json" in saved
            assert "html" in saved
            
            # Verify files exist
            for path in saved.values():
                assert Path(path).exists()
    
    def test_save_video_script(self, sample_report, sample_evidence, sample_opinions):
        """Test saving video script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = save_export(
                ["video"],
                tmpdir,
                sample_report,
                sample_evidence,
                sample_opinions
            )
            
            assert "video" in saved
            assert Path(saved["video"]).exists()
            
            # Verify content
            content = Path(saved["video"]).read_text()
            assert "AUTOMATON AUDITOR" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])