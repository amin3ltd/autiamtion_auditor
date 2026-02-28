"""
Judge Nodes for Automaton Auditor

These nodes implement the three distinct judge personas:
- Prosecutor: Critical lens (looks for flaws, security issues)
- Defense: Optimistic lens (rewards effort, creative workarounds)
- Tech Lead: Pragmatic lens (evaluates architectural soundness)

Each judge analyzes the same evidence and produces a JudicialOpinion
with a score (1-5), argument, and cited evidence.
"""

from typing import Dict, List, Optional
import json
import re
import logging

from langchain_core.runnables import RunnableConfig

from ..state import AgentState, Evidence, JudicialOpinion

# Set up logging
logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> dict:
    """
    Extract and parse JSON from LLM response, handling malformed JSON.
    
    This handles cases where:
    - JSON is truncated
    - Extra text surrounds the JSON
    - JSON has formatting issues (extra commas, etc.)
    """
    if not response_text:
        raise ValueError("Empty response text")
    
    # Try direct JSON parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks (with json specifier)
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to extract JSON from plain markdown code blocks
    json_match = re.search(r'```\s*([\s\S]*?)\s*```', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in the response - more aggressive pattern
    # Find all potential JSON start positions
    json_start_positions = [m.start() for m in re.finditer(r'\{', response_text)]
    
    for json_start in json_start_positions:
        # Find the last complete-looking structure from this position
        brace_count = 0
        in_string = False
        last_valid = json_start
        
        for i in range(json_start, len(response_text)):
            char = response_text[i]
            
            # Handle escaped characters in strings
            if in_string and char == '\\' and i + 1 < len(response_text):
                i += 1  # Skip escaped character
                continue
            
            if char == '"' and (i == 0 or response_text[i-1] != '\\'):
                in_string = not in_string
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        last_valid = i + 1
                        break
        
        # Try to parse this candidate
        candidate = response_text[json_start:last_valid]
        try:
            result = json.loads(candidate)
            # Verify it has expected fields
            if "score" in result:
                return result
        except json.JSONDecodeError:
            continue
    
    # Last resort: try to fix common JSON issues
    # Remove trailing commas, fix missing quotes, etc.
    fixed = response_text.strip()
    
    # Try finding JSON-like structure with just key-value pairs
    # This handles cases where LLM returns partial JSON
    json_match = re.search(r'"([^"]+)"\s*:\s*"?([^",\}]+)"?', response_text)
    if json_match:
        # Try to extract score and argument at minimum
        score_match = re.search(r'"score"\s*:\s*(\d+)', response_text)
        argument_match = re.search(r'"argument"\s*:\s*"([^"]*)"', response_text)
        
        if score_match:
            return {
                "score": int(score_match.group(1)),
                "argument": argument_match.group(1) if argument_match else "Extracted from response",
                "judge": "",
                "criterion_id": "",
                "cited_evidence": []
            }
    
    raise ValueError(f"Could not parse JSON from response: {response_text[:200]}")


# =============================================================================
# PROSECUTOR - The Critical Lens
# =============================================================================


def create_prosecutor_node(llm=None):
    """
    Factory to create the Prosecutor judge node.
    
    Args:
        llm: LLM for generating opinions
        
    Returns:
        A node function
    """
    
    def prosecutor(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Evaluate evidence as the Prosecutor (critical lens).
        """
        if llm is None:
            # No LLM - return placeholder
            return {"opinions": []}
        
        evidences = state.get("evidences", {})
        rubric_dims = state.get("rubric_dimensions", [])
        
        opinions: List[JudicialOpinion] = []
        
        # Analyze each rubric dimension
        for dim in rubric_dims:
            dim_id = dim.get("id", "unknown")
            dim_name = dim.get("name", "Unknown")
            
            # Collect all evidence for this dimension
            dim_evidence = []
            for detective_name, evidence_list in evidences.items():
                for ev in evidence_list:
                    if dim_id in ev.goal or dim_name.lower() in ev.goal.lower():
                        dim_evidence.append(ev)
            
            if not dim_evidence:
                continue
            
            # Format evidence for prompt
            evidence_text = "\n".join([
                f"- {e.goal}: {e.content} (confidence: {e.confidence})"
                for e in dim_evidence
            ])
            
            prompt = f"""Evaluate the following evidence for criterion: {dim_name}

Evidence:
{evidence_text}

As the Prosecutor, provide your critical assessment. Look for:
- Security flaws
- Missing requirements
- Bypassed structure
- Hallucinations or fabrications

Output your verdict as JSON with score (1-5) and reasoning.
"""
            
            try:
                # Get LLM response and parse JSON manually
                # Note: with_structured_output() doesn't work well with LM Studio
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON from response
                result = extract_json_from_response(response_text)
                
                # Create JudicialOpinion from parsed JSON
                opinions.append(JudicialOpinion(
                    judge="Prosecutor",
                    criterion_id=dim_id,
                    score=min(5, max(1, round(float(result.get("score", 3))))),
                    argument=result.get("argument", response_text[:500]),
                    cited_evidence=[e.location for e in dim_evidence]
                ))
                
            except Exception as e:
                logger.warning(f"Prosecutor judge error for {dim_id}: {str(e)}")
                # Create a fallback opinion with error info
                opinions.append(JudicialOpinion(
                    judge="Prosecutor",
                    criterion_id=dim_id,
                    score=3,
                    argument=f"Error in prosecution: {str(e)[:200]}",
                    cited_evidence=[e.location for e in dim_evidence]
                ))
        
        return {"opinions": opinions}
    
    return prosecutor


# =============================================================================
# DEFENSE ATTORNEY - The Optimistic Lens
# =============================================================================


def create_defense_node(llm=None):
    """
    Factory to create the Defense Attorney judge node.
    
    Args:
        llm: LLM for generating opinions
        
    Returns:
        A node function
    """
    
    def defense(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Evaluate evidence as the Defense (optimistic lens).
        """
        if llm is None:
            return {"opinions": []}
        
        evidences = state.get("evidences", {})
        rubric_dims = state.get("rubric_dimensions", [])
        
        opinions: List[JudicialOpinion] = []
        
        for dim in rubric_dims:
            dim_id = dim.get("id", "unknown")
            dim_name = dim.get("name", "Unknown")
            
            dim_evidence = []
            for detective_name, evidence_list in evidences.items():
                for ev in evidence_list:
                    if dim_id in ev.goal or dim_name.lower() in ev.goal.lower():
                        dim_evidence.append(ev)
            
            if not dim_evidence:
                continue
            
            evidence_text = "\n".join([
                f"- {e.goal}: {e.content} (confidence: {e.confidence})"
                for e in dim_evidence
            ])
            
            prompt = f"""Evaluate the following evidence for criterion: {dim_name}

Evidence:
{evidence_text}

As the Defense Attorney, provide an optimistic assessment. Look for:
- Creative workarounds
- Deep understanding despite imperfections
- Effort and intent
- The "spirit of the law" even if letter was missed

Output your verdict as JSON with score (1-5) and reasoning.
"""
            
            try:
                # Get LLM response and parse JSON manually
                # Note: with_structured_output() doesn't work well with LM Studio
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON from response
                result = extract_json_from_response(response_text)
                
                # Create JudicialOpinion from parsed JSON
                opinions.append(JudicialOpinion(
                    judge="Defense",
                    criterion_id=dim_id,
                    score=min(5, max(1, round(float(result.get("score", 3))))),
                    argument=result.get("argument", response_text[:500]),
                    cited_evidence=[e.location for e in dim_evidence]
                ))
                
            except Exception as e:
                logger.warning(f"Defense judge error for {dim_id}: {str(e)}")
                # Create a fallback opinion with error info
                opinions.append(JudicialOpinion(
                    judge="Defense",
                    criterion_id=dim_id,
                    score=3,
                    argument=f"Error in defense: {str(e)[:200]}",
                    cited_evidence=[e.location for e in dim_evidence]
                ))
        
        return {"opinions": opinions}
    
    return defense


# =============================================================================
# TECH LEAD - The Pragmatic Lens
# =============================================================================


def create_tech_lead_node(llm=None):
    """
    Factory to create the Tech Lead judge node.
    
    Args:
        llm: LLM for generating opinions
        
    Returns:
        A node function
    """
    
    def tech_lead(
        state: AgentState,
        config: Optional[RunnableConfig] = None
    ) -> Dict:
        """
        Evaluate evidence as the Tech Lead (pragmatic lens).
        """
        if llm is None:
            return {"opinions": []}
        
        evidences = state.get("evidences", {})
        rubric_dims = state.get("rubric_dimensions", [])
        
        opinions: List[JudicialOpinion] = []
        
        for dim in rubric_dims:
            dim_id = dim.get("id", "unknown")
            dim_name = dim.get("name", "Unknown")
            
            dim_evidence = []
            for detective_name, evidence_list in evidences.items():
                for ev in evidence_list:
                    if dim_id in ev.goal or dim_name.lower() in ev.goal.lower():
                        dim_evidence.append(ev)
            
            if not dim_evidence:
                continue
            
            evidence_text = "\n".join([
                f"- {e.goal}: {e.content} (confidence: {e.confidence})"
                for e in dim_evidence
            ])
            
            prompt = f"""Evaluate the following evidence for criterion: {dim_name}

Evidence:
{evidence_text}

As the Tech Lead, provide a pragmatic assessment. Focus on:
- Does it actually work?
- Is it maintainable?
- Is the architecture sound?
- Would you want to maintain this code?

Output your verdict as JSON with score (1-5) and reasoning.
"""
            
            try:
                # Get LLM response and parse JSON manually
                # Note: with_structured_output() doesn't work well with LM Studio
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON from response
                result = extract_json_from_response(response_text)
                
                # Create JudicialOpinion from parsed JSON
                opinions.append(JudicialOpinion(
                    judge="TechLead",
                    criterion_id=dim_id,
                    score=min(5, max(1, round(float(result.get("score", 3))))),
                    argument=result.get("argument", response_text[:500]),
                    cited_evidence=[e.location for e in dim_evidence]
                ))
                
            except Exception as e:
                logger.warning(f"TechLead judge error for {dim_id}: {str(e)}")
                # Create a fallback opinion with error info
                opinions.append(JudicialOpinion(
                    judge="TechLead",
                    criterion_id=dim_id,
                    score=3,
                    argument=f"Error in tech lead review: {str(e)[:200]}",
                    cited_evidence=[e.location for e in dim_evidence]
                ))

        return {"opinions": opinions}
    
    return tech_lead


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = [
    "create_prosecutor_node",
    "create_defense_node",
    "create_tech_lead_node",
]
