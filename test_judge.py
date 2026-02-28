"""Quick test of a single judge."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up environment for LM Studio (use .env values if available, otherwise use defaults)
os.environ.setdefault("LM_STUDIO_URL", "http://localhost:1234/v1")
os.environ.setdefault("LM_MODEL", "gemma-3-4b")

from src.lm_studio import create_llm_from_env
from src.state import AgentState, Evidence

# Create test LLM
print("Creating LLM...")
llm = create_llm_from_env()
print("LLM created")

# Create test state
test_state: AgentState = {
    "repo_url": "https://github.com/test",
    "pdf_path": "./test.pdf",
    "rubric_dimensions": [
        {"id": "test", "name": "Test Criterion"}
    ],
    "evidences": {
        "repo_investigator": [
            Evidence(
                goal="test",
                found=True,
                content="StateGraph with parallel execution detected",
                location="src/graph.py",
                rationale="AST analysis shows parallel nodes",
                confidence=0.8
            )
        ]
    },
    "opinions": [],
    "final_report": None
}

# Test a single judge
from src.nodes.judges import create_prosecutor_node

print("Creating prosecutor node...")
prosecutor = create_prosecutor_node(llm)

print("Running prosecutor...")
result = prosecutor(test_state)

print("\nResult:")
print(result)
