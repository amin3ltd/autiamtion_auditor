"""
Automaton Auditor Dashboard - Professional Edition

A comprehensive Streamlit dashboard for the Automaton Auditor system.
Features:
- Multiple LLM provider support (LM Studio, OpenAI, Anthropic, Google, Ollama, etc.)
- Real-time audit progress tracking
- Professional metrics and visualizations
- Evidence and judge opinion visualization
- Export capabilities
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import json
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import asdict

# Import LLM providers
try:
    from src.llm_providers import (
        LLMProvider, 
        PROVIDER_CONFIGS, 
        create_llm, 
        check_provider_health,
        load_from_env
    )
    from src.state import (
        Evidence, 
        JudicialOpinion, 
        CriterionResult, 
        AuditReport,
        DEFAULT_RUBRIC
    )
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False


# =============================================================================
# STREAMLIT CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Automaton Auditor | Professional",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com',
        'Report a bug': 'https://github.com',
        'About': '# Automaton Auditor\nDigital Courtroom for Automated Code Quality Audits'
    }
)


# =============================================================================
# CUSTOM CSS FOR PROFESSIONAL APPEARANCE
# =============================================================================

st.markdown("""
<style>
    /* Main theme */
    .stApp {
        background: linear-gradient(to bottom, #0f172a, #1e293b);
    }
    
    /* Cards */
    .card {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid rgba(100, 116, 139, 0.3);
    }
    
    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
    }
    
    /* Progress stages */
    .stage-completed {
        background: rgba(34, 197, 94, 0.2);
        border-left: 4px solid #22c55e;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    
    .stage-active {
        background: rgba(251, 191, 36, 0.2);
        border-left: 4px solid #fbbf24;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    
    .stage-pending {
        background: rgba(71, 85, 105, 0.2);
        border-left: 4px solid #64748b;
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    
    /* Judge panels */
    .judge-prosecutor {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 8px;
        padding: 15px;
    }
    
    .judge-defense {
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 8px;
        padding: 15px;
    }
    
    .judge-techlead {
        background: rgba(168, 85, 247, 0.15);
        border: 1px solid rgba(168, 85, 247, 0.3);
        border-radius: 8px;
        padding: 15px;
    }
    
    /* Score badges */
    .score-5 { background: #22c55e; color: white; padding: 4px 12px; border-radius: 20px; }
    .score-4 { background: #84cc16; color: white; padding: 4px 12px; border-radius: 20px; }
    .score-3 { background: #eab308; color: white; padding: 4px 12px; border-radius: 20px; }
    .score-2 { background: #f97316; color: white; padding: 4px 12px; border-radius: 20px; }
    .score-1 { background: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR - LLM PROVIDER CONFIGURATION
# =============================================================================

def render_provider_sidebar():
    """Render the LLM provider configuration sidebar."""
    with st.sidebar:
        st.title("⚙️ Configuration")
        st.markdown("---")
        
        # Provider selection
        st.subheader("🧠 LLM Provider")
        
        if not IMPORTS_OK:
            st.error("⚠️ Import error. Check dependencies.")
            return None
        
        # Get available providers
        providers = list(LLMProvider)
        provider_options = {p.value: PROVIDER_CONFIGS[p].name for p in providers}
        
        selected_provider = st.selectbox(
            "Select Provider",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            help="Choose the LLM provider for analysis"
        )
        
        config = PROVIDER_CONFIGS[LLMProvider(selected_provider)]
        
        # Provider-specific configuration
        st.markdown("### Provider Settings")
        
        # Check provider health for local providers
        if selected_provider in ["lm_studio", "ollama"]:
            health = check_provider_health(LLMProvider(selected_provider))
            if health["available"]:
                st.success(f"✅ {health['message']}")
                if "models" in health:
                    model_options = health["models"]
            else:
                st.warning(f"⚠️ {health['message']}")
                model_options = config.models
        else:
            model_options = config.models
        
        # Model selection
        model = st.selectbox(
            "Model",
            options=model_options,
            index=0,
            help="Select the model to use"
        )
        
        # API Key (for cloud providers)
        api_key = None
        if config.requires_api_key:
            api_key = st.text_input(
                "API Key",
                type="password",
                help=f"Required for {config.name}",
                value=os.getenv(f"{selected_provider.upper()}_API_KEY", "")
            )
        
        # Base URL (for local providers)
        base_url = None
        if config.requires_base_url:
            default_urls = {
                "lm_studio": "http://localhost:1234/v1",
                "ollama": "http://localhost:11434/v1"
            }
            base_url = st.text_input(
                "Base URL",
                value=default_urls.get(selected_provider, ""),
                help="Local server URL"
            )
        
        # Advanced parameters
        with st.expander("⚡ Advanced Parameters"):
            temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
            max_tokens = st.number_input("Max Tokens", 100, 32000, 4096, 100)
            streaming = st.checkbox("Enable Streaming", value=False)
        
        # Create LLM button
        create_llm_btn = st.button("🔗 Connect to LLM", type="primary")
        
        llm = None
        if create_llm_btn:
            try:
                llm = create_llm(
                    provider=LLMProvider(selected_provider),
                    model=model,
                    api_key=api_key or None,
                    base_url=base_url or None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=streaming
                )
                st.success("✅ Connected successfully!")
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")
        
        st.markdown("---")
        
        # Demo mode
        st.subheader("🎭 Demo Mode")
        demo_mode = st.checkbox(
            "Enable Demo Mode", 
            value=True,
            help="Run with sample data (no LLM required)"
        )
        
        st.markdown("---")
        
        # Audit history
        st.subheader("📊 Recent Audits")
        
        if "audit_history" not in st.session_state:
            st.session_state.audit_history = []
        
        for i, audit in enumerate(st.session_state.audit_history[-3:]):
            with st.container():
                st.markdown(f"**{audit['repo'][:30]}...**")
                st.caption(f"Score: {audit['score']:.1f} | {audit['time']}")
        
        return {
            "provider": selected_provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "llm": llm,
            "demo_mode": demo_mode
        }


# =============================================================================
# MAIN INPUT FORM
# =============================================================================

def render_main_input():
    """Render the main audit input form."""
    st.title("⚖️ Automaton Auditor")
    st.markdown("### Digital Courtroom for Automated Code Quality Audits")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        repo_url = st.text_input(
            "🔗 GitHub Repository URL",
            placeholder="https://github.com/username/repository",
            help="Enter the full URL of the GitHub repository to audit"
        )
        
        pdf_path = st.text_input(
            "📄 PDF Report Path",
            placeholder="./reports/auditor_report.pdf",
            help="Path to the PDF architectural report"
        )
    
    with col2:
        # Quick actions
        st.markdown("### Quick Actions")
        
        # Sample repos
        sample_repos = [
            ("10academy/Week2-Solution", "Week 2 Solution"),
            ("langchain-ai/langgraph", "LangGraph"),
            ("openai/openai-python", "OpenAI Python"),
        ]
        
        for repo, desc in sample_repos:
            if st.button(f"📋 {desc}", key=repo):
                repo_url = f"https://github.com/{repo}"
        
        # Available PDFs
        pdf_files = list(Path(".").glob("**/*.pdf"))
        if pdf_files:
            selected_pdf = st.selectbox(
                "Available Reports",
                [str(p) for p in pdf_files[:5]],
                index=0
            )
            if selected_pdf and not pdf_path:
                pdf_path = selected_pdf
    
    # Rubric selection
    with st.expander("📋 Evaluation Rubric"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Active Criteria:**")
            for dim in DEFAULT_RUBRIC[:5]:
                st.checkbox(dim["name"], value=True, key=dim["id"])
        
        with col2:
            st.markdown("**Additional Criteria:**")
            for dim in DEFAULT_RUBRIC[5:]:
                st.checkbox(dim["name"], value=True, key=dim["id"])
    
    # Submit button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        start_audit = st.button(
            "🚀 Start Audit",
            type="primary",
            use_container_width=True,
            disabled=not (repo_url and pdf_path)
        )
    
    return repo_url, pdf_path, start_audit


# =============================================================================
# PROGRESS VISUALIZATION
# =============================================================================

def render_audit_progress(stage: str, description: str, status: str):
    """Render a progress stage with status indicator."""
    if status == "completed":
        icon = "✅"
        cls = "stage-completed"
    elif status == "active":
        icon = "⏳"
        cls = "stage-active"
    else:
        icon = "⭕"
        cls = "stage-pending"
    
    st.markdown(f"""
    <div class="{cls}">
        <h4>{icon} {stage}</h4>
        <p>{description}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if status == "active":
        st.progress(50, text="Processing...")
    elif status == "completed":
        st.progress(100)


# =============================================================================
# EVIDENCE PANELS
# =============================================================================

def render_evidence_panel(evidences: Dict[str, List[Evidence]]):
    """Render evidence from detectives."""
    st.header("🔍 Detective Evidence")
    
    if not evidences:
        st.warning("No evidence collected.")
        return
    
    # Create tabs
    tabs = st.tabs([
        "📂 Repo Investigator", 
        "📄 Doc Analyst", 
        "👁️ Vision Inspector"
    ])
    
    detective_data = [
        ("repo_investigator", tabs[0]),
        ("doc_analyst", tabs[1]),
        ("vision_inspector", tabs[2])
    ]
    
    for det_name, tab in detective_data:
        with tab:
            evidence_list = evidences.get(det_name, [])
            
            if not evidence_list:
                st.info(f"No evidence from {det_name.replace('_', ' ').title()}")
                continue
            
            for ev in evidence_list:
                with st.expander(f"📌 {ev.goal.replace('_', ' ').title()}"):
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.metric("Found", "✅" if ev.found else "❌")
                        st.metric("Confidence", f"{ev.confidence:.0%}")
                    
                    with col2:
                        st.code(ev.content or "N/A", language="python")
                        st.caption(f"📍 {ev.location}")
                        st.caption(f"💭 {ev.rationale}")


# =============================================================================
# JUDGE DELIBERATION PANEL
# =============================================================================

def render_judge_panel(opinions: List[JudicialOpinion]):
    """Render judge opinions."""
    st.header("⚖️ Judge Deliberations")
    
    if not opinions:
        st.warning("No judge opinions yet.")
        return
    
    # Group by criterion
    criteria = set(op.criterion_id for op in opinions)
    
    for criterion_id in criteria:
        criterion_opinions = [op for op in opinions if op.criterion_id == criterion_id]
        
        with st.expander(f"📊 {criterion_id.replace('_', ' ').title()}", expanded=True):
            # Three columns for judges
            col1, col2, col3 = st.columns(3)
            
            judges = {
                "Prosecution": ("prosecutor", col1, "🔴"),
                "Defense": ("defense", col2, "🔵"),
                "Tech Lead": ("techlead", col3, "🟣")
            }
            
            for judge_name, (judge_key, col, icon) in judges.items():
                opinion = next((op for op in criterion_opinions if op.judge.lower() == judge_key), None)
                
                with col:
                    # Score badge
                    score_class = f"score-{opinion.score}" if opinion else "score-3"
                    score_html = f'<span class="{score_class}">{opinion.score}/5</span>' if opinion else "N/A"
                    st.markdown(f"**{icon} {judge_name}**")
                    st.markdown(f"Score: {score_html}", unsafe_allow_html=True)
                    
                    if opinion:
                        st.markdown(f"_{opinion.argument[:200]}_")
                        if len(opinion.argument) > 200:
                            st.markdown("...")
            
            # Cited evidence
            st.markdown("---")
            st.caption("📎 Cited Evidence:")
            all_evidence = []
            for op in criterion_opinions:
                all_evidence.extend(op.cited_evidence)
            st.caption(", ".join(set(all_evidence))[:200])


# =============================================================================
# FINAL REPORT PANEL
# =============================================================================

def render_report_panel(report: AuditReport):
    """Render final audit report."""
    st.header("🏛️ Final Verdict")
    
    if not report:
        st.warning("No report generated.")
        return
    
    # Executive summary
    st.subheader("📝 Executive Summary")
    st.markdown(report.executive_summary)
    
    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        grade = "A" if report.overall_score >= 4.5 else "B" if report.overall_score >= 3.5 else "C" if report.overall_score >= 2.5 else "D" if report.overall_score >= 1.5 else "F"
        st.metric("Overall Score", f"{report.overall_score:.1f}/5.0")
    
    with col2:
        st.metric("Grade", grade)
    
    with col3:
        st.metric("Criteria", len(report.criteria))
    
    with col4:
        criteria_passed = sum(1 for c in report.criteria if c.final_score >= 3)
        st.metric("Passed", f"{criteria_passed}/{len(report.criteria)}")
    
    # Score chart
    st.subheader("📈 Score Breakdown")
    
    df = pd.DataFrame([
        {"Criterion": c.dimension_name[:30], "Score": c.final_score}
        for c in report.criteria
    ])
    
    st.bar_chart(df.set_index("Criterion"), horizontal=True, color="#3b82f6")
    
    # Detailed results
    st.subheader("📋 Detailed Results")
    
    for criterion in report.criteria:
        with st.expander(f"{criterion.dimension_name} - {criterion.final_score}/5"):
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if criterion.final_score >= 4:
                    st.success(f"✅ Excellent: {criterion.final_score}/5")
                elif criterion.final_score >= 3:
                    st.warning(f"⚠️ Satisfactory: {criterion.final_score}/5")
                else:
                    st.error(f"❌ Needs Work: {criterion.final_score}/5")
            
            with col2:
                st.markdown(f"**Remediation:** {criterion.remediation}")
                
                if criterion.dissent_summary:
                    st.info(f"**Dissent:** {criterion.dissent_summary}")
    
    # Remediation plan
    st.subheader("🔧 Remediation Plan")
    st.code(report.remediation_plan, language="markdown")
    
    # Export
    st.download_button(
        "📥 Download Report (JSON)",
        data=report.model_dump_json(indent=2),
        file_name=f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


# =============================================================================
# DEMO DATA GENERATOR
# =============================================================================

def generate_demo_data():
    """Generate comprehensive demo data."""
    
    evidences = {
        "repo_investigator": [
            Evidence(
                goal="git_forensic_analysis",
                found=True,
                content="12 commits found. Progression: Setup → Tools → Graph → Judges → Synthesis",
                location="/tmp/demo_repo",
                rationale="Clear iterative development with meaningful commits.",
                confidence=0.95
            ),
            Evidence(
                goal="state_management_rigor",
                found=True,
                content="Pydantic: ✓ | TypedDict: ✓ | Reducers: ✓ | Evidence Model: ✓ | Opinion Model: ✓",
                location="src/state.py",
                rationale="Full Pydantic implementation with operator.add/ior reducers.",
                confidence=0.92
            ),
            Evidence(
                goal="graph_orchestration",
                found=True,
                content="StateGraph: ✓ | Fan-out: ✓ | Fan-in: ✓ | Nodes: [detectives, judges, chief_justice]",
                location="src/graph.py",
                rationale="Proper parallel execution with conditional edges.",
                confidence=0.88
            ),
            Evidence(
                goal="safe_tool_engineering",
                found=True,
                content="tempfile: ✓ | subprocess: ✓ | No os.system: ✓ | Error handling: ✓",
                location="src/tools/repo_tools.py",
                rationale="Production-ready security practices.",
                confidence=0.94
            ),
            Evidence(
                goal="structured_output_enforcement",
                found=True,
                content="with_structured_output: ✓ | Pydantic schemas: ✓ | Retry logic: ✓",
                location="src/nodes/judges.py",
                rationale="All judges use structured output.",
                confidence=0.90
            )
        ],
        "doc_analyst": [
            Evidence(
                goal="theoretical_depth",
                found=True,
                content="Keywords: Dialectical Synthesis, Fan-In/Fan-Out, Metacognition - all substantive",
                location="report.pdf",
                rationale="Deep architectural explanations with implementation details.",
                confidence=0.85
            ),
            Evidence(
                goal="report_accuracy",
                found=True,
                content="Claims: 20 verified, 1 minor discrepancy",
                location="report.pdf",
                rationale="99% accuracy with cross-reference validation.",
                confidence=0.82
            )
        ],
        "vision_inspector": [
            Evidence(
                goal="swarm_visual",
                found=True,
                content="LangGraph StateGraph diagram with parallel branches clearly shown",
                location="report.pdf",
                rationale="Accurate architecture visualization.",
                confidence=0.80
            )
        ]
    }
    
    opinions = [
        # Git Analysis
        JudicialOpinion(judge="Prosecutor", criterion_id="git_forensic_analysis",
                       score=4, argument="Strong commit history. Minor improvement: more descriptive messages.",
                       cited_evidence=["git log", "commit timestamps"]),
        JudicialOpinion(judge="Defense", criterion_id="git_forensic_analysis",
                       score=5, argument="Excellent iterative development. Clear story of learning and growth.",
                       cited_evidence=["commit progression"]),
        JudicialOpinion(judge="TechLead", criterion_id="git_forensic_analysis",
                       score=4, argument="Solid git practices. Consider feature branches.",
                       cited_evidence=["branch structure"]),
        
        # State Management
        JudicialOpinion(judge="Prosecutor", criterion_id="state_management_rigor",
                       score=5, argument="Perfect Pydantic implementation with proper reducers.",
                       cited_evidence=["state.py"]),
        JudicialOpinion(judge="Defense", criterion_id="state_management_rigor",
                       score=5, argument="Excellent type safety and state design.",
                       cited_evidence=["AgentState"]),
        JudicialOpinion(judge="TechLead", criterion_id="state_management_rigor",
                       score=5, argument="Production-ready. Clean and maintainable.",
                       cited_evidence=["schema"]),
        
        # Graph Orchestration
        JudicialOpinion(judge="Prosecutor", criterion_id="graph_orchestration",
                       score=4, argument="Proper fan-out/fan-in. Could add more error handling.",
                       cited_evidence=["graph.py"]),
        JudicialOpinion(judge="Defense", criterion_id="graph_orchestration",
                       score=5, argument="Creative LangGraph implementation.",
                       cited_evidence=["parallel execution"]),
        JudicialOpinion(judge="TechLead", criterion_id="graph_orchestration",
                       score=4, argument="Clean architecture. Consider more conditional edges.",
                       cited_evidence=["conditional_edges"]),
        
        # Safe Tool Engineering
        JudicialOpinion(judge="Prosecutor", criterion_id="safe_tool_engineering",
                       score=5, argument="Excellent sandboxing and security practices.",
                       cited_evidence=["repo_tools.py"]),
        JudicialOpinion(judge="Defense", criterion_id="safe_tool_engineering",
                       score=4, argument="Good security. Could add URL validation.",
                       cited_evidence=["input handling"]),
        JudicialOpinion(judge="TechLead", criterion_id="safe_tool_engineering",
                       score=5, argument="Safe and production-ready.",
                       cited_evidence=["error_handling"]),
        
        # Judicial Nuance
        JudicialOpinion(judge="Prosecutor", criterion_id="judicial_nuance",
                       score=4, argument="Distinct personas. Make prosecutor more adversarial.",
                       cited_evidence=["judges.py"]),
        JudicialOpinion(judge="Defense", criterion_id="judicial_nuance",
                       score=5, argument="Excellent dialectical separation.",
                       cited_evidence=["system_prompts"]),
        JudicialOpinion(judge="TechLead", criterion_id="judicial_nuance",
                       score=4, argument="Good role separation.",
                       cited_evidence=["persona_prompts"]),
        
        # Chief Justice
        JudicialOpinion(judge="Prosecutor", criterion_id="chief_justice_synthesis",
                       score=4, argument="Proper synthesis rules implemented.",
                       cited_evidence=["justice.py"]),
        JudicialOpinion(judge="Defense", criterion_id="chief_justice_synthesis",
                       score=5, argument="Excellent deterministic resolution.",
                       cited_evidence=["synthesis_rules"]),
        JudicialOpinion(judge="TechLead", criterion_id="chief_justice_synthesis",
                       score=4, argument="Good rule-based approach.",
                       cited_evidence=["conflict_resolution"]),
    ]
    
    criteria = [
        CriterionResult(
            dimension_id="git_forensic_analysis",
            dimension_name="Git Forensic Analysis",
            final_score=4,
            judge_opinions=[o for o in opinions if o.criterion_id == "git_forensic_analysis"],
            dissent_summary=None,
            remediation="Maintain current workflow. Consider feature branches for major changes."
        ),
        CriterionResult(
            dimension_id="state_management_rigor",
            dimension_name="State Management Rigor",
            final_score=5,
            judge_opinions=[o for o in opinions if o.criterion_id == "state_management_rigor"],
            dissent_summary=None,
            remediation="Continue best practices. Consider adding state validation."
        ),
        CriterionResult(
            dimension_id="graph_orchestration",
            dimension_name="Graph Orchestration Architecture",
            final_score=4,
            judge_opinions=[o for o in opinions if o.criterion_id == "graph_orchestration"],
            dissent_summary=None,
            remediation="Add more conditional edges for edge cases."
        ),
        CriterionResult(
            dimension_id="safe_tool_engineering",
            dimension_name="Safe Tool Engineering",
            final_score=5,
            judge_opinions=[o for o in opinions if o.criterion_id == "safe_tool_engineering"],
            dissent_summary=None,
            remediation="Add URL input validation."
        ),
        CriterionResult(
            dimension_id="judicial_nuance",
            dimension_name="Judicial Nuance and Dialectics",
            final_score=4,
            judge_opinions=[o for o in opinions if o.criterion_id == "judicial_nuance"],
            dissent_summary=None,
            remediation="Make prosecutor persona more adversarial."
        ),
        CriterionResult(
            dimension_id="chief_justice_synthesis",
            dimension_name="Chief Justice Synthesis Engine",
            final_score=4,
            judge_opinions=[o for o in opinions if o.criterion_id == "chief_justice_synthesis"],
            dissent_summary=None,
            remediation="Consider adding more synthesis rules."
        ),
        CriterionResult(
            dimension_id="theoretical_depth",
            dimension_name="Theoretical Depth",
            final_score=5,
            judge_opinions=[o for o in opinions if o.criterion_id == "theoretical_depth"],
            dissent_summary=None,
            remediation="Continue deep architectural explanations."
        ),
        CriterionResult(
            dimension_id="report_accuracy",
            dimension_name="Report Accuracy",
            final_score=4,
            judge_opinions=[o for o in opinions if o.criterion_id == "report_accuracy"],
            dissent_summary=None,
            remediation="Improve cross-reference validation."
        ),
    ]
    
    report = AuditReport(
        repo_url="https://github.com/demo/automaton-auditor",
        executive_summary="The Automaton Auditor demonstrates production-grade LangGraph architecture with proper parallel execution. State management uses Pydantic with correct reducers. The judicial layer shows excellent persona separation. Minor improvements can be made in error handling and persona strength. Overall: Master Thinker level implementation.",
        overall_score=4.5,
        criteria=criteria,
        remediation_plan="1. Add conditional error handling edges\n2. Implement URL input validation\n3. Strengthen prosecutor adversarial prompts\n4. Add more synthesis rules for edge cases\n5. Enhance cross-reference validation"
    )
    
    return evidences, opinions, report


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main dashboard application."""
    
    # Render sidebar
    config = render_provider_sidebar()
    
    if config is None and not IMPORTS_OK:
        st.error("⚠️ Dependencies not properly installed.")
        return
    
    # Render main input
    repo_url, pdf_path, start_audit = render_main_input()
    
    # Initialize session state
    if "audit_results" not in st.session_state:
        st.session_state.audit_results = None
    
    # Run audit
    if start_audit and repo_url and pdf_path:
        if config.get("demo_mode", True):
            # Run demo
            with st.spinner("🎭 Running demo audit..."):
                import time
                time.sleep(1)  # Simulate processing
                
                evidences, opinions, report = generate_demo_data()
                
                st.session_state.audit_results = {
                    "repo_url": repo_url,
                    "pdf_path": pdf_path,
                    "evidences": evidences,
                    "opinions": opinions,
                    "report": report,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add to history
                st.session_state.audit_history.append({
                    "repo": repo_url,
                    "score": report.overall_score,
                    "time": datetime.now().strftime("%H:%M")
                })
            
            st.success("✅ Demo audit completed!")
            
        elif config.get("llm"):
            # Run real audit with LLM
            with st.spinner("🔄 Running audit with LLM..."):
                st.info("Real LLM audit requires full graph execution. Demo mode available.")
        else:
            st.warning("⚠️ No LLM configured. Enable Demo Mode or connect to an LLM.")
    
    # Display results
    if st.session_state.audit_results:
        results = st.session_state.audit_results
        
        st.markdown("---")
        st.header("📊 Audit Results")
        
        # Progress stages
        col1, col2, col3 = st.columns(3)
        
        with col1:
            render_audit_progress("🔍 Detectives", "Collecting evidence", "completed")
        with col2:
            render_audit_progress("⚖️ Judges", "Deliberating", "completed")
        with col3:
            render_audit_progress("🏛️ Chief Justice", "Synthesizing verdict", "completed")
        
        # Display panels
        with st.expander("🔍 Evidence Collected", expanded=False):
            render_evidence_panel(results["evidences"])
        
        with st.expander("⚖️ Judge Deliberations", expanded=False):
            render_judge_panel(results["opinions"])
        
        # Final report (always expanded)
        render_report_panel(results["report"])
    
    else:
        # Welcome message
        st.markdown("""
        ---
        
        ## 👋 Welcome to Automaton Auditor
        
        This is a **hierarchical multi-agent system** that audits GitHub repositories 
        using a "Digital Courtroom" architecture.
        
        ### How It Works
        
        1. **Detectives** (parallel): Collect forensic evidence
           - 🔍 RepoInvestigator - Code structure, git history
           - 📄 DocAnalyst - Report accuracy, theory depth
           - 👁️ VisionInspector - Diagram analysis
        
        2. **Judges** (parallel): Evaluate with distinct lenses
           - ⚖️ Prosecutor - Critical (finds flaws)
           - 🛡️ Defense - Optimistic (rewards effort)
           - 👨‍💼 TechLead - Pragmatic (architecture focus)
        
        3. **Chief Justice**: Synthesizes final verdict
        
        ### Getting Started
        
        - Enable **Demo Mode** in sidebar for sample data
        - Or connect to an **LLM provider** for real audits
        - Click **Start Audit** to begin!
        """)
        
        # Show sample metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Providers", "8+")
        with col2:
            st.metric("Criteria", "10")
        with col3:
            st.metric("Demo Mode", "✓")
        with col4:
            st.metric("Export", "JSON")


if __name__ == "__main__":
    main()
