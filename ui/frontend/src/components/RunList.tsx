// FILE: ui/frontend/src/components/RunList.tsx
// Sidebar component showing list of runs

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { Run } from '../types';
import { listRuns } from '../api/client';

const statusColors: Record<string, string> = {
    created: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    stopping: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    stopped: 'bg-orange-100 text-orange-800',
};

interface Props {
    onCreateNew: () => void;
}

export function RunList({ onCreateNew }: Props) {
    const { runId } = useParams();
    const [runs, setRuns] = useState<Run[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadRuns();
        const interval = setInterval(loadRuns, 5000);
        return () => clearInterval(interval);
    }, []);

    async function loadRuns() {
        try {
            const data = await listRuns();
            setRuns(data);
        } catch (err) {
            console.error('Failed to load runs:', err);
        } finally {
            setLoading(false);
        }
    }

    function formatDate(dateStr: string): string {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    return (
        <div className="h-full flex flex-col bg-white border-r border-gray-200">
            {/* Header */}
            <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Runs</h2>
                <button
                    onClick={onCreateNew}
                    className="mt-2 w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
                >
                    + New Run
                </button>
            </div>

            {/* Runs List */}
            <div className="flex-1 overflow-y-auto">
                {loading && (
                    <div className="p-4 text-gray-500 text-sm">Loading runs...</div>
                )}

                {!loading && runs.length === 0 && (
                    <div className="p-4 text-gray-500 text-sm">No runs yet</div>
                )}

                {runs.map((run) => (
                    <Link
                        key={run.id}
                        to={`/run/${run.id}`}
                        className={`block p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors ${run.id === runId ? 'bg-primary-50' : ''
                            }`}
                    >
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-gray-900 truncate">
                                {run.id.slice(0, 20)}...
                            </span>
                            <span
                                className={`px-2 py-0.5 text-xs rounded-full ${statusColors[run.status] || 'bg-gray-100 text-gray-800'
                                    }`}
                            >
                                {run.status}
                            </span>
                        </div>
                        <div className="text-xs text-gray-500">
                            {run.config.mode === 'agent' ? '🔧 Agent' : '📋 Harness'}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                            {formatDate(run.created_at)}
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    );
}
