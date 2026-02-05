// FILE: ui/frontend/src/pages/LedgerPage.tsx
// Ledger timeline page

import { useParams } from 'react-router-dom';
import { LedgerTimeline } from '../components/LedgerTimeline';

export function LedgerPage() {
    const { runId } = useParams<{ runId: string }>();

    if (!runId) {
        return <div className="p-8 text-gray-500">Select a run to view ledger</div>;
    }

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b bg-white">
                <h1 className="text-xl font-bold">Ledger Timeline</h1>
                <p className="text-sm text-gray-500 font-mono">{runId}</p>
            </div>
            <div className="flex-1 overflow-y-auto bg-gray-50">
                <LedgerTimeline runId={runId} />
            </div>
        </div>
    );
}
