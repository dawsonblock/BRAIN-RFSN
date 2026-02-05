// ui/frontend/src/hooks/useRunEvents.ts
// React hook for consuming real-time run events via WebSocket

import { useEffect, useRef, useState, useCallback } from 'react';

export interface RunEvent {
    type: string;
    ts: string;
    [key: string]: unknown;
}

export interface UseRunEventsOptions {
    onEvent?: (event: RunEvent) => void;
    reconnectInterval?: number;
    maxEvents?: number;
}

export interface UseRunEventsResult {
    events: RunEvent[];
    connected: boolean;
    error: string | null;
    clearEvents: () => void;
}

export function useRunEvents(
    runId: string | null,
    options: UseRunEventsOptions = {}
): UseRunEventsResult {
    const { onEvent, reconnectInterval = 3000, maxEvents = 200 } = options;
    const [events, setEvents] = useState<RunEvent[]>([]);
    const [connected, setConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const clearEvents = useCallback(() => {
        setEvents([]);
    }, []);

    const connect = useCallback(() => {
        if (!runId) return;

        // Close existing connection
        if (wsRef.current) {
            wsRef.current.close();
        }

        // Clear any pending reconnect
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/run/${runId}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setConnected(true);
                setError(null);
            };

            ws.onmessage = (evt) => {
                try {
                    const event: RunEvent = JSON.parse(evt.data);
                    setEvents((prev) => {
                        const updated = [...prev, event];
                        // Limit stored events
                        return updated.slice(-maxEvents);
                    });
                    if (onEvent) {
                        onEvent(event);
                    }
                } catch (e) {
                    console.warn('Failed to parse WebSocket message:', e);
                }
            };

            ws.onerror = () => {
                setError('WebSocket error');
            };

            ws.onclose = () => {
                setConnected(false);
                wsRef.current = null;
                // Schedule reconnect
                reconnectTimerRef.current = setTimeout(() => {
                    connect();
                }, reconnectInterval);
            };
        } catch (e) {
            setError(`Failed to connect: ${e}`);
        }
    }, [runId, onEvent, reconnectInterval, maxEvents]);

    useEffect(() => {
        if (runId) {
            connect();
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
        };
    }, [runId, connect]);

    return { events, connected, error, clearEvents };
}

export default useRunEvents;
