"""
Detective Nodes for Automaton Auditor

These agents perform forensic analysis without opinionation.
They collect structured evidence based on strict protocols.

Nodes:
- RepoInvestigator: Analyzes GitHub repositories (git history, AST)
- DocAnalyst: Analyzes PDF reports (cross-reference, keyword depth)
- VisionInspector: Analyzes diagrams (optional)
"""

import os
import tempfile
from typing import Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from ..state import AgentState, Evidence
from ..tools.repo_tools import (
    clone_repository,
    get_git_history,
    analyze_graph_structure,
    analyze_state_definitions,
    check_sandboxing,
    GitCloneError,
    GitAnalysisError,
)
from ..tools.doc_tools import (
    DocumentAnalyzer,
    PDFParseError,
)


# =============================================================================
# REPO INVESTIGATOR - The Code Detective
# =============================================================================


def create_repo_investigator_node(llm=None):
    """
    Factory to create a RepoInvestigator node.
    
    The node performs forensic analysis of GitHub repositories:
    - Git history analysis (commit patterns)
    - State management verification (Pydantic, TypedDict)
    - Graph structure verification (AST-based)
    - Security sandboxing verification
    
    Args:
        llm: Optional LLM for enhanced analysis
    
    Returns:
        A node function that takes AgentState and returns updated state
    """
    
    def repo_investigator(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Perform forensic analysis of the target repository.
        
        This node:
        1. Clones the repository (sandboxed)
        2. Analyzes git history
        3. Parses AST for graph structure
        4. Checks state definitions
        5. Verifies sandboxing
        
        Returns evidence dict to be merged into state.
        """
        repo_url = state["repo_url"]
        rubric_dims = state["rubric_dimensions"]
        
        evidence_list: List[Evidence] = []
        temp_repo_path = None
        
        try:
            # Step 1: Clone repository (sandboxed)
            temp_repo_path = clone_repository(repo_url)
            
            # Step 2: Git forensic analysis
            try:
                git_history = get_git_history(temp_repo_path)
                
                evidence_list.append(Evidence(
                    goal="git_forensic_analysis",
                    found=git_history.get("count", 0) > 0,
                    content=f"Commits: {git_history.get('count', 0)}. "
                            f"Progression: {git_history.get('progression_detected', False)}. "
                            f"Monolithic: {git_history.get('is_monolithic', True)}",
                    location=temp_repo_path,
                    rationale=f"Found {git_history.get('count', 0)} commits. "
                              f"{'Iterative development detected' if git_history.get('progression_detected') else 'Bulk upload pattern detected'}",
                    confidence=0.9 if git_history.get("count", 0) > 0 else 0.1
                ))
            except GitAnalysisError as e:
                evidence_list.append(Evidence(
                    goal="git_forensic_analysis",
                    found=False,
                    content=str(e),
                    location=repo_url,
                    rationale="Failed to extract git history",
                    confidence=0.0
                ))
            
            # Step 3: Graph structure analysis (AST-based)
            graph_analysis = analyze_graph_structure(temp_repo_path)
            
            evidence_list.append(Evidence(
                goal="graph_orchestration",
                found=graph_analysis.get("found", False),
                content=f"StateGraph: {graph_analysis.get('has_stategraph', False)}. "
                        f"Parallel Fan-out: {graph_analysis.get('has_parallel_fanout', False)}. "
                        f"Parallel Fan-in: {graph_analysis.get('has_parallel_fanin', False)}. "
                        f"Nodes: {graph_analysis.get('nodes', [])}. "
                        f"Edges: {graph_analysis.get('edges', [])}",
                location=graph_analysis.get("file", "unknown"),
                rationale="AST analysis of graph.py. "
                          f"{'Found parallel orchestration' if graph_analysis.get('has_parallel_fanout') else 'Linear or no parallel structure detected'}",
                confidence=0.8 if graph_analysis.get("found") else 0.1
            ))
            
            # Step 4: State definitions analysis
            state_analysis = analyze_state_definitions(temp_repo_path)
            
            evidence_list.append(Evidence(
                goal="state_management_rigor",
                found=state_analysis.get("found", False),
                content=f"Pydantic: {state_analysis.get('has_pydantic', False)}. "
                        f"TypedDict: {state_analysis.get('has_typeddict', False)}. "
                        f"Reducers: {state_analysis.get('has_reducers', False)}. "
                        f"Evidence Model: {state_analysis.get('has_evidence_model', False)}. "
                        f"JudicialOpinion Model: {state_analysis.get('has_judicial_opinion_model', False)}",
                location=state_analysis.get("file", "unknown"),
                rationale="AST analysis of state definitions. "
                          f"{'Pydantic models with reducers found' if state_analysis.get('has_reducers') else 'Plain dicts or missing reducers'}",
                confidence=0.8 if state_analysis.get("found") else 0.1
            ))
            
            # Step 5: Security sandboxing check
            sandbox_analysis = check_sandboxing(temp_repo_path)
            
            evidence_list.append(Evidence(
                goal="safe_tool_engineering",
                found=sandbox_analysis.get("found", False),
                content=f"Uses tempfile: {sandbox_analysis.get('uses_tempfile', False)}. "
                        f"Uses subprocess: {sandbox_analysis.get('uses_subprocess', False)}. "
                        f"Security issues: {sandbox_analysis.get('has_security_issues', True)}. "
                        f"Issues: {sandbox_analysis.get('issues', [])}",
                location=sandbox_analysis.get("tools_dir", "unknown"),
                rationale="Security analysis of tool implementations. "
                          f"{'Proper sandboxing detected' if sandbox_analysis.get('uses_tempfile') else 'No tempfile usage - potential security issue'}",
                confidence=0.8 if sandbox_analysis.get("found") else 0.1
            ))
            
            # Step 6: Structured output enforcement check
            # This requires checking for with_structured_output or bind_tools
            evidence_list.append(Evidence(
                goal="structured_output_enforcement",
                found=False,  # Will be analyzed via code search
                content="Analysis pending - requiresJudge node code inspection",
                location="src/nodes/judges.py",
                rationale="Deferred to judges layer for code inspection",
                confidence=0.5
            ))
            
        except GitCloneError as e:
            # Handle clone failure
            evidence_list.append(Evidence(
                goal="git_forensic_analysis",
                found=False,
                content=f"Clone failed: {str(e)}",
                location=repo_url,
                rationale="Could not access repository",
                confidence=0.0
            ))
        
        finally:
            # Cleanup temporary directory
            if temp_repo_path and os.path.exists(temp_repo_path):
                import shutil
                try:
                    shutil.rmtree(temp_repo_path, ignore_errors=True)
                except Exception:
                    pass
        
        # Return the evidence as a dict for reducer merge
        return {
            "evidences": {"repo_investigator": evidence_list}
        }
    
    return repo_investigator


# =============================================================================
# DOC ANALYST - The Paperwork Detective
# =============================================================================


def create_doc_analyst_node(llm=None):
    """
    Factory to create a DocAnalyst node.
    
    Performs forensic analysis of PDF reports:
    - Keyword depth (buzzword vs substantive)
    - Cross-reference verification
    - Claim validation
    
    Args:
        llm: Optional LLM for enhanced analysis
    
    Returns:
        A node function
    """
    
    def doc_analyst(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Analyze the PDF report for accuracy and depth.
        """
        pdf_path = state["pdf_path"]
        evidence_list: List[Evidence] = []
        
        try:
            analyzer = DocumentAnalyzer(pdf_path)
            analyzer.load()
            
            # Check theoretical depth (keyword analysis)
            keywords = [
                "Dialectical Synthesis",
                "Fan-In",
                "Fan-Out", 
                "Metacognition",
                "State Synchronization"
            ]
            
            keyword_analysis = analyzer.check_keyword_depth(keywords)
            
            # Summarize findings
            buzzwords = [
                k for k, v in keyword_analysis.items() 
                if v.get("is_buzzword", False)
            ]
            substantive = [
                k for k, v in keyword_analysis.items() 
                if v.get("found") and not v.get("is_buzzword")
            ]
            
            evidence_list.append(Evidence(
                goal="theoretical_depth",
                found=len(substantive) > 0,
                content=f"Keywords analyzed: {list(keyword_analysis.keys())}. "
                        f"Substantive: {substantive}. "
                        f"Buzzwords: {buzzwords}",
                location=pdf_path,
                rationale=f"Found {len(substantive)} keywords with substance, "
                          f"{len(buzzwords)} appear to be buzzwords",
                confidence=0.7 if keyword_analysis else 0.1
            ))
            
            # Check report accuracy (cross-reference)
            claims = analyzer.extract_claims()
            
            # Note: We can't verify against repo without having cloned it
            # This would need to be done in coordination with RepoInvestigator
            evidence_list.append(Evidence(
                goal="report_accuracy",
                found=len(claims) > 0,
                content=f"Total claims extracted: {len(claims)}. "
                        f"Sample claims: {[c.get('claim', '')[:100] for c in claims[:3]]}",
                location=pdf_path,
                rationale=f"Extracted {len(claims)} implementation claims from report. "
                          f"Cross-reference verification requires repo access.",
                confidence=0.6
            ))
            
        except PDFParseError as e:
            evidence_list.append(Evidence(
                goal="report_accuracy",
                found=False,
                content=f"PDF parse error: {str(e)}",
                location=pdf_path,
                rationale="Could not parse PDF document",
                confidence=0.0
            ))
        
        return {
            "evidences": {"doc_analyst": evidence_list}
        }
    
    return doc_analyst


# =============================================================================
# VISION INSPECTOR - The Diagram Detective (Optional)
# =============================================================================


def create_vision_inspector_node(vision_llm=None):
    """
    Factory to create a VisionInspector node.
    
    Analyzes diagrams extracted from PDFs to verify:
    - Correct StateGraph visualization
    - Parallel flow representation
    - Swarm architecture depiction
    
    Note: This is optional for the interim submission.
    Execution requires a vision-capable LLM.
    
    Args:
        vision_llm: A vision-capable LLM (e.g., GPT-4V, Gemini Pro Vision)
    
    Returns:
        A node function
    """
    
    def vision_inspector(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Analyze diagrams in the PDF report.
        """
        pdf_path = state["pdf_path"]
        evidence_list: List[Evidence] = []
        
        if vision_llm is None:
            # Return placeholder - optional feature
            evidence_list.append(Evidence(
                goal="swarm_visual",
                found=False,
                content="VisionInspector not implemented - requires vision LLM",
                location=pdf_path,
                rationale="Optional feature - no vision LLM configured",
                confidence=0.0
            ))
            return {
                "evidences": {"vision_inspector": evidence_list}
            }
        
        try:
            from ..tools.doc_tools import extract_images_from_pdf
            
            images = extract_images_from_pdf(pdf_path)
            
            if not images:
                evidence_list.append(Evidence(
                    goal="swarm_visual",
                    found=False,
                    content="No images found in PDF",
                    location=pdf_path,
                    rationale="PDF contains no extractable images",
                    confidence=0.3
                ))
            else:
                # Would use vision LLM to analyze each image
                # This is a placeholder for the actual implementation
                evidence_list.append(Evidence(
                    goal="swarm_visual",
                    found=True,
                    content=f"Found {len(images)} images - vision analysis pending",
                    location=pdf_path,
                    rationale=f"Images extracted but not yet analyzed with vision LLM",
                    confidence=0.5
                ))
        
        except Exception as e:
            evidence_list.append(Evidence(
                goal="swarm_visual",
                found=False,
                content=f"Error: {str(e)}",
                location=pdf_path,
                rationale="Failed to analyze diagrams",
                confidence=0.0
            ))
        
        return {
            "evidences": {"vision_inspector": evidence_list}
        }
    
    return vision_inspector


# =============================================================================
# EVIDENCE AGGREGATOR - Fan-in Node
# =============================================================================


def create_evidence_aggregator_node():
    """
    Create the evidence aggregator node.
    
    This is the fan-in node that collects all evidence from
    parallel detective branches before passing to judges.
    
    It performs:
    - Validation of collected evidence
    - Formatting for judge consumption
    - Error handling for missing evidence
    """
    
    def evidence_aggregator(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Aggregate and validate evidence from all detectives.
        """
        evidences = state.get("evidences", {})
        
        # Flatten all evidence into a single list for judges
        all_evidence = []
        for detective_name, evidence_list in evidences.items():
            if evidence_list:
                all_evidence.extend(evidence_list)
        
        # Check for missing evidence categories
        expected_categories = [
            "repo_investigator",
            "doc_analyst",
            "vision_inspector"
        ]
        
        missing = [
            cat for cat in expected_categories 
            if cat not in evidences or not evidences[cat]
        ]
        
        # Log aggregation summary
        summary = {
            "total_evidence": len(all_evidence),
            "by_detective": {
                cat: len(evidences.get(cat, []))
                for cat in expected_categories
            },
            "missing_categories": missing
        }
        
        # Return empty dict - the state already has the evidences
        # This node is primarily for validation and logging
        return {
            # Could add aggregated data here if needed
        }
    
    return evidence_aggregator
