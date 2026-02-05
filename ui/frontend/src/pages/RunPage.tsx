// FILE: ui/frontend/src/pages/RunPage.tsx
// Main run control page with start/stop and status

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import type { Run, VerifyResult } from '../types';
import { getRun, startRun, stopRun, verifyRun } from '../api/client';

export function RunPage() {
    const { runId } = useParams<{ runId: string }>();
    const [run, setRun] = useState<Run | null>(null);
    const [loading, setLoading] = useState(true);
    const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
    const [verifying, setVerifying] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => {
        if (runId) {
            loadRun();
            const interval = setInterval(loadRun, 3000);
            return () => clearInterval(interval);
        }
    }, [runId]);

    async function loadRun() {
        if (!runId) return;
        try {
            const data = await getRun(runId);
            setRun(data);
        } catch (err) {
            console.error('Failed to load run:', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleStart() {
        if (!runId) return;
        setActionLoading(true);
        try {
            await startRun(runId);
            await loadRun();
        } catch (err) {
            console.error('Failed to start run:', err);
            alert(`Failed to start: ${err}`);
        } finally {
            setActionLoading(false);
        }
    }

    async function handleStop() {
        if (!runId) return;
        setActionLoading(true);
        try {
            await stopRun(runId);
            await loadRun();
        } catch (err) {
            console.error('Failed to stop run:', err);
        } finally {
            setActionLoading(false);
        }
    }

    async function handleVerify() {
        if (!runId) return;
        setVerifying(true);
        try {
            const result = await verifyRun(runId);
            setVerifyResult(result);
        } catch (err) {
            console.error('Failed to verify:', err);
        } finally {
            setVerifying(false);
        }
    }

    const statusColors: Record<string, string> = {
        created: 'bg-gray-500',
        running: 'bg-blue-500',
        stopping: 'bg-yellow-500',
        completed: 'bg-green-500',
        failed: 'bg-red-500',
        stopped: 'bg-orange-500',
    };

    if (loading) {
        return <div className="p-8 text-gray-500">Loading run...</div>;
    }

    if (!run) {
        return <div className="p-8 text-gray-500">Run not found</div>;
    }


    const canStart = run.status === 'created';
    const canStop = run.status === 'running';

    return (
        <div className="p-6 max-w-4xl">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-2xl font-bold text-gray-900">Run Details</h1>
                    <span
                        className={`px-3 py-1 rounded-full text-white text-sm font-medium ${statusColors[run.status] || 'bg-gray-500'
                            }`}
                    >
                        {run.status.toUpperCase()}
                    </span>
                </div>
                <p className="text-gray-500 font-mono text-sm">{run.id}</p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mb-6">
                {canStart && (
                    <button
                        onClick={handleStart}
                        disabled={actionLoading}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                        ▶ Start Run
                    </button>
                )}
                {canStop && (
                    <button
                        onClick={handleStop}
                        disabled={actionLoading}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                    >
                        ⏹ Stop Run
                    </button>
                )}
                <button
                    onClick={handleVerify}
                    disabled={verifying}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                    {verifying ? '...' : '🔍 Verify Ledger'}
                </button>
            </div>

            {/* Verify Result */}
            {verifyResult && (
                <div
                    className={`p-4 rounded-lg mb-6 ${verifyResult.valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                        }`}
                >
                    <div className="flex items-center gap-2">
                        <span className="text-xl">{verifyResult.valid ? '✅' : '❌'}</span>
                        <span className="font-medium">
                            {verifyResult.valid ? 'Ledger Valid' : 'Ledger Invalid'}
                        </span>
                    </div>
                    <p className="text-sm mt-1 text-gray-600">{verifyResult.message}</p>
                    <p className="text-sm text-gray-500">Entries: {verifyResult.entry_count}</p>
                </div>
            )}

            {/* Configuration */}
            <div className="bg-white border rounded-lg p-4 mb-6">
                <h2 className="text-lg font-semibold mb-4">Configuration</h2>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <div className="text-sm text-gray-500">Mode</div>
                        <div className="font-medium">
                            {run.config.mode === 'agent' ? '🔧 Single Agent' : '📋 Multi-Task Harness'}
                        </div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Model</div>
                        <div className="font-medium">{run.config.model}</div>
                    </div>
                    {run.config.workspace && (
                        <div className="col-span-2">
                            <div className="text-sm text-gray-500">Workspace</div>
                            <div className="font-mono text-sm">{run.config.workspace}</div>
                        </div>
                    )}
                    {run.config.tasks_file && (
                        <div className="col-span-2">
                            <div className="text-sm text-gray-500">Tasks File</div>
                            <div className="font-mono text-sm">{run.config.tasks_file}</div>
                        </div>
                    )}
                    <div>
                        <div className="text-sm text-gray-500">Max Attempts</div>
                        <div className="font-medium">{run.config.max_attempts}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Timeout</div>
                        <div className="font-medium">{run.config.timeout}s</div>
                    </div>
                </div>
            </div>

            {/* Timing */}
            <div className="bg-white border rounded-lg p-4">
                <h2 className="text-lg font-semibold mb-4">Timing</h2>
                <div className="grid grid-cols-3 gap-4">
                    <div>
                        <div className="text-sm text-gray-500">Created</div>
                        <div className="font-medium text-sm">{run.created_at || '-'}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Started</div>
                        <div className="font-medium text-sm">{run.started_at || '-'}</div>
                    </div>
                    <div>
                        <div className="text-sm text-gray-500">Ended</div>
                        <div className="font-medium text-sm">{run.ended_at || '-'}</div>
                    </div>
                </div>
                {run.exit_code !== null && (
                    <div className="mt-4">
                        <div className="text-sm text-gray-500">Exit Code</div>
                        <div className={`font-medium ${run.exit_code === 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {run.exit_code}
                        </div>
                    </div>
                )}
                {run.error && (
                    <div className="mt-4">
                        <div className="text-sm text-gray-500">Error</div>
                        <div className="font-mono text-sm text-red-600">{run.error}</div>
                    </div>
                )}
            </div>
        </div>
    );
}
