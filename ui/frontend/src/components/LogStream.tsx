// FILE: ui/frontend/src/components/LogStream.tsx
// Real-time log streaming component using SSE

import { useEffect, useRef, useState } from 'react';
import { streamLogs, getLogs } from '../api/client';

interface Props {
    runId: string;
    isRunning: boolean;
}

export function LogStream({ runId, isRunning }: Props) {
    const [logs, setLogs] = useState('');
    const [autoScroll, setAutoScroll] = useState(true);
    const logRef = useRef<HTMLPreElement>(null);
    const cleanupRef = useRef<(() => void) | null>(null);

    useEffect(() => {
        // Load initial logs
        getLogs(runId, 'stdout', 1000).then(({ content }) => {
            setLogs(content);
        });

        // If running, start streaming
        if (isRunning) {
            cleanupRef.current = streamLogs(
                runId,
                (data) => {
                    if (data.content) {
                        setLogs((prev) => prev + data.content);
                    }
                    if (data.status) {
                        setLogs((prev) => prev + `\n[Run ${data.status}]\n`);
                    }
                },
                (error) => {
                    console.error('SSE error:', error);
                }
            );
        }

        return () => {
            if (cleanupRef.current) {
                cleanupRef.current();
            }
        };
    }, [runId, isRunning]);

    useEffect(() => {
        if (autoScroll && logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight;
        }
    }, [logs, autoScroll]);

    function handleScroll() {
        if (logRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = logRef.current;
            const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
            setAutoScroll(isAtBottom);
        }
    }

    function downloadLogs() {
        const blob = new Blob([logs], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${runId}_logs.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }

    return (
        <div className="h-full flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-2 bg-gray-100 border-b">
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-600">
                        {isRunning ? (
                            <span className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                Streaming...
                            </span>
                        ) : (
                            'Log output'
                        )}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <label className="flex items-center gap-1 text-sm text-gray-600">
                        <input
                            type="checkbox"
                            checked={autoScroll}
                            onChange={(e) => setAutoScroll(e.target.checked)}
                            className="rounded"
                        />
                        Auto-scroll
                    </label>
                    <button
                        onClick={downloadLogs}
                        className="px-3 py-1 text-sm bg-white border rounded hover:bg-gray-50"
                    >
                        Download
                    </button>
                </div>
            </div>

            {/* Log content */}
            <pre
                ref={logRef}
                onScroll={handleScroll}
                className="flex-1 overflow-auto p-4 bg-gray-900 text-gray-100 font-mono text-sm whitespace-pre-wrap"
            >
                {logs || 'No log output yet...'}
            </pre>
        </div>
    );
}
