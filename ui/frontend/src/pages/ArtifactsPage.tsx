// FILE: ui/frontend/src/pages/ArtifactsPage.tsx
// Artifacts file browser page

import { useParams } from 'react-router-dom';
import { ArtifactTree } from '../components/ArtifactTree';

export function ArtifactsPage() {
    const { runId } = useParams<{ runId: string }>();

    if (!runId) {
        return <div className="p-8 text-gray-500">Select a run to view artifacts</div>;
    }

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b bg-white">
                <h1 className="text-xl font-bold">Artifacts</h1>
                <p className="text-sm text-gray-500 font-mono">{runId}</p>
            </div>
            <div className="flex-1 overflow-hidden">
                <ArtifactTree runId={runId} />
            </div>
        </div>
    );
}
