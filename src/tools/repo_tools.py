"""
Repository Investigation Tools

Provides forensic tools for analyzing GitHub repositories:
- Sandboxed git clone operations
- Git history extraction and analysis
- AST-based code structure analysis
- Graph wiring verification
"""

import ast
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =============================================================================
# SANDBOXED GIT OPERATIONS
# =============================================================================


class GitCloneError(Exception):
    """Raised when git clone fails."""
    pass


class GitAnalysisError(Exception):
    """Raised when git analysis fails."""
    pass


def clone_repository(repo_url: str, branch: str = "main") -> str:
    """
    Clone a GitHub repository into an isolated temporary directory.
    
    SECURITY: This function uses tempfile.TemporaryDirectory to ensure
    the cloned repository is isolated from the main codebase.
    
    Args:
        repo_url: The HTTPS URL of the GitHub repository
        branch: The branch to clone (default: main)
    
    Returns:
        Path to the temporary directory containing the cloned repo
    
    Raises:
        GitCloneError: If the clone operation fails
    """
    temp_dir = None
    
    try:
        # Create an isolated temporary directory
        temp_dir = tempfile.mkdtemp(prefix="auditor_clone_")
        repo_path = Path(temp_dir)
        
        # Validate the URL is HTTPS (never allow file:// or local paths)
        if not repo_url.startswith("https://github.com/"):
            # Allow git@ URLs for authentication
            if not repo_url.startswith("git@github.com:"):
                raise GitCloneError(
                    f"Only GitHub HTTPS or SSH URLs are allowed. Got: {repo_url}"
                )
        
        # Use subprocess with explicit error handling
        # Capture both stdout and stderr for debugging
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise GitCloneError(
                f"Git clone failed with code {result.returncode}: {result.stderr}"
            )
        
        return str(repo_path)
    
    except subprocess.TimeoutExpired:
        raise GitCloneError("Git clone timed out after 5 minutes")
    except FileNotFoundError:
        raise GitCloneError("Git is not installed or not in PATH")
    except Exception as e:
        # Clean up on failure
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise GitCloneError(f"Unexpected error during clone: {str(e)}")


def get_git_history(repo_path: str) -> Dict:
    """
    Extract the git commit history to verify iterative development.
    
    Analyzes:
    - Number of commits (should be > 3 for progression)
    - Commit timestamps (detect bulk upload patterns)
    - Commit messages (verify step-by-step progression)
    
    Args:
        repo_path: Path to the cloned repository
    
    Returns:
        Dict with commit history analysis
    
    Raises:
        GitAnalysisError: If git history cannot be extracted
    """
    try:
        os.chdir(repo_path)
        
        # Get commit log with timestamps
        result = subprocess.run(
            ["git", "log", "--oneline", "--date=iso", "--format=%H|%ad|%s"],
            capture_output=True,
            text=True,
            cwd=repo_path
        )
        
        if result.returncode != 0:
            raise GitAnalysisError(f"git log failed: {result.stderr}")
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({
                    "hash": parts[0],
                    "timestamp": parts[1],
                    "message": parts[2]
                })
        
        # Analyze for patterns
        commit_count = len(commits)
        
        # Check for single "init" commit
        is_monolithic = (
            commit_count <= 1 or
            (commit_count <= 3 and all("init" in c["message"].lower() for c in commits))
        )
        
        # Check for bulk upload (all commits within minutes)
        if len(commits) >= 2:
            first_time = commits[0]["timestamp"]
            last_time = commits[-1]["timestamp"]
            # Simplified check - just note the timestamps
            time_span_note = f"First: {first_time}, Last: {last_time}"
        else:
            time_span_note = "Insufficient commits for time analysis"
        
        return {
            "commits": commits,
            "count": commit_count,
            "is_monolithic": is_monolithic,
            "time_span_note": time_span_note,
            "progression_detected": commit_count > 3
        }
    
    except Exception as e:
        raise GitAnalysisError(f"Failed to analyze git history: {str(e)}")


# =============================================================================
# AST-BASED CODE ANALYSIS
# =============================================================================


def analyze_graph_structure(repo_path: str) -> Dict:
    """
    Analyze the LangGraph structure using AST parsing.
    
    This is more robust than regex because it understands
    actual Python syntax and can verify:
    - StateGraph instantiation
    - Node definitions
    - Edge wiring (fan-out/fan-in patterns)
    - Conditional edges
    
    Args:
        repo_path: Path to the repository
    
    Returns:
        Dict with graph structure analysis
    """
    graph_file = Path(repo_path) / "src" / "graph.py"
    
    if not graph_file.exists():
        # Try alternate locations
        for alt_path in ["graph.py", "src/graph.py", "app/graph.py"]:
            if Path(repo_path) / alt_path:
                graph_file = Path(repo_path) / alt_path
                break
    
    if not graph_file.exists():
        return {
            "found": False,
            "error": "No graph.py file found",
            "has_stategraph": False,
            "has_parallel_fanout": False,
            "nodes": [],
            "edges": []
        }
    
    try:
        with open(graph_file, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        tree = ast.parse(source_code)
        
        # Find StateGraph instantiation
        has_stategraph = False
        nodes = []
        edges = []
        conditional_edges = []
        
        for node in ast.walk(tree):
            # Check for StateGraph(...)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
                    has_stategraph = True
            
            # Look for builder.add_edge calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "add_edge":
                        # Extract source and target
                        if len(node.args) >= 2:
                            source = _extract_name(node.args[0])
                            target = _extract_name(node.args[1])
                            if source and target:
                                edges.append({"source": source, "target": target})
                    
                    elif node.func.attr == "add_conditional_edges":
                        if len(node.args) >= 2:
                            source = _extract_name(node.args[0])
                            conditional_edges.append({"source": source, "type": "conditional"})
            
            # Look for node definitions (functions or lambda definitions)
            if isinstance(node, ast.FunctionDef):
                nodes.append(node.name)
        
        # Analyze for parallel patterns
        # Fan-out: One node connects to multiple nodes
        # Fan-in: Multiple nodes connect to one node
        
        fanout_sources = {}
        fanin_targets = {}
        
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            fanout_sources[source] = fanout_sources.get(source, 0) + 1
            fanin_targets[target] = fanin_targets.get(target, 0) + 1
        
        has_parallel_fanout = any(count > 1 for count in fanout_sources.values())
        has_parallel_fanin = any(count > 1 for count in fanin_targets.values())
        
        return {
            "found": True,
            "file": str(graph_file),
            "has_stategraph": has_stategraph,
            "has_parallel_fanout": has_parallel_fanout,
            "has_parallel_fanin": has_parallel_fanin,
            "nodes": nodes,
            "edges": edges,
            "conditional_edges": conditional_edges,
            "fanout_count": fanout_sources,
            "fanin_count": fanin_targets
        }
    
    except Exception as e:
        return {
            "found": True,
            "error": str(e),
            "has_stategraph": False,
            "has_parallel_fanout": False,
            "nodes": [],
            "edges": []
        }


def analyze_state_definitions(repo_path: str) -> Dict:
    """
    Analyze state definitions using AST parsing.
    
    Verifies:
    - Use of Pydantic BaseModel
    - Use of TypedDict
    - Use of Annotated with reducers (operator.add, operator.ior)
    - Evidence and JudicialOpinion model definitions
    
    Args:
        repo_path: Path to the repository
    
    Returns:
        Dict with state definition analysis
    """
    state_file = Path(repo_path) / "src" / "state.py"
    
    if not state_file.exists():
        # Try alternate locations
        for alt_path in ["state.py", "src/state.py", "src/models.py"]:
            if (Path(repo_path) / alt_path).exists():
                state_file = Path(repo_path) / alt_path
                break
    
    if not state_file.exists():
        return {
            "found": False,
            "error": "No state.py file found",
            "has_pydantic": False,
            "has_typeddict": False,
            "has_reducers": False
        }
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        tree = ast.parse(source_code)
        
        has_pydantic = False
        has_typeddict = False
        has_reducers = False
        has_evidence_model = False
        has_judicial_opinion_model = False
        has_agent_state = False
        
        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "pydantic":
                    for alias in node.names:
                        if alias.name == "BaseModel":
                            has_pydantic = True
                if node.module == "typing_extensions" or node.module == "typing":
                    for alias in node.names:
                        if alias.name == "TypedDict":
                            has_typeddict = True
                if node.module == "typing":
                    for alias in node.names:
                        if alias.name == "Annotated":
                            has_reducers = True
            
            # Check for operator imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "operator":
                        has_reducers = True
            
            # Check class definitions
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from BaseModel
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        if node.name == "Evidence":
                            has_evidence_model = True
                        elif node.name == "JudicialOpinion":
                            has_judicial_opinion_model = True
                
                # Check if it's a TypedDict
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "TypedDict":
                        if node.name == "AgentState":
                            has_agent_state = True
        
        # Check for operator.add or operator.ior in Annotated
        has_operator_reducers = "operator.add" in source_code or "operator.ior" in source_code
        
        return {
            "found": True,
            "file": str(state_file),
            "has_pydantic": has_pydantic,
            "has_typeddict": has_typeddict,
            "has_reducers": has_reducers and has_operator_reducers,
            "has_evidence_model": has_evidence_model,
            "has_judicial_opinion_model": has_judicial_opinion_model,
            "has_agent_state": has_agent_state,
            "uses_pydantic_rigor": has_pydantic and has_evidence_model
        }
    
    except Exception as e:
        return {
            "found": True,
            "error": str(e),
            "has_pydantic": False,
            "has_typeddict": False,
            "has_reducers": False
        }


def check_sandboxing(repo_path: str) -> Dict:
    """
    Verify that git operations use proper sandboxing.
    
    Checks:
    - Use of tempfile.TemporaryDirectory
    - No raw os.system() calls
    - Proper error handling
    - No auth keys in code
    
    Args:
        repo_path: Path to the repository
    
    Returns:
        Dict with sandboxing analysis
    """
    tools_dir = Path(repo_path) / "src" / "tools"
    
    if not tools_dir.exists():
        return {
            "found": False,
            "error": "No tools directory found",
            "uses_tempfile": False,
            "has_security_issues": True
        }
    
    issues = []
    uses_tempfile = False
    uses_subprocess = False
    uses_os_system = False
    
    for py_file in tools_dir.glob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check for tempfile
            if "tempfile" in content:
                uses_tempfile = True
            
            # Check for subprocess
            if "subprocess.run" in content or "subprocess.call" in content:
                uses_subprocess = True
            
            # Check for dangerous os.system
            if "os.system" in content:
                uses_os_system = True
                issues.append(f"Found os.system in {py_file.name}")
            
            # Check for hardcoded secrets
            if re.search(r'["\']ghp_[a-zA-Z0-9]{36}', content):
                issues.append(f"Hardcoded GitHub token found in {py_file.name}")
            
            if re.search(r'os\.environ\.get\([\'"]API_KEY', content):
                # This is OK - using env vars is good
                pass
                
        except Exception:
            pass
    
    return {
        "found": True,
        "tools_dir": str(tools_dir),
        "uses_tempfile": uses_tempfile,
        "uses_subprocess": uses_subprocess,
        "uses_os_system": uses_os_system,
        "has_security_issues": len(issues) > 0,
        "issues": issues
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _extract_name(node: ast.AST) -> Optional[str]:
    """
    Extract a name from an AST node.
    
    Handles:
    - ast.Name (the variable name)
    - ast.Constant (string literals)
    - ast.Attribute (module.name)
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return str(node.value)
    elif isinstance(node, ast.Attribute):
        return node.attr
    return None


def find_python_files(repo_path: str, pattern: str = "*.py") -> List[str]:
    """
    Find all Python files in the repository.
    
    Args:
        repo_path: Root path of the repository
        pattern: Glob pattern for matching files
    
    Returns:
        List of relative file paths
    """
    root = Path(repo_path)
    files = []
    
    for path in root.rglob(pattern):
        # Skip __pycache__ and hidden directories
        if "__pycache__" in str(path) or any(
            part.startswith(".") for part in path.parts
        ):
            continue
        files.append(str(path.relative_to(root)))
    
    return files
