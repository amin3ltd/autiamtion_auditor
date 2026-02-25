"""Test script to run the Automaton Auditor against this repository."""
import os
import sys

# Set up environment for LM Studio
os.environ["LM_STUDIO_URL"] = "http://localhost:1234/v1"
os.environ["LM_MODEL"] = "gemma-3-4b"

print("Setting up Automaton Auditor test...")
print(f"LM Studio URL: {os.environ['LM_STUDIO_URL']}")
print(f"Model: {os.environ['LM_MODEL']}")

# Import after env is set
from src.lm_studio import create_lm_studio_llm
from src.graph import run_auditor
from src.state import create_initial_state

# Create LLM instance
print("\nConnecting to LM Studio...")
try:
    llm = create_lm_studio_llm(model_name=os.environ["LM_MODEL"])
    print("OK - Connected to LM Studio")
except Exception as e:
    print(f"FAIL - Failed to connect: {e}")
    sys.exit(1)

# Sample rubric dimensions (subset for testing)
rubric_dimensions = [
    {
        "id": "state_management_rigor",
        "name": "State Management Rigor",
        "target_artifact": "github_repo",
        "forensic_instruction": "Check for Pydantic models and reducers",
    },
    {
        "id": "graph_orchestration",
        "name": "Graph Orchestration",
        "target_artifact": "github_repo",
        "forensic_instruction": "Verify parallel fan-out/fan-in structure",
    },
]

# Run the auditor
print("\nRunning Automaton Auditor...")
print("Target: This repository + test.pdf")
print("(This may take a minute...)\n")

try:
    result = run_auditor(
        repo_url="https://github.com/amin3ltd/autiamtion_auditor",
        pdf_path="./test.pdf",
        rubric_dimensions=rubric_dimensions,
        llm=llm
    )
    
    print("\n" + "="*60)
    print("AUDIT COMPLETE")
    print("="*60)
    
    # Print final report summary
    if result.get("final_report"):
        report = result["final_report"]
        print(f"\nRepository: {report.repo_url}")
        print(f"Overall Score: {report.overall_score:.1f}/5.0")
        print(f"\nCriteria Evaluated: {len(report.criteria)}")
        
        print("\n--- DETAILED RESULTS ---")
        for criterion in report.criteria:
            print(f"\n{criterion.dimension_name}: {criterion.final_score}/5")
            print(f"  Remediation: {criterion.remediation}")
            
            # Print judge opinions (abbreviated)
            for op in criterion.judge_opinions:
                score_str = f"{op.judge[:3]}: {op.score}"
                arg_preview = op.argument[:80].replace('\n', ' ')
                print(f"    {score_str} - {arg_preview}...")
        
        print(f"\n--- EXECUTIVE SUMMARY ---")
        print(report.executive_summary[:300] + "..." if len(report.executive_summary) > 300 else report.executive_summary)
    else:
        print("\nNo final report generated")
    
except Exception as e:
    print(f"\nFAIL - Error during audit: {e}")
    import traceback
    traceback.print_exc()
