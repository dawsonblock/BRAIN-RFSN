// FILE: ui/frontend/src/types.ts
// TypeScript types for RFSN Control Center

export type RunMode = 'agent' | 'harness';

export type RunStatus =
    | 'created'
    | 'running'
    | 'stopping'
    | 'completed'
    | 'failed'
    | 'stopped';

export interface RunConfig {
    mode: RunMode;
    workspace: string;
    tasks_file: string;
    model: string;
    base_url: string;
    api_key: string;
    max_attempts: number;
    timeout: number;
}

export interface Run {
    id: string;
    config: RunConfig;
    status: RunStatus;
    created_at: string;
    started_at: string;
    ended_at: string;
    exit_code: number | null;
    error: string;
}

export interface CreateRunRequest {
    mode: RunMode;
    workspace?: string;
    tasks_file?: string;
    model?: string;
    base_url?: string;
    api_key?: string;
    max_attempts?: number;
    timeout?: number;
}

export interface LedgerEntry {
    seq: number;
    timestamp: string;
    event_type: string;
    data: Record<string, unknown>;
    hash: string;
    prev_hash: string;
}

export interface TimelineStep {
    step_id: number;
    timestamp: string;
    proposal: Record<string, unknown> | null;
    decision: Record<string, unknown> | null;
    results: Record<string, unknown>[];
}

export interface LedgerSummary {
    total_entries: number;
    event_counts: Record<string, number>;
    first_timestamp: string | null;
    last_timestamp: string | null;
}

export interface Artifact {
    path: string;
    type: 'file' | 'directory';
    size?: number;
    modified?: string;
}

export interface VerifyResult {
    valid: boolean;
    message: string;
    entry_count: number;
}

export interface Settings {
    model: string;
    base_url: string;
    api_key_preview: string;
    has_api_key: boolean;
}

export interface LogContent {
    content: string;
    type?: string;
}

export interface FileContent {
    content: string;
    truncated: boolean;
    total_size: number;
    message?: string;
}
