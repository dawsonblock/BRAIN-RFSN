# FILE: ui/backend/main.py
"""FastAPI backend for RFSN Control Center."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel

from .security import is_path_confined, validate_run_id, safe_join, ConfinementError
from .ledger_parse import (
    parse_ledger_file,
    build_timeline,
    verify_ledger_chain,
    get_ledger_summary,
)
from .run_manager import run_manager, RunConfig, RunMode, RunStatus
from .sse import sse_event, stream_file_tail


app = FastAPI(
    title="RFSN Control Center API",
    description="Backend API for RFSN agent runs and monitoring",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    # Content Security Policy - allow self and inline for dev
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' http://localhost:* ws://localhost:*"
    )
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Enable XSS filter
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ============ Models ============

class CreateRunRequest(BaseModel):
    mode: str  # "agent" or "harness"
    workspace: str = ""
    tasks_file: str = ""
    model: str = "gpt-4"
    base_url: str = ""
    api_key: str = ""
    max_attempts: int = 6
    timeout: int = 3600


class RunResponse(BaseModel):
    id: str
    config: Dict[str, Any]
    status: str
    created_at: str
    started_at: str
    ended_at: str
    exit_code: Optional[int]
    error: str


class VerifyResponse(BaseModel):
    valid: bool
    message: str
    entry_count: int


class SettingsRequest(BaseModel):
    model: str = "gpt-4"
    base_url: str = ""
    api_key: str = ""


# ============ Settings Storage ============

SETTINGS_FILE = Path(__file__).parent.parent.parent / "ui_runs" / ".settings.json"


def load_settings() -> Dict[str, str]:
    """Load settings from file."""
    import json
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"model": "gpt-4", "base_url": "", "api_key": ""}


def save_settings(settings: Dict[str, str]):
    """Save settings to file."""
    import json
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


# ============ Endpoints ============

@app.get("/")
async def root():
    return {"status": "ok", "service": "RFSN Control Center"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ---- Runs ----

@app.get("/runs", response_model=List[RunResponse])
async def list_runs():
    """List all runs."""
    return [r.to_dict() for r in run_manager.list_runs()]


@app.post("/runs/create", response_model=RunResponse)
async def create_run(req: CreateRunRequest):
    """Create a new run."""
    try:
        mode = RunMode(req.mode)
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {req.mode}")
    
    # Validate paths
    if mode == RunMode.AGENT and not req.workspace:
        raise HTTPException(400, "workspace is required for agent mode")
    if mode == RunMode.HARNESS and not req.tasks_file:
        raise HTTPException(400, "tasks_file is required for harness mode")
    
    config = RunConfig(
        mode=mode,
        workspace=req.workspace,
        tasks_file=req.tasks_file,
        model=req.model,
        base_url=req.base_url,
        api_key=req.api_key,
        max_attempts=req.max_attempts,
        timeout=req.timeout,
    )
    
    run = run_manager.create_run(config)
    return run.to_dict()


@app.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    """Get run details."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    
    return run.to_dict()


@app.post("/runs/{run_id}/start")
async def start_run(run_id: str):
    """Start a run."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    
    if not run_manager.start_run(run_id):
        raise HTTPException(400, f"Cannot start run in status: {run.status.value}")
    
    return {"status": "started", "run_id": run_id}


@app.post("/runs/{run_id}/stop")
async def stop_run(run_id: str):
    """Stop a running run."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    if not run_manager.stop_run(run_id):
        raise HTTPException(400, "Cannot stop run")
    
    return {"status": "stopped", "run_id": run_id}


@app.get("/runs/{run_id}/status")
async def get_run_status(run_id: str):
    """Get current run status."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    
    return {
        "id": run.id,
        "status": run.status.value,
        "exit_code": run.exit_code,
        "error": run.error,
    }


# ---- Logs ----

@app.get("/runs/{run_id}/logs")
async def get_logs(
    run_id: str,
    log_type: str = Query("stdout", pattern="^(stdout|stderr)$"),
    tail: int = Query(500, ge=1, le=10000),
):
    """Get log content."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    content = run_manager.get_logs(run_id, log_type, tail)
    return {"content": content}


@app.get("/runs/{run_id}/logs/stream")
async def stream_logs(run_id: str):
    """Stream logs via SSE."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    
    run_dir = run_manager.get_run_dir(run_id)
    stdout_path = run_dir / "stdout.log"
    
    async def generate():
        # Send initial content
        if stdout_path.exists():
            with open(stdout_path, 'r', encoding='utf-8', errors='replace') as f:
                initial = f.read()
            if initial:
                yield await sse_event('log', {'content': initial, 'type': 'initial'})
        
        # Stream new content
        async for event in stream_file_tail(str(stdout_path)):
            yield event
            
            # Check if run is still active
            current_run = run_manager.get_run(run_id)
            if current_run and current_run.status not in (RunStatus.RUNNING, RunStatus.STOPPING):
                yield await sse_event('end', {'status': current_run.status.value})
                break
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---- Ledger ----

@app.get("/runs/{run_id}/ledger")
async def get_ledger(run_id: str):
    """Get parsed ledger entries."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run_dir = run_manager.get_run_dir(run_id)
    ledger_path = run_dir / "ledger.jsonl"
    
    entries = parse_ledger_file(str(ledger_path))
    return {
        "entries": [e.to_dict() for e in entries],
        "summary": get_ledger_summary(entries),
    }


@app.get("/runs/{run_id}/ledger/timeline")
async def get_ledger_timeline(run_id: str):
    """Get ledger as timeline steps."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run_dir = run_manager.get_run_dir(run_id)
    ledger_path = run_dir / "ledger.jsonl"
    
    entries = parse_ledger_file(str(ledger_path))
    timeline = build_timeline(entries)
    
    return {
        "steps": [s.to_dict() for s in timeline],
        "total": len(timeline),
    }


@app.post("/runs/{run_id}/verify", response_model=VerifyResponse)
async def verify_run(run_id: str):
    """Verify ledger hash chain."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run_dir = run_manager.get_run_dir(run_id)
    ledger_path = run_dir / "ledger.jsonl"
    
    entries = parse_ledger_file(str(ledger_path))
    valid, message = verify_ledger_chain(entries)
    
    return VerifyResponse(
        valid=valid,
        message=message,
        entry_count=len(entries),
    )


# ---- Artifacts ----

@app.get("/runs/{run_id}/artifacts/list")
async def list_artifacts(run_id: str):
    """List all artifacts in run directory."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    artifacts = run_manager.list_artifacts(run_id)
    return {"artifacts": artifacts}


@app.get("/runs/{run_id}/artifacts/file")
async def get_artifact_file(
    run_id: str,
    path: str = Query(..., description="Relative path to file"),
):
    """Get artifact file content."""
    if not validate_run_id(run_id):
        raise HTTPException(400, "Invalid run ID")
    
    run_dir = run_manager.get_run_dir(run_id)
    
    # SECURITY: Verify path is confined
    full_path = safe_join(str(run_dir), path)
    if not full_path:
        raise HTTPException(403, "Path traversal not allowed")
    
    file_path = Path(full_path)
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    if not file_path.is_file():
        raise HTTPException(400, "Not a file")
    
    # Check file size
    size = file_path.stat().st_size
    max_inline = 1024 * 1024  # 1MB
    
    # Determine content type
    suffix = file_path.suffix.lower()
    text_extensions = {'.txt', '.log', '.json', '.jsonl', '.md', '.py', '.yaml', '.yml', '.toml', '.diff', '.patch'}
    
    if suffix in text_extensions:
        if size > max_inline:
            # Return truncated content with warning
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(max_inline)
            return {
                "content": content,
                "truncated": True,
                "total_size": size,
                "message": f"File truncated. Total size: {size} bytes",
            }
        else:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return {
                "content": content,
                "truncated": False,
                "total_size": size,
            }
    else:
        # Binary file - return download link
        return FileResponse(
            file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )


# ---- Settings ----

@app.get("/settings")
async def get_settings():
    """Get saved settings."""
    settings = load_settings()
    # Don't expose full API key
    if settings.get('api_key'):
        key = settings['api_key']
        settings['api_key_preview'] = key[:8] + '...' if len(key) > 8 else '***'
        settings['has_api_key'] = True
    else:
        settings['api_key_preview'] = ''
        settings['has_api_key'] = False
    del settings['api_key']
    return settings


@app.post("/settings")
async def save_settings_endpoint(req: SettingsRequest):
    """Save settings."""
    settings = {
        'model': req.model,
        'base_url': req.base_url,
        'api_key': req.api_key,
    }
    save_settings(settings)
    return {"status": "saved"}


# ============ Main ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
