"""
LangSmith Integration Module for Automaton Auditor

This module provides LangSmith tracing integration for debugging,
monitoring, and analyzing the Automaton Auditor's multi-agent workflows.

LangSmith is LangChain's platform for debugging, monitoring, and tracing
LLM applications. This module enables:
- Automatic tracing of all LLM calls
- State inspection at each node
- Run history and feedback
- Performance metrics
"""

import os
from typing import Optional, Dict, Any, List
from functools import wraps
from datetime import datetime


# =============================================================================
# LANGSMITH CONFIGURATION
# =============================================================================


def get_langsmith_config() -> Dict[str, Optional[str]]:
    """
    Get LangSmith configuration from environment variables.
    
    Returns:
        Dict with configuration values
    """
    return {
        "tracing_enabled": os.getenv("LANGSMITH_TRACING", "false").lower() == "true",
        "api_key": os.getenv("LANGCHAIN_API_KEY"),
        "project": os.getenv("LANGCHAIN_PROJECT", "automaton-auditor"),
        "endpoint": os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        "tenant_id": os.getenv("LANGCHAIN_TENANT_ID"),
    }


def is_langsmith_enabled() -> bool:
    """
    Check if LangSmith tracing is enabled.
    
    Returns:
        True if LangSmith is configured and enabled
    """
    config = get_langsmith_config()
    return config["tracing_enabled"] and config["api_key"] is not None


def configure_langsmith():
    """
    Configure LangSmith environment variables.
    
    This should be called before importing LangGraph or LangChain
    to ensure tracing is enabled from the start.
    
    Note: This function sets os.environ values, so it should be called
    before any LangChain imports.
    """
    if is_langsmith_enabled():
        # LangChain will automatically pick up these env vars
        os.environ["LANGSMITH_TRACING"] = "true"
        # Ensure we have the API key set
        if "LANGCHAIN_API_KEY" not in os.environ:
            api_key = os.getenv("LANGCHAIN_API_KEY")
            if api_key:
                os.environ["LANGCHAIN_API_KEY"] = api_key
        print(f"[LangSmith] Tracing enabled for project: {get_langsmith_config()['project']}")
    else:
        print("[LangSmith] Tracing disabled. Set LANGSMITH_TRACING=true and LANGCHAIN_API_KEY to enable.")


# =============================================================================
# LANGSMITH CALLBACK HANDLER
# =============================================================================


def create_langsmith_callback(project_name: Optional[str] = None):
    """
    Create a LangSmith callback handler for LangChain models.
    
    Args:
        project_name: Optional project name override
        
    Returns:
        LangSmithCallbackHandler or None if not configured
    """
    if not is_langsmith_enabled():
        return None
    
    try:
        from langchain_community.callbacks import LangSmithCallbackHandler
    except ImportError:
        try:
            from langchain.callbacks import LangSmithCallbackHandler
        except ImportError:
            print("[LangSmith] Warning: LangSmith callback handler not available")
            return None
    
    config = get_langsmith_config()
    project = project_name or config["project"]
    
    return LangSmithCallbackHandler(
        project_name=project,
        endpoint=config["endpoint"],
        tenant_id=config["tenant_id"],
    )


# =============================================================================
# GRAPH TRACING HELPERS
# =============================================================================


def trace_node(node_name: str):
    """
    Decorator to trace a node function with LangSmith.
    
    Args:
        node_name: Name of the node for tracing
        
    Returns:
        Decorated function with tracing
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_langsmith_enabled():
                from langsmith import traceable
                # Use langsmith's traceable for manual tracing
                return traceable(func, name=node_name)(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def create_traced_graph(graph, project_name: Optional[str] = None):
    """
    Wrap a compiled LangGraph with LangSmith tracing.
    
    Args:
        graph: Compiled LangGraph
        project_name: Optional project name
        
    Returns:
        Graph with LangSmith tracing enabled
    """
    if not is_langsmith_enabled():
        return graph
    
    config = get_langsmith_config()
    project = project_name or config["project"]
    
    # LangGraph automatically traces when LANGSMITH_TRACING is set
    # This function provides additional configuration if needed
    print(f"[LangSmith] Graph '{project}' will be traced")
    
    return graph


# =============================================================================
# RUN TRACKING
# =============================================================================


class AuditRunTracker:
    """
    Track audit runs for LangSmith with additional metadata.
    
    This class provides structured logging for audit runs,
    including rubric dimensions, repository info, and final scores.
    """
    
    def __init__(self, repo_url: str, rubric_dimensions: List[Dict]):
        self.repo_url = repo_url
        self.rubric_dimensions = rubric_dimensions
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.run_id: Optional[str] = None
        
    def start_run(self) -> Dict[str, Any]:
        """
        Start a new tracked run.
        
        Returns:
            Run metadata dict
        """
        if not is_langsmith_enabled():
            return {"status": "disabled"}
        
        try:
            from langsmith import Client
            
            client = Client()
            
            # Create a new run
            run = client.create_run(
                project_name=get_langsmith_config()["project"],
                name="audit_run",
                run_type="chain",
                inputs={
                    "repo_url": self.repo_url,
                    "rubric_dimensions": [d.get("id", "unknown") for d in self.rubric_dimensions]
                },
                extra={
                    "repo_url": self.repo_url,
                    "num_dimensions": len(self.rubric_dimensions)
                }
            )
            
            self.run_id = run.id
            return {"status": "started", "run_id": str(run.id)}
            
        except Exception as e:
            print(f"[LangSmith] Warning: Could not start run: {e}")
            return {"status": "error", "message": str(e)}
    
    def end_run(self, final_report: Optional[Dict] = None, error: Optional[str] = None):
        """
        End the tracked run with results.
        
        Args:
            final_report: Final audit report dict
            error: Error message if run failed
        """
        self.end_time = datetime.now()
        
        if not is_langsmith_enabled() or not self.run_id:
            return
        
        try:
            from langsmith import Client
            
            client = Client()
            
            outputs = {}
            if final_report:
                outputs = {
                    "final_score": final_report.get("overall_score", "N/A"),
                    "num_criteria": len(final_report.get("criteria_results", []))
                }
            
            if error:
                outputs["error"] = error
                
            client.update_run(
                run_id=self.run_id,
                outputs=outputs,
                end_time=self.end_time.isoformat()
            )
            
        except Exception as e:
            print(f"[LangSmith] Warning: Could not update run: {e}")
    
    def log_evidence(self, detective_name: str, evidence_count: int):
        """
        Log evidence collection event.
        
        Args:
            detective_name: Name of the detective
            evidence_count: Number of evidence items collected
        """
        if not is_langsmith_enabled():
            return
            
        try:
            from langsmith import Client
            client = Client()
            
            # Log as a child run
            client.create_run(
                project_name=get_langsmith_config()["project"],
                name=detective_name,
                run_type="tool",
                parent_run_id=self.run_id,
                inputs={"detective": detective_name},
                outputs={"evidence_count": evidence_count}
            )
        except Exception:
            pass
    
    def log_judgment(self, judge_name: str, criterion_id: str, score: int):
        """
        Log judgment event from a judge.
        
        Args:
            judge_name: Name of the judge (prosecutor/defense/tech_lead)
            criterion_id: ID of the criterion evaluated
            score: Score given by the judge
        """
        if not is_langsmith_enabled():
            return
            
        try:
            from langsmith import Client
            client = Client()
            
            client.create_run(
                project_name=get_langsmith_config()["project"],
                name=f"{judge_name}_judgment",
                run_type="chain",
                parent_run_id=self.run_id,
                inputs={
                    "judge": judge_name,
                    "criterion": criterion_id
                },
                outputs={"score": score}
            )
        except Exception:
            pass


# =============================================================================
# DASHBOARD INTEGRATION
# =============================================================================


def get_langsmith_dashboard_url() -> Optional[str]:
    """
    Get the URL for the LangSmith dashboard.
    
    Returns:
        URL string or None if not configured
    """
    if not is_langsmith_enabled():
        return None
    
    config = get_langsmith_config()
    project = config["project"]
    
    # LangSmith dashboard URL format
    return f"{config['endpoint']}/o/{config.get('tenant_id', 'default')}/projects/{project}"


def print_dashboard_link():
    """Print a clickable link to the LangSmith dashboard."""
    url = get_langsmith_dashboard_url()
    if url:
        print(f"\n{'='*60}")
        print(f"📊 LangSmith Dashboard: {url}")
        print(f"{'='*60}\n")
    else:
        print("\n[LangSmith] Tracing not enabled. Check your .env file.")


# =============================================================================
# INITIALIZATION
# =============================================================================


def init_langsmith():
    """
    Initialize LangSmith tracing.
    
    This should be called at application startup before any LangChain
    or LangGraph operations.
    """
    configure_langsmith()
    
    if is_langsmith_enabled():
        print_dashboard_link()
    
    return is_langsmith_enabled()


# Auto-initialize when this module is imported
# Uncomment the following line to auto-enable tracing
# init_langsmith()


if __name__ == "__main__":
    # Test LangSmith configuration
    config = get_langsmith_config()
    print("LangSmith Configuration:")
    print(f"  Enabled: {config['tracing_enabled']}")
    print(f"  API Key set: {config['api_key'] is not None}")
    print(f"  Project: {config['project']}")
    print(f"  Endpoint: {config['endpoint']}")
    print(f"  Dashboard: {get_langsmith_dashboard_url()}")
