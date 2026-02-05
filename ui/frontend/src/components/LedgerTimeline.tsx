// FILE: ui/frontend/src/components/LedgerTimeline.tsx
// Timeline view of ledger entries (proposal -> decision -> results)

import { useEffect, useState } from 'react';
import type { TimelineStep } from '../types';
import { getLedgerTimeline } from '../api/client';

interface Props {
    runId: string;
}

export function LedgerTimeline({ runId }: Props) {
    const [steps, setSteps] = useState<TimelineStep[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

    useEffect(() => {
        loadTimeline();
    }, [runId]);

    async function loadTimeline() {
        setLoading(true);
        try {
            const data = await getLedgerTimeline(runId);
            setSteps(data.steps);
        } catch (err) {
            console.error('Failed to load timeline:', err);
        } finally {
            setLoading(false);
        }
    }

    function toggleStep(stepId: number) {
        setExpandedSteps((prev) => {
            const next = new Set(prev);
            if (next.has(stepId)) {
                next.delete(stepId);
            } else {
                next.add(stepId);
            }
            return next;
        });
    }

    function formatJSON(obj: unknown, maxLength = 500): string {
        const str = JSON.stringify(obj, null, 2);
        if (str.length > maxLength) {
            return str.slice(0, maxLength) + '...';
        }
        return str;
    }

    function getDecisionBadge(decision: Record<string, unknown> | null) {
        if (!decision) return null;
        const allowed = decision.allowed as boolean;
        return (
            <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${allowed
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
            >
                {allowed ? 'ALLOWED' : 'DENIED'}
            </span>
        );
    }

    function getActionTypes(proposal: Record<string, unknown> | null): string[] {
        if (!proposal) return [];
        const actions = proposal.actions as Array<{ type?: string }>;
        if (Array.isArray(actions)) {
            return actions.map((a) => a.type || 'UNKNOWN');
        }
        return [];
    }

    if (loading) {
        return (
            <div className="p-8 text-center text-gray-500">Loading timeline...</div>
        );
    }

    if (steps.length === 0) {
        return (
            <div className="p-8 text-center text-gray-500">
                No ledger entries yet. Run the agent to see the timeline.
            </div>
        );
    }

    return (
        <div className="p-4 space-y-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Timeline ({steps.length} steps)</h3>
                <button
                    onClick={loadTimeline}
                    className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
                >
                    Refresh
                </button>
            </div>

            {steps.map((step) => {
                const isExpanded = expandedSteps.has(step.step_id);
                const actionTypes = getActionTypes(step.proposal);

                return (
                    <div
                        key={step.step_id}
                        className="border rounded-lg bg-white shadow-sm overflow-hidden"
                    >
                        {/* Header */}
                        <button
                            onClick={() => toggleStep(step.step_id)}
                            className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <span className="w-8 h-8 flex items-center justify-center bg-primary-100 text-primary-700 rounded-full text-sm font-medium">
                                    {step.step_id}
                                </span>
                                <div className="text-left">
                                    <div className="flex items-center gap-2">
                                        {actionTypes.map((type, i) => (
                                            <span
                                                key={i}
                                                className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-mono"
                                            >
                                                {type}
                                            </span>
                                        ))}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                        {step.timestamp}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                {getDecisionBadge(step.decision)}
                                <svg
                                    className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''
                                        }`}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M19 9l-7 7-7-7"
                                    />
                                </svg>
                            </div>
                        </button>

                        {/* Expanded content */}
                        {isExpanded && (
                            <div className="border-t px-4 py-3 space-y-3 bg-gray-50">
                                {/* Proposal */}
                                {step.proposal && (
                                    <div>
                                        <div className="text-xs font-semibold text-gray-600 mb-1">
                                            PROPOSAL
                                        </div>
                                        <pre className="p-2 bg-white border rounded text-xs overflow-x-auto">
                                            {formatJSON(step.proposal)}
                                        </pre>
                                    </div>
                                )}

                                {/* Decision */}
                                {step.decision && (
                                    <div>
                                        <div className="text-xs font-semibold text-gray-600 mb-1">
                                            DECISION
                                        </div>
                                        <pre className="p-2 bg-white border rounded text-xs overflow-x-auto">
                                            {formatJSON(step.decision)}
                                        </pre>
                                    </div>
                                )}

                                {/* Results */}
                                {step.results.length > 0 && (
                                    <div>
                                        <div className="text-xs font-semibold text-gray-600 mb-1">
                                            RESULTS ({step.results.length})
                                        </div>
                                        {step.results.map((result, i) => (
                                            <pre
                                                key={i}
                                                className="p-2 bg-white border rounded text-xs overflow-x-auto mb-2"
                                            >
                                                {formatJSON(result)}
                                            </pre>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
