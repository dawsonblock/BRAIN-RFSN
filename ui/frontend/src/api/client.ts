// FILE: ui/frontend/src/api/client.ts
// Typed API client for RFSN Control Center

import type {
    Run,
    CreateRunRequest,
    LedgerEntry,
    LedgerSummary,
    TimelineStep,
    Artifact,
    VerifyResult,
    Settings,
    FileContent,
} from '../types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ============ Runs ============

export async function listRuns(): Promise<Run[]> {
    return fetchJSON<Run[]>('/runs');
}

export async function createRun(config: CreateRunRequest): Promise<Run> {
    return fetchJSON<Run>('/runs/create', {
        method: 'POST',
        body: JSON.stringify(config),
    });
}

export async function getRun(runId: string): Promise<Run> {
    return fetchJSON<Run>(`/runs/${runId}`);
}

export async function startRun(runId: string): Promise<{ status: string }> {
    return fetchJSON<{ status: string }>(`/runs/${runId}/start`, {
        method: 'POST',
    });
}

export async function stopRun(runId: string): Promise<{ status: string }> {
    return fetchJSON<{ status: string }>(`/runs/${runId}/stop`, {
        method: 'POST',
    });
}

export async function getRunStatus(runId: string): Promise<{
    id: string;
    status: string;
    exit_code: number | null;
    error: string;
}> {
    return fetchJSON(`/runs/${runId}/status`);
}

// ============ Logs ============

export async function getLogs(
    runId: string,
    logType: 'stdout' | 'stderr' = 'stdout',
    tail: number = 500
): Promise<{ content: string }> {
    return fetchJSON(`/runs/${runId}/logs?log_type=${logType}&tail=${tail}`);
}

export function streamLogs(
    runId: string,
    onMessage: (data: { content?: string; status?: string; type?: string }) => void,
    onError?: (error: Event) => void
): () => void {
    const eventSource = new EventSource(`${API_BASE}/runs/${runId}/logs/stream`);

    eventSource.addEventListener('log', (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
        } catch {
            onMessage({ content: event.data });
        }
    });

    eventSource.addEventListener('end', (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage({ status: data.status });
        } catch {
            // Ignore
        }
        eventSource.close();
    });

    eventSource.onerror = (error) => {
        if (onError) onError(error);
        eventSource.close();
    };

    return () => eventSource.close();
}

// ============ Ledger ============

export async function getLedger(runId: string): Promise<{
    entries: LedgerEntry[];
    summary: LedgerSummary;
}> {
    return fetchJSON(`/runs/${runId}/ledger`);
}

export async function getLedgerTimeline(runId: string): Promise<{
    steps: TimelineStep[];
    total: number;
}> {
    return fetchJSON(`/runs/${runId}/ledger/timeline`);
}

export async function verifyRun(runId: string): Promise<VerifyResult> {
    return fetchJSON<VerifyResult>(`/runs/${runId}/verify`, {
        method: 'POST',
    });
}

// ============ Artifacts ============

export async function listArtifacts(runId: string): Promise<{
    artifacts: Artifact[];
}> {
    return fetchJSON(`/runs/${runId}/artifacts/list`);
}

export async function getArtifactFile(
    runId: string,
    path: string
): Promise<FileContent> {
    return fetchJSON(`/runs/${runId}/artifacts/file?path=${encodeURIComponent(path)}`);
}

// ============ Settings ============

export async function getSettings(): Promise<Settings> {
    return fetchJSON<Settings>('/settings');
}

export async function saveSettings(settings: {
    model: string;
    base_url: string;
    api_key: string;
}): Promise<{ status: string }> {
    return fetchJSON<{ status: string }>('/settings', {
        method: 'POST',
        body: JSON.stringify(settings),
    });
}
