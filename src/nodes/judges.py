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

from langchain_core.runnables import RunnableConfig

from ..state import AgentState, Evidence, JudicialOpinion


# =============================================================================
# PROSECUTOR - The Critical Lens
# =============================================================================


PROSECUTOR_SYSTEM_PROMPT = """You are the Prosecutor in a digital courtroom.

Your core philosophy: "Trust No One. Assume Vibe Coding."

Your objective: Scrutinize the evidence for gaps, security flaws, and laziness.

Guidelines:
- If the rubric asks for "Parallel Orchestration" and evidence shows "Linear pipeline", argue for Score 1
- Look specifically for bypassed structure - if Judges return freeform text instead of Pydantic models, charge "Hallucination Liability"
- Provide harsh scores and specific missing elements
- Do NOT reward effort or intent - only look at what was actually delivered
- Security flaws should always result in the lowest possible score

You must output a JSON object with:
- judge: "Prosecutor"
- criterion_id: the dimension being evaluated
- score: 1-5 (1 is worst, 5 is best)
- argument: your reasoning for this score
- cited_evidence: list of evidence items you considered
"""


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
            
            # Create prompt for prosecutor
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
                # Use LLM with structured output
                from langchain_core.output_parsers import JsonOutputParser
                
                parser = JsonOutputParser()
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON response
                import json
                try:
                    result = json.loads(response_text)
                    opinions.append(JudicialOpinion(
                        judge="Prosecutor",
                        criterion_id=dim_id,
                        score=min(5, max(1, int(result.get("score", 3)))),
                        argument=result.get("argument", "No argument provided"),
                        cited_evidence=[e.location for e in dim_evidence]
                    ))
                except:
                    # Fallback: extract score from text
                    opinions.append(JudicialOpinion(
                        judge="Prosecutor",
                        criterion_id=dim_id,
                        score=3,
                        argument=f"Prosecutor review: {response_text[:200]}",
                        cited_evidence=[e.location for e in dim_evidence]
                    ))
                    
            except Exception as e:
                opinions.append(JudicialOpinion(
                    judge="Prosecutor",
                    criterion_id=dim_id,
                    score=3,
                    argument=f"Error in prosecution: {str(e)}",
                    cited_evidence=[e.location for e in dim_evidence]
                ))
        
        return {"opinions": opinions}
    
    return prosecutor


# =============================================================================
# DEFENSE ATTORNEY - The Optimistic Lens
# =============================================================================


DEFENSE_SYSTEM_PROMPT = """You are the Defense Attorney in a digital courtroom.

Your core philosophy: "Reward Effort and Intent. Look for the Spirit of the Law."

Your objective: Highlight creative workarounds, deep thought, and effort, even if the implementation is imperfect.

Guidelines:
- If the code is buggy but shows deep understanding of concepts, argue for a higher score
- Look at Git History - if commits tell a story of struggle and iteration, reward the engineering process
- Find the "good" in imperfect implementations
- Look for creative solutions even if they don't follow the exact pattern requested
- Focus on intent and learning

You must output a JSON object with:
- judge: "Defense"
- criterion_id: the dimension being evaluated
- score: 1-5 (1 is worst, 5 is best)
- argument: your reasoning for this score
- cited_evidence: list of evidence items you considered
"""


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
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                import json
                try:
                    result = json.loads(response_text)
                    opinions.append(JudicialOpinion(
                        judge="Defense",
                        criterion_id=dim_id,
                        score=min(5, max(1, int(result.get("score", 3)))),
                        argument=result.get("argument", "No argument provided"),
                        cited_evidence=[e.location for e in dim_evidence]
                    ))
                except:
                    opinions.append(JudicialOpinion(
                        judge="Defense",
                        criterion_id=dim_id,
                        score=3,
                        argument=f"Defense review: {response_text[:200]}",
                        cited_evidence=[e.location for e in dim_evidence]
                    ))
                    
            except Exception as e:
                opinions.append(JudicialOpinion(
                    judge="Defense",
                    criterion_id=dim_id,
                    score=3,
                    argument=f"Error in defense: {str(e)}",
                    cited_evidence=[e.location for e in dim_evidence]
                ))
        
        return {"opinions": opinions}
    
    return defense


# =============================================================================
# TECH LEAD - The Pragmatic Lens
# =============================================================================


TECH_LEAD_SYSTEM_PROMPT = """You are the Tech Lead in a digital courtroom.

Your core philosophy: "Does it actually work? Is it maintainable?"

Your objective: Evaluate architectural soundness, code cleanliness, and practical viability.

Guidelines:
- Focus on the Artifacts - is the code actually functional?
- Ignore the "vibe" and the "struggle"
- Is the operator.add reducer actually used to prevent data overwriting?
- Are tool calls isolated and safe?
- You are the tie-breaker - be practical, not emotional

You must output a JSON object with:
- judge: "TechLead"
- criterion_id: the dimension being evaluated
- score: 1-5 (1 is worst, 5 is best)
- argument: your reasoning for this score
- cited_evidence: list of evidence items you considered
"""


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
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                import json
                try:
                    result = json.loads(response_text)
                    opinions.append(JudicialOpinion(
                        judge="TechLead",
                        criterion_id=dim_id,
                        score=min(5, max(1, int(result.get("score", 3)))),
                        argument=result.get("argument", "No argument provided"),
                        cited_evidence=[e.location for e in dim_evidence]
                    ))
                except:
                    opinions.append(JudicialOpinion(
                        judge="TechLead",
                        criterion_id=dim_id,
                        score=3,
                        argument=f"Tech Lead review: {response_text[:200]}",
                        cited_evidence=[e.location for e in dim_evidence]
                    ))
                    
            except Exception as e:
                opinions.append(JudicialOpinion(
                    judge="TechLead",
                    criterion_id=dim_id,
                    score=3,
                    argument=f"Error in tech lead review: {str(e)}",
                    cited_evidence=[e.location for e in dim_evidence]
                ))
        
        return {"opinions": opinions}
    
    return tech_lead
