"""
FastAPI Dashboard for Automaton Auditor

A REST API-based dashboard with Jinja2 templates for the Automaton Auditor system.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import uvicorn
import io
import json

# Import components
try:
    from src.llm_providers import (
        LLMProvider, 
        PROVIDER_CONFIGS, 
        create_llm, 
        check_provider_health,
    )
    from src.state import (
        Evidence, 
        JudicialOpinion, 
        CriterionResult, 
        AuditReport,
        DEFAULT_RUBRIC
    )
    from dashboard.export_utils import (
        export_to_markdown,
        export_to_text,
        export_to_json,
        export_to_html,
        generate_video_script,
    )
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    print(f"Import error: {e}")


# =============================================================================
# FASTAPI APP SETUP
# =============================================================================

app = FastAPI(
    title="Automaton Auditor",
    description="Digital Courtroom for Automated Code Quality Audits",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Create static directory
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AuditRequest(BaseModel):
    repo_url: str
    pdf_path: str = "./report.pdf"
    provider: str = "lm_studio"
    model: Optional[str] = None
    demo_mode: bool = True


class ProviderConfig(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


# =============================================================================
# IN-MEMORY STORAGE
# =============================================================================

audit_storage: Dict[str, Dict] = {}
provider_config: Dict = {"configured": False}


# =============================================================================
# ROUTES
# =============================================================================

async def dashboard(request: Request):
    """Main dashboard page."""
    # Ensure template exists
    template_path = Path(__file__).parent / "templates" / "index.html"
    if not template_path.exists():
        create_template()
    
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return HTMLResponse(content=get_simple_html(), status_code=200)


@app.get("/", tags=["root"])
async def root(request: Request):
    """Root route - serves the dashboard."""
    return await dashboard(request)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "imports_ok": IMPORTS_OK
    }


@app.get("/api/providers")
async def list_providers():
    """List all available LLM providers."""
    if not IMPORTS_OK:
        return {"providers": [], "error": "Dependencies not installed"}
    
    providers = []
    for provider in LLMProvider:
        config = PROVIDER_CONFIGS[provider]
        health = check_provider_health(provider)
        
        providers.append({
            "id": provider.value,
            "name": config.name,
            "requires_api_key": config.requires_api_key,
            "requires_base_url": config.requires_base_url,
            "supports_vision": config.supports_vision,
            "default_model": config.default_model,
            "models": config.models,
            "available": health.get("available", False),
            "health_message": health.get("message", "")
        })
    
    return {"providers": providers}


@app.post("/api/config")
async def configure_provider(config: ProviderConfig):
    """Configure the LLM provider."""
    try:
        if config.provider in [p.value for p in LLMProvider]:
            provider_config.update({
                "provider": config.provider,
                "model": config.model,
                "configured": True
            })
            return {"status": "success", "message": f"Provider {config.provider} configured"}
        else:
            return {"status": "error", "message": "Invalid provider"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/config")
async def get_config():
    return provider_config


@app.post("/api/audit")
async def start_audit(request: AuditRequest, background_tasks: BackgroundTasks):
    """Start a new audit."""
    audit_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    audit_record = {
        "audit_id": audit_id,
        "status": "pending",
        "repo_url": request.repo_url,
        "pdf_path": request.pdf_path,
        "created_at": datetime.now().isoformat(),
        "provider": request.provider
    }
    
    audit_storage[audit_id] = audit_record
    background_tasks.add_task(run_audit_task, audit_id, request)
    
    return {"audit_id": audit_id, "status": "started"}


async def run_audit_task(audit_id: str, request: AuditRequest):
    """Background task to run audit."""
    try:
        audit_storage[audit_id]["status"] = "running"
        
        if request.demo_mode:
            evidences, opinions, report = generate_demo_data()
        else:
            evidences, opinions, report = generate_demo_data()  # Placeholder
        
        audit_storage[audit_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "evidences": serialize_evidences(evidences),
            "opinions": serialize_opinions(opinions),
            "report": report.model_dump() if hasattr(report, 'model_dump') else asdict(report)
        })
        
    except Exception as e:
        audit_storage[audit_id].update({
            "status": "failed",
            "error": str(e)
        })


@app.get("/api/audit/{audit_id}")
async def get_audit(audit_id: str):
    if audit_id not in audit_storage:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit_storage[audit_id]


@app.get("/api/audit")
async def list_audits():
    return {"audits": list(audit_storage.values())}


@app.get("/api/audit/{audit_id}/export/{format}")
async def export_audit(audit_id: str, format: str):
    if audit_id not in audit_storage:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    audit = audit_storage[audit_id]
    
    if audit["status"] != "completed":
        raise HTTPException(status_code=400, detail="Audit not completed")
    
    report = reconstruct_report(audit["report"])
    evidences = reconstruct_evidences(audit["evidences"])
    opinions = reconstruct_opinions(audit["opinions"])
    
    exports = {
        "json": (export_to_json(report, evidences, opinions), "application/json"),
        "markdown": (export_to_markdown(report, evidences, opinions), "text/markdown"),
        "text": (export_to_text(report, evidences, opinions), "text/plain"),
        "html": (export_to_html(report, evidences, opinions), "text/html"),
        "video": (generate_video_script(report, evidences, opinions), "text/plain")
    }
    
    if format not in exports:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    content, media_type = exports[format]
    
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={audit_id}.{format}"}
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def serialize_evidences(evidences):
    return {k: [e.model_dump() if hasattr(e, 'model_dump') else asdict(e) for e in v] 
            for k, v in evidences.items()}

def serialize_opinions(opinions):
    return [o.model_dump() if hasattr(o, 'model_dump') else asdict(o) for o in opinions]

def reconstruct_report(data):
    return AuditReport(**data)

def reconstruct_evidences(data):
    return {k: [Evidence(**e) for e in v] for k, v in data.items()}

def reconstruct_opinions(data):
    return [JudicialOpinion(**o) for o in data]

def generate_demo_data():
    evidences = {
        "repo_investigator": [
            Evidence(goal="git_forensic_analysis", found=True,
                    content="12 commits. Progression: Setup → Tools → Graph → Judges",
                    location="/repo", rationale="Clear iterative development.", confidence=0.95),
            Evidence(goal="state_management_rigor", found=True,
                    content="Pydantic: ✓ | TypedDict: ✓ | Reducers: ✓",
                    location="src/state.py", rationale="Full Pydantic.", confidence=0.92),
            Evidence(goal="graph_orchestration", found=True,
                    content="StateGraph: ✓ | Fan-out: ✓ | Fan-in: ✓",
                    location="src/graph.py", rationale="Proper parallel.", confidence=0.88),
            Evidence(goal="safe_tool_engineering", found=True,
                    content="tempfile: ✓ | subprocess: ✓",
                    location="src/tools", rationale="Secure.", confidence=0.94)
        ],
        "doc_analyst": [
            Evidence(goal="theoretical_depth", found=True,
                    content="Dialectical Synthesis, Fan-In/Fan-Out, Metacognition",
                    location="report.pdf", rationale="Deep understanding.", confidence=0.85),
            Evidence(goal="report_accuracy", found=True,
                    content="Claims verified: 19/20",
                    location="report.pdf", rationale="99% accuracy.", confidence=0.82)
        ],
        "vision_inspector": [
            Evidence(goal="swarm_visual", found=True,
                    content="LangGraph diagram with parallel branches",
                    location="report.pdf", rationale="Accurate.", confidence=0.80)
        ]
    }
    
    opinions = [
        JudicialOpinion(judge="Prosecutor", criterion_id="git_forensic_analysis",
                       score=4, argument="Good commits.", cited_evidence=["git log"]),
        JudicialOpinion(judge="Defense", criterion_id="git_forensic_analysis",
                       score=5, argument="Excellent progression.", cited_evidence=["git log"]),
        JudicialOpinion(judge="TechLead", criterion_id="git_forensic_analysis",
                       score=4, argument="Solid workflow.", cited_evidence=["git log"]),
        
        JudicialOpinion(judge="Prosecutor", criterion_id="state_management_rigor",
                       score=5, argument="Perfect Pydantic.", cited_evidence=["state.py"]),
        JudicialOpinion(judge="Defense", criterion_id="state_management_rigor",
                       score=5, argument="Excellent types.", cited_evidence=["state.py"]),
        JudicialOpinion(judge="TechLead", criterion_id="state_management_rigor",
                       score=5, argument="Production-ready.", cited_evidence=["state.py"]),
        
        JudicialOpinion(judge="Prosecutor", criterion_id="graph_orchestration",
                       score=4, argument="Good parallel.", cited_evidence=["graph.py"]),
        JudicialOpinion(judge="Defense", criterion_id="graph_orchestration",
                       score=5, argument="Excellent architecture.", cited_evidence=["graph.py"]),
        JudicialOpinion(judge="TechLead", criterion_id="graph_orchestration",
                       score=4, argument="Clean structure.", cited_evidence=["graph.py"]),
    ]
    
    criteria = [
        CriterionResult(dimension_id="git_forensic_analysis", dimension_name="Git Forensic Analysis",
                      final_score=4,
                      judge_opinions=[o for o in opinions if o.criterion_id == "git_forensic_analysis"],
                      remediation="Maintain workflow"),
        CriterionResult(dimension_id="state_management_rigor", dimension_name="State Management Rigor",
                      final_score=5,
                      judge_opinions=[o for o in opinions if o.criterion_id == "state_management_rigor"],
                      remediation="Continue best practices"),
        CriterionResult(dimension_id="graph_orchestration", dimension_name="Graph Orchestration",
                      final_score=4,
                      judge_opinions=[o for o in opinions if o.criterion_id == "graph_orchestration"],
                      remediation="Add more conditional edges")
    ]
    
    report = AuditReport(
        repo_url="https://github.com/demo/automaton-auditor",
        executive_summary="Excellent implementation with production-grade architecture.",
        overall_score=4.5,
        criteria=criteria,
        remediation_plan="1. Continue best practices\n2. Add error handling\n3. Enhance tests"
    )
    
    return evidences, opinions, report


def get_simple_html() -> str:
    """Fallback simple HTML if template fails."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Automaton Auditor</title></head>
    <body style="background:#0f172a;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
        <h1>Automaton Auditor</h1>
        <p>Loading...</p>
    </body>
    </html>
    """


# =============================================================================
# TEMPLATE FILES
# =============================================================================

def create_template():
    """Create the template file."""
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automaton Auditor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
        .glass { background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(10px); }
        .glow { box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
    </style>
</head>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automaton Auditor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
        .glass { background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(10px); }
        .glow { box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
    </style>
</head>
<body class="min-h-screen text-gray-100">
    <!-- Header -->
    <nav class="glass border-b border-gray-700">
        <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <i class="fas fa-gavel text-3xl text-blue-400"></i>
                <div>
                    <h1 class="text-2xl font-bold text-blue-400">Automaton Auditor</h1>
                    <p class="text-xs text-gray-400">Digital Courtroom for Code Quality</p>
                </div>
            </div>
            <div class="flex gap-4">
                <button onclick="showSection('audit')" class="px-4 py-2 rounded-lg hover:bg-gray-700 transition">
                    <i class="fas fa-play mr-2"></i>New Audit
                </button>
                <button onclick="showSection('providers')" class="px-4 py-2 rounded-lg hover:bg-gray-700 transition">
                    <i class="fas fa-cog mr-2"></i>Providers
                </button>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Hero Section -->
        <div class="text-center mb-12">
            <h2 class="text-4xl font-bold mb-4">⚖️ Automated Code Quality Audits</h2>
            <p class="text-xl text-gray-400 max-w-2xl mx-auto">
                A hierarchical multi-agent system that audits GitHub repositories using a Digital Courtroom architecture.
            </p>
        </div>

        <!-- Main Grid -->
        <div class="grid lg:grid-cols-3 gap-8">
            <!-- Left Panel - Start Audit -->
            <div class="lg:col-span-1">
                <div class="glass rounded-2xl p-6 glow">
                    <h3 class="text-xl font-bold mb-4 text-blue-400">
                        <i class="fas fa-rocket mr-2"></i>Start Audit
                    </h3>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">Repository URL</label>
                            <input type="text" id="repoUrl" 
                                   placeholder="https://github.com/user/repo"
                                   class="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none">
                        </div>
                        
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">PDF Report Path</label>
                            <input type="text" id="pdfPath" value="./report.pdf"
                                   class="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none">
                        </div>
                        
                        <div>
                            <label class="block text-sm text-gray-400 mb-1">LLM Provider</label>
                            <select id="provider" class="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none">
                            </select>
                        </div>
                        
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" id="demoMode" checked class="w-4 h-4">
                            <span class="text-sm text-gray-300">Demo Mode (no LLM required)</span>
                        </label>
                        
                        <button onclick="startAudit()" 
                                class="w-full bg-gradient-to-r from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 rounded-lg py-3 font-bold transition glow">
                            <i class="fas fa-play mr-2"></i>Start Audit
                        </button>
                    </div>
                </div>

                <!-- Providers Status -->
                <div class="glass rounded-2xl p-6 mt-6">
                    <h3 class="text-lg font-bold mb-3 text-blue-400">
                        <i class="fas fa-server mr-2"></i>Providers
                    </h3>
                    <div id="providerStatus" class="text-sm text-gray-400">
                        Loading...
                    </div>
                </div>
            </div>

            <!-- Right Panel - Results -->
            <div class="lg:col-span-2">
                <!-- Tabs -->
                <div class="flex gap-2 mb-4">
                    <button onclick="showTab('history')" id="tab-history" 
                            class="px-4 py-2 rounded-lg bg-blue-600 font-semibold">
                        <i class="fas fa-history mr-2"></i>History
                    </button>
                    <button onclick="showTab('result')" id="tab-result" 
                            class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600">
                        <i class="fas fa-chart-bar mr-2"></i>Results
                    </button>
                </div>

                <!-- History Panel -->
                <div id="panel-history">
                    <div class="glass rounded-2xl p-6">
                        <h3 class="text-xl font-bold mb-4 text-blue-400">Recent Audits</h3>
                        <div id="auditList" class="space-y-3">
                            <p class="text-gray-400">No audits yet. Start your first audit!</p>
                        </div>
                    </div>
                </div>

                <!-- Result Panel -->
                <div id="panel-result" class="hidden">
                    <div class="glass rounded-2xl p-6">
                        <div id="resultContent">
                            <p class="text-gray-400 text-center py-8">
                                Run an audit to see results here
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Loading Modal -->
    <div id="loadingModal" class="fixed inset-0 bg-black/70 hidden items-center justify-center z-50">
        <div class="glass rounded-2xl p-8 text-center">
            <i class="fas fa-spinner fa-spin text-4xl text-blue-400 mb-4"></i>
            <h3 class="text-xl font-bold">Running Audit...</h3>
            <p class="text-gray-400 mt-2">Please wait while we analyze the repository</p>
        </div>
    </div>

    <script>
        const API = '';
        let currentAuditId = null;

        // Load providers on start
        async function loadProviders() {
            try {
                const res = await fetch(API + '/api/providers');
                const data = await res.json();
                
                const select = document.getElementById('provider');
                select.innerHTML = data.providers.map(p => 
                    `<option value="${p.id}">${p.name} ${p.available ? '✅' : '❌'}</option>`
                ).join('');
                
                const status = document.getElementById('providerStatus');
                const available = data.providers.filter(p => p.available).length;
                status.innerHTML = `${available} of ${data.providers.length} providers available`;
            } catch (e) {
                console.error(e);
            }
        }

        // Load audits
        async function loadAudits() {
            try {
                const res = await fetch(API + '/api/audit');
                const data = await res.json();
                
                const list = document.getElementById('auditList');
                if (data.audits.length === 0) {
                    list.innerHTML = '<p class="text-gray-400">No audits yet.</p>';
                    return;
                }
                
                list.innerHTML = data.audits.map(a => `
                    <div class="bg-gray-800 rounded-lg p-4 flex justify-between items-center cursor-pointer hover:bg-gray-700" 
                         onclick="viewAudit('${a.audit_id}')">
                        <div>
                            <div class="font-semibold">${a.repo_url}</div>
                            <div class="text-sm text-gray-400">${a.created_at}</div>
                        </div>
                        <span class="px-3 py-1 rounded-full text-sm ${
                            a.status === 'completed' ? 'bg-green-600' : 
                            a.status === 'running' ? 'bg-blue-600' :
                            a.status === 'failed' ? 'bg-red-600' : 'bg-yellow-600'
                        }">${a.status}</span>
                    </div>
                `).reverse().join('');
            } catch (e) {
                console.error(e);
            }
        }

        // Start audit
        async function startAudit() {
            const repoUrl = document.getElementById('repoUrl').value;
            const pdfPath = document.getElementById('pdfPath').value;
            const provider = document.getElementById('provider').value;
            const demoMode = document.getElementById('demoMode').checked;

            if (!repoUrl) {
                alert('Please enter a repository URL');
                return;
            }

            document.getElementById('loadingModal').classList.remove('hidden');
            document.getElementById('loadingModal').classList.add('flex');

            try {
                const res = await fetch(API + '/api/audit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        repo_url: repoUrl,
                        pdf_path: pdfPath,
                        provider: provider,
                        demo_mode: demoMode
                    })
                });
                
                const data = await res.json();
                currentAuditId = data.audit_id;
                
                // Poll for results
                for (let i = 0; i < 30; i++) {
                    await new Promise(r => setTimeout(r, 1000));
                    const statusRes = await fetch(API + '/api/audit/' + data.audit_id);
                    const status = await statusRes.json();
                    
                    if (status.status === 'completed') {
                        showResult(status);
                        break;
                    } else if (status.status === 'failed') {
                        alert('Audit failed: ' + status.error);
                        break;
                    }
                }
                
                loadAudits();
            } catch (e) {
                alert('Error: ' + e);
            } finally {
                document.getElementById('loadingModal').classList.add('hidden');
                document.getElementById('loadingModal').classList.remove('flex');
            }
        }

        // View audit result
        async function viewAudit(auditId) {
            try {
                const res = await fetch(API + '/api/audit/' + auditId);
                const data = await res.json();
                showResult(data);
            } catch (e) {
                console.error(e);
            }
        }

        // Show result
        function showResult(data) {
            showTab('result');
            
            if (data.status !== 'completed') {
                document.getElementById('resultContent').innerHTML = 
                    `<p class="text-yellow-400">Status: ${data.status}</p>`;
                return;
            }
            
            const report = data.report;
            const criteria = report.criteria || [];
            
            let html = `
                <div class="grid grid-cols-3 gap-4 mb-6">
                    <div class="bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl p-4 text-center">
                        <div class="text-3xl font-bold">${report.overall_score}</div>
                        <div class="text-sm text-blue-200">Overall Score</div>
                    </div>
                    <div class="bg-gradient-to-br from-green-500 to-green-700 rounded-xl p-4 text-center">
                        <div class="text-3xl font-bold">${criteria.filter(c => c.final_score >= 4).length}</div>
                        <div class="text-sm text-green-200">Excellent</div>
                    </div>
                    <div class="bg-gradient-to-br from-purple-500 to-purple-700 rounded-xl p-4 text-center">
                        <div class="text-3xl font-bold">${criteria.length}</div>
                        <div class="text-sm text-purple-200">Criteria</div>
                    </div>
                </div>
                
                <h4 class="font-bold mb-3 text-blue-400">Score Breakdown</h4>
                <div class="space-y-2 mb-6">
                    ${criteria.map(c => `
                        <div class="bg-gray-800 rounded-lg p-3 flex justify-between items-center">
                            <span>${c.dimension_name}</span>
                            <span class="px-3 py-1 rounded-full text-sm ${
                                c.final_score >= 4 ? 'bg-green-600' :
                                c.final_score >= 3 ? 'bg-yellow-600' : 'bg-red-600'
                            }">${c.final_score}/5</span>
                        </div>
                    `).join('')}
                </div>
                
                <div class="flex gap-2 mb-4">
                    <a href="${API}/api/audit/${data.audit_id}/export/json" 
                       class="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700">
                        <i class="fas fa-download mr-2"></i>JSON
                    </a>
                    <a href="${API}/api/audit/${data.audit_id}/export/markdown" 
                       class="px-4 py-2 bg-green-600 rounded-lg hover:bg-green-700">
                        <i class="fas fa-file-alt mr-2"></i>Markdown
                    </a>
                    <a href="${API}/api/audit/${data.audit_id}/export/html" 
                       class="px-4 py-2 bg-purple-600 rounded-lg hover:bg-purple-700">
                        <i class="fas fa-code mr-2"></i>HTML
                    </a>
                </div>
                
                <h4 class="font-bold mb-2 text-blue-400">Executive Summary</h4>
                <p class="text-gray-300 bg-gray-800 rounded-lg p-4">${report.executive_summary}</p>
            `;
            
            document.getElementById('resultContent').innerHTML = html;
        }

        // Tab switching
        function showTab(tab) {
            document.getElementById('panel-history').classList.toggle('hidden', tab !== 'history');
            document.getElementById('panel-result').classList.toggle('hidden', tab !== 'result');
            document.getElementById('tab-history').classList.toggle('bg-blue-600', tab === 'history');
            document.getElementById('tab-history').classList.toggle('bg-gray-700', tab !== 'history');
            document.getElementById('tab-result').classList.toggle('bg-blue-600', tab === 'result');
            document.getElementById('tab-result').classList.toggle('bg-gray-700', tab !== 'result');
        }

        // Initialize
        loadProviders();
        loadAudits();
    </script>
</body>
</html>
"""

# Ensure template exists on startup
if __name__ == "__main__":
    create_template()
    uvicorn.run(app, host="0.0.0.0", port=8000)
