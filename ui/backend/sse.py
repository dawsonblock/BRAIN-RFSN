# FILE: ui/backend/sse.py
"""Server-Sent Events helpers."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict


async def sse_event(
    event: str,
    data: Any,
    id: str = None
) -> str:
    """Format a single SSE event."""
    lines = []
    if id:
        lines.append(f"id: {id}")
    lines.append(f"event: {event}")
    
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data)
    else:
        data_str = str(data)
    
    # SSE requires each data line to be prefixed
    for line in data_str.split('\n'):
        lines.append(f"data: {line}")
    
    lines.append("")  # Empty line terminates event
    return "\n".join(lines) + "\n"


async def stream_file_tail(
    filepath: str,
    max_lines: int = 100,
    poll_interval: float = 0.5
) -> AsyncGenerator[str, None]:
    """
    Stream the tail of a file, yielding new lines as they appear.
    """
    import os
    from pathlib import Path
    
    path = Path(filepath)
    last_pos = 0
    last_size = 0
    
    while True:
        try:
            if path.exists():
                current_size = path.stat().st_size
                
                if current_size > last_size:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        new_content = f.read()
                        last_pos = f.tell()
                        last_size = current_size
                        
                        if new_content:
                            yield await sse_event('log', {'content': new_content})
        except (OSError, IOError):
            pass
        
        await asyncio.sleep(poll_interval)


async def send_heartbeat() -> str:
    """Send a heartbeat comment to keep connection alive."""
    return ": heartbeat\n\n"


class SSEManager:
    """Manage SSE connections for a run."""
    
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
    
    def register(self, run_id: str) -> asyncio.Queue:
        """Register a new SSE listener for a run."""
        if run_id not in self._queues:
            self._queues[run_id] = asyncio.Queue()
        return self._queues[run_id]
    
    async def broadcast(self, run_id: str, event: str, data: Any):
        """Broadcast an event to all listeners for a run."""
        if run_id in self._queues:
            msg = await sse_event(event, data)
            await self._queues[run_id].put(msg)
    
    def unregister(self, run_id: str):
        """Unregister SSE listener for a run."""
        self._queues.pop(run_id, None)


# Global SSE manager
sse_manager = SSEManager()
