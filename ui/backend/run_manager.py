# FILE: ui/backend/run_manager.py
"""Run manager for spawning and controlling agent/harness processes."""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .sse import sse_manager


class RunMode(str, Enum):
    AGENT = "agent"
    HARNESS = "harness"


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class RunConfig:
    """Configuration for a run."""
    mode: RunMode
    workspace: str = ""
    tasks_file: str = ""
    model: str = "gpt-4"
    base_url: str = ""
    api_key: str = ""
    max_attempts: int = 6
    timeout: int = 3600  # 1 hour default
    extra_env: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['mode'] = self.mode.value
        # Don't expose API key in responses
        d['api_key'] = '***' if self.api_key else ''
        return d


@dataclass
class Run:
    """A single run instance."""
    id: str
    config: RunConfig
    status: RunStatus = RunStatus.CREATED
    created_at: str = ""
    started_at: str = ""
    ended_at: str = ""
    exit_code: Optional[int] = None
    error: str = ""
    
    # Internal state (not serialized)
    process: Optional[subprocess.Popen] = field(default=None, repr=False)
    log_thread: Optional[threading.Thread] = field(default=None, repr=False)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'config': self.config.to_dict(),
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'exit_code': self.exit_code,
            'error': self.error,
        }


class RunManager:
    """Manages all runs and their lifecycle."""
    
    def __init__(self, runs_dir: str = "./ui_runs"):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.runs: Dict[str, Run] = {}
        self._load_existing_runs()
    
    def _load_existing_runs(self):
        """Load metadata for existing runs from disk."""
        for run_dir in self.runs_dir.iterdir():
            if run_dir.is_dir():
                meta_path = run_dir / "meta.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, 'r') as f:
                            data = json.load(f)
                        config = RunConfig(
                            mode=RunMode(data['config']['mode']),
                            workspace=data['config'].get('workspace', ''),
                            tasks_file=data['config'].get('tasks_file', ''),
                            model=data['config'].get('model', 'gpt-4'),
                            base_url=data['config'].get('base_url', ''),
                            max_attempts=data['config'].get('max_attempts', 6),
                            timeout=data['config'].get('timeout', 3600),
                        )
                        run = Run(
                            id=data['id'],
                            config=config,
                            status=RunStatus(data.get('status', 'completed')),
                            created_at=data.get('created_at', ''),
                            started_at=data.get('started_at', ''),
                            ended_at=data.get('ended_at', ''),
                            exit_code=data.get('exit_code'),
                            error=data.get('error', ''),
                        )
                        self.runs[run.id] = run
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
    
    def get_run_dir(self, run_id: str) -> Path:
        """Get the directory for a run."""
        return self.runs_dir / run_id
    
    def create_run(self, config: RunConfig) -> Run:
        """Create a new run."""
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        run = Run(id=run_id, config=config)
        
        # Create run directory
        run_dir = self.get_run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        self._save_run_meta(run)
        
        self.runs[run_id] = run
        return run
    
    def _save_run_meta(self, run: Run):
        """Save run metadata to disk."""
        run_dir = self.get_run_dir(run.id)
        meta_path = run_dir / "meta.json"
        with open(meta_path, 'w') as f:
            json.dump(run.to_dict(), f, indent=2)
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID."""
        return self.runs.get(run_id)
    
    def list_runs(self) -> List[Run]:
        """List all runs, sorted by creation time (newest first)."""
        return sorted(
            self.runs.values(),
            key=lambda r: r.created_at,
            reverse=True
        )
    
    def start_run(self, run_id: str) -> bool:
        """Start a run."""
        run = self.runs.get(run_id)
        if not run:
            return False
        
        if run.status == RunStatus.RUNNING:
            return False
        
        run_dir = self.get_run_dir(run_id)
        
        # Build command
        if run.config.mode == RunMode.AGENT:
            cmd = [
                "python", "-u", "rfsn_swe_agent.py",
                "--workspace", run.config.workspace,
                "--task-id", f"ui_{run_id}",
                "--max-attempts", str(run.config.max_attempts),
            ]
        else:  # HARNESS
            cmd = [
                "python", "-u", "swebench_runner.py",
                "--tasks-file", run.config.tasks_file,
                "--output-dir", str(run_dir / "harness_output"),
            ]
        
        # Build environment
        env = os.environ.copy()
        env.update({
            'RFSN_LEDGER_PATH': str(run_dir / "ledger.jsonl"),
            'RFSN_RUN_DIR': str(run_dir),
            'RFSN_MODEL': run.config.model,
        })
        if run.config.base_url:
            env['OPENAI_API_BASE'] = run.config.base_url
            env['OPENAI_BASE_URL'] = run.config.base_url
        if run.config.api_key:
            env['OPENAI_API_KEY'] = run.config.api_key
        env.update(run.config.extra_env)
        
        # Open log files
        stdout_path = run_dir / "stdout.log"
        stderr_path = run_dir / "stderr.log"
        
        try:
            stdout_file = open(stdout_path, 'w')
            stderr_file = open(stderr_path, 'w')
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=stdout_file,
                stderr=stderr_file,
                env=env,
                cwd=str(Path(__file__).parent.parent.parent),  # Repo root
                start_new_session=True,
            )
            
            run.process = process
            run.status = RunStatus.RUNNING
            run.started_at = datetime.utcnow().isoformat() + "Z"
            self._save_run_meta(run)
            
            # Start monitoring thread
            run.log_thread = threading.Thread(
                target=self._monitor_process,
                args=(run, stdout_file, stderr_file),
                daemon=True
            )
            run.log_thread.start()
            
            return True
            
        except Exception as e:
            run.status = RunStatus.FAILED
            run.error = str(e)
            self._save_run_meta(run)
            return False
    
    def _monitor_process(self, run: Run, stdout_file, stderr_file):
        """Monitor a running process."""
        try:
            # Wait for process to complete
            exit_code = run.process.wait(timeout=run.config.timeout)
            run.exit_code = exit_code
            run.status = RunStatus.COMPLETED if exit_code == 0 else RunStatus.FAILED
        except subprocess.TimeoutExpired:
            run.process.kill()
            run.exit_code = -1
            run.status = RunStatus.FAILED
            run.error = "Timeout exceeded"
        except Exception as e:
            run.status = RunStatus.FAILED
            run.error = str(e)
        finally:
            run.ended_at = datetime.utcnow().isoformat() + "Z"
            stdout_file.close()
            stderr_file.close()
            self._save_run_meta(run)
    
    def stop_run(self, run_id: str) -> bool:
        """Stop a running run."""
        run = self.runs.get(run_id)
        if not run or run.status != RunStatus.RUNNING:
            return False
        
        if run.process:
            run.status = RunStatus.STOPPING
            try:
                # Try graceful shutdown first
                os.killpg(os.getpgid(run.process.pid), signal.SIGTERM)
                time.sleep(2)
                if run.process.poll() is None:
                    os.killpg(os.getpgid(run.process.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            
            run.status = RunStatus.STOPPED
            run.ended_at = datetime.utcnow().isoformat() + "Z"
            self._save_run_meta(run)
            return True
        
        return False
    
    def get_logs(self, run_id: str, log_type: str = "stdout", tail: int = 500) -> str:
        """Get log content for a run."""
        run_dir = self.get_run_dir(run_id)
        log_file = run_dir / f"{log_type}.log"
        
        if not log_file.exists():
            return ""
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Return tail
            lines = content.split('\n')
            if len(lines) > tail:
                return '\n'.join(lines[-tail:])
            return content
        except (OSError, IOError):
            return ""
    
    def list_artifacts(self, run_id: str) -> List[Dict[str, Any]]:
        """List all artifacts in a run directory."""
        run_dir = self.get_run_dir(run_id)
        if not run_dir.exists():
            return []
        
        artifacts = []
        
        def walk_dir(path: Path, prefix: str = ""):
            for item in sorted(path.iterdir()):
                rel_path = prefix + item.name if prefix else item.name
                
                if item.is_file():
                    artifacts.append({
                        'path': rel_path,
                        'type': 'file',
                        'size': item.stat().st_size,
                        'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    })
                elif item.is_dir():
                    artifacts.append({
                        'path': rel_path,
                        'type': 'directory',
                    })
                    walk_dir(item, rel_path + "/")
        
        walk_dir(run_dir)
        return artifacts


# Global run manager instance
run_manager = RunManager()
