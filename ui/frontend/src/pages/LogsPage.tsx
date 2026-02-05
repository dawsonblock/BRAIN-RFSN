// FILE: ui/frontend/src/pages/LogsPage.tsx
// Live log streaming page

import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { LogStream } from '../components/LogStream';
import { getRun } from '../api/client';
import type { Run } from '../types';

export function LogsPage() {
    const { runId } = useParams<{ runId: string }>();
    const [run, setRun] = useState<Run | null>(null);

    useEffect(() => {
        if (runId) {
            loadRun();
            const interval = setInterval(loadRun, 5000);
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
        }
    }

    if (!runId) {
        return <div className="p-8 text-gray-500">Select a run to view logs</div>;
    }

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b bg-white">
                <h1 className="text-xl font-bold">Live Logs</h1>
                <p className="text-sm text-gray-500 font-mono">{runId}</p>
            </div>
            <div className="flex-1 overflow-hidden">
                <LogStream runId={runId} isRunning={run?.status === 'running'} />
            </div>
        </div>
    );
}
