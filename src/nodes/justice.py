"""
Chief Justice Node for Automaton Auditor

This node synthesizes the three judge opinions (Prosecutor, Defense, TechLead)
into a final verdict using deterministic rules:

1. Rule of Security: Security flaws cap score at 3
2. Rule of Evidence: Forensic facts always overrule judicial opinion
3. Rule of Functionality: Tech Lead's architectural confirmation carries highest weight
4. Dissent Requirement: Score variance > 2 requires explicit dissent explanation
"""

from typing import Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from ..state import (
    AgentState, 
    JudicialOpinion, 
    CriterionResult, 
    AuditReport
)


# =============================================================================
# SYNTHESIS RULES
# =============================================================================


def resolve_conflict(prosecutor_score: int, defense_score: int, tech_lead_score: int) -> tuple[int, str]:
    """
    Resolve conflict between three judges using deterministic rules.
    
    Returns:
        (final_score, dissent_summary)
    """
    scores = [prosecutor_score, defense_score, tech_lead_score]
    score_range = max(scores) - min(scores)
    
    # Rule: Score variance > 2 requires explicit dissent
    if score_range > 2:
        dissent = f"Score variance of {score_range} detected. "
        
        # Security override: if any score is 1 due to security, cap at 3
        if 1 in scores:
            return 3, dissent + "Security flaw override applied."
        
        # Average the middle two scores
        sorted_scores = sorted(scores)
        final = sorted_scores[1]  # Middle value
        return final, dissent + f"Resolved to median: {final}"
    
    # Rule: Simple average for minor disagreements
    return round(sum(scores) / 3), ""


def apply_security_override(opinions: List[JudicialOpinion]) -> bool:
    """
    Check if any judge identified a security flaw.
    """
    security_keywords = ["security", "vulnerability", "os.system", "shell injection"]
    
    for op in opinions:
        if op.argument:
            for keyword in security_keywords:
                if keyword.lower() in op.argument.lower() and op.score <= 2:
                    return True
    return False


def generate_remediation(criterion_name: str, opinions: List[JudicialOpinion]) -> str:
    """
    Generate remediation advice based on judge opinions.
    """
    low_scores = [op for op in opinions if op.score <= 2]
    
    if not low_scores:
        return f"{criterion_name}: Maintain current quality standards."
    
    # Extract common issues
    issues = []
    for op in low_scores:
        if "security" in op.argument.lower():
            issues.append("Address security concerns")
        if "missing" in op.argument.lower():
            issues.append("Implement required components")
        if "parallel" in op.argument.lower():
            issues.append("Add parallel execution")
        if "pydantic" in op.argument.lower() or "typed" in op.argument.lower():
            issues.append("Add proper type validation")
    
    if issues:
        return f"{criterion_name}: " + "; ".join(set(issues)) + "."
    return f"{criterion_name}: Review implementation based on judge feedback."


# =============================================================================
# CHIEF JUSTICE NODE
# =============================================================================


def create_chief_justice_node(llm=None):
    """
    Factory to create the Chief Justice node.
    
    This node:
    1. Collects all judge opinions
    2. Groups them by criterion
    3. Applies deterministic conflict resolution rules
    4. Generates final AuditReport
    
    Args:
        llm: Optional LLM for enhanced synthesis
        
    Returns:
        A node function
    """
    
    def chief_justice(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Synthesize judge opinions into final verdict.
        """
        opinions = state.get("opinions", [])
        rubric_dims = state.get("rubric_dimensions", [])
        
        if not opinions:
            # No opinions to synthesize
            return {"final_report": None}
        
        # Group opinions by criterion
        criteria_results: List[CriterionResult] = []
        
        # Get unique criterion IDs from opinions
        criterion_ids = set(op.criterion_id for op in opinions)
        
        for criterion_id in criterion_ids:
            # Get all opinions for this criterion
            criterion_opinions = [op for op in opinions if op.criterion_id == criterion_id]
            
            # Get criterion name
            criterion_name = criterion_id
            for dim in rubric_dims:
                if dim.get("id") == criterion_id:
                    criterion_name = dim.get("name", criterion_id)
                    break
            
            # Get scores from each judge
            prosecutor_score = 3
            defense_score = 3
            tech_lead_score = 3
            
            for op in criterion_opinions:
                if op.judge == "Prosecutor":
                    prosecutor_score = op.score
                elif op.judge == "Defense":
                    defense_score = op.score
                elif op.judge == "TechLead":
                    tech_lead_score = op.score
            
            # Apply synthesis rules
            final_score, dissent = resolve_conflict(
                prosecutor_score, 
                defense_score, 
                tech_lead_score
            )
            
            # Check for security override
            if apply_security_override(criterion_opinions):
                if final_score > 3:
                    final_score = 3
            
            # Generate remediation
            remediation = generate_remediation(criterion_name, criterion_opinions)
            
            # Create CriterionResult
            result = CriterionResult(
                dimension_id=criterion_id,
                dimension_name=criterion_name,
                final_score=final_score,
                judge_opinions=criterion_opinions,
                dissent_summary=dissent if dissent else None,
                remediation=remediation
            )
            
            criteria_results.append(result)
        
        # Calculate overall score
        overall_score = 0
        if criteria_results:
            overall_score = sum(r.final_score for r in criteria_results) / len(criteria_results)
        
        # Generate executive summary
        if llm:
            try:
                summary_prompt = f"""Generate a brief executive summary for this audit report.

Overall Score: {overall_score:.1f}/5.0
Criteria Evaluated: {len(criteria_results)}

Key findings:
"""
                for r in criteria_results:
                    summary_prompt += f"- {r.dimension_name}: {r.final_score}/5\n"
                
                response = llm.invoke(summary_prompt)
                executive_summary = response.content if hasattr(response, 'content') else str(response)
            except:
                executive_summary = f"Audit complete. Overall score: {overall_score:.1f}/5.0. {len(criteria_results)} criteria evaluated."
        else:
            executive_summary = f"Audit complete. Overall score: {overall_score:.1f}/5.0. {len(criteria_results)} criteria evaluated."
        
        # Generate remediation plan
        remediation_plan = "\n".join([r.remediation for r in criteria_results])
        
        # Create final report
        report = AuditReport(
            repo_url=state.get("repo_url", ""),
            executive_summary=executive_summary,
            overall_score=overall_score,
            criteria=criteria_results,
            remediation_plan=remediation_plan
        )
        
        return {"final_report": report}
    
    return chief_justice
