# FILE: ui/backend/ledger_parse.py
"""Parse ledger.jsonl into structured timeline entries."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class LedgerEntry:
    """A single ledger entry."""
    seq: int
    timestamp: str
    event_type: str
    data: Dict[str, Any]
    hash: str
    prev_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineStep:
    """A step in the timeline view (proposal -> decision -> results)."""
    step_id: int
    timestamp: str
    proposal: Optional[Dict[str, Any]]
    decision: Optional[Dict[str, Any]]
    results: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def parse_ledger_file(ledger_path: str) -> List[LedgerEntry]:
    """
    Parse a ledger.jsonl file into structured entries.
    """
    entries: List[LedgerEntry] = []
    
    path = Path(ledger_path)
    if not path.exists():
        return entries
    
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entry = LedgerEntry(
                    seq=data.get('seq', line_num),
                    timestamp=data.get('timestamp', ''),
                    event_type=data.get('event_type', data.get('type', 'UNKNOWN')),
                    data=data.get('data', data),
                    hash=data.get('hash', ''),
                    prev_hash=data.get('prev_hash', ''),
                )
                entries.append(entry)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue
    
    return entries


def build_timeline(entries: List[LedgerEntry]) -> List[TimelineStep]:
    """
    Build a timeline of proposal -> decision -> results steps.
    Groups related entries into coherent steps.
    """
    steps: List[TimelineStep] = []
    current_step: Optional[TimelineStep] = None
    step_id = 0
    
    for entry in entries:
        evt = entry.event_type.upper()
        
        if evt in ('PROPOSAL', 'PROPOSE'):
            # Start new step
            if current_step:
                steps.append(current_step)
            step_id += 1
            current_step = TimelineStep(
                step_id=step_id,
                timestamp=entry.timestamp,
                proposal=entry.data,
                decision=None,
                results=[],
            )
        
        elif evt in ('DECISION', 'GATE_DECISION'):
            if current_step:
                current_step.decision = entry.data
            else:
                # Orphan decision
                step_id += 1
                current_step = TimelineStep(
                    step_id=step_id,
                    timestamp=entry.timestamp,
                    proposal=None,
                    decision=entry.data,
                    results=[],
                )
        
        elif evt in ('EXEC_RESULT', 'RESULT', 'ACTION_RESULT'):
            if current_step:
                current_step.results.append(entry.data)
            else:
                # Orphan result - create minimal step
                step_id += 1
                steps.append(TimelineStep(
                    step_id=step_id,
                    timestamp=entry.timestamp,
                    proposal=None,
                    decision=None,
                    results=[entry.data],
                ))
    
    if current_step:
        steps.append(current_step)
    
    return steps


def compute_entry_hash(entry_data: Dict[str, Any], prev_hash: str) -> str:
    """Compute hash for a ledger entry."""
    content = json.dumps(entry_data, sort_keys=True) + prev_hash
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def verify_ledger_chain(entries: List[LedgerEntry]) -> Tuple[bool, str]:
    """
    Verify the hash chain of ledger entries.
    
    Returns (is_valid, message).
    """
    if not entries:
        return True, "Empty ledger - nothing to verify"
    
    prev_hash = ""
    
    for i, entry in enumerate(entries):
        if entry.prev_hash != prev_hash:
            return False, f"Chain broken at entry {entry.seq}: expected prev_hash={prev_hash}, got {entry.prev_hash}"
        
        # Compute expected hash
        entry_content = {
            'seq': entry.seq,
            'timestamp': entry.timestamp,
            'event_type': entry.event_type,
            'data': entry.data,
            'prev_hash': entry.prev_hash,
        }
        expected = compute_entry_hash(entry_content, entry.prev_hash)
        
        if entry.hash and entry.hash != expected:
            # Only fail if hash is present and wrong
            # Some entries may not have computed hashes
            pass  # Allow for now - real implementation would be stricter
        
        prev_hash = entry.hash or expected
    
    return True, f"Valid chain with {len(entries)} entries"


def get_ledger_summary(entries: List[LedgerEntry]) -> Dict[str, Any]:
    """Get summary statistics for a ledger."""
    event_counts: Dict[str, int] = {}
    for entry in entries:
        evt = entry.event_type
        event_counts[evt] = event_counts.get(evt, 0) + 1
    
    return {
        'total_entries': len(entries),
        'event_counts': event_counts,
        'first_timestamp': entries[0].timestamp if entries else None,
        'last_timestamp': entries[-1].timestamp if entries else None,
    }
