// FILE: ui/frontend/src/pages/NewRunModal.tsx
// Modal for creating new runs

import { useState } from 'react';
import type { CreateRunRequest } from '../types';
import { createRun, startRun } from '../api/client';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onCreated: (runId: string) => void;
}

export function NewRunModal({ isOpen, onClose, onCreated }: Props) {
    const [mode, setMode] = useState<'agent' | 'harness'>('agent');
    const [workspace, setWorkspace] = useState('');
    const [tasksFile, setTasksFile] = useState('');
    const [model, setModel] = useState('gpt-4');
    const [maxAttempts, setMaxAttempts] = useState(6);
    const [timeout, setTimeout] = useState(3600);
    const [autoStart, setAutoStart] = useState(true);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState('');

    if (!isOpen) return null;

    async function handleCreate() {
        setError('');

        // Validation
        if (mode === 'agent' && !workspace.trim()) {
            setError('Workspace path is required');
            return;
        }
        if (mode === 'harness' && !tasksFile.trim()) {
            setError('Tasks file path is required');
            return;
        }

        setCreating(true);
        try {
            const config: CreateRunRequest = {
                mode,
                workspace: workspace.trim(),
                tasks_file: tasksFile.trim(),
                model,
                max_attempts: maxAttempts,
                timeout,
            };

            const run = await createRun(config);

            if (autoStart) {
                await startRun(run.id);
            }

            onCreated(run.id);
            onClose();

            // Reset form
            setWorkspace('');
            setTasksFile('');
        } catch (err) {
            setError(String(err));
        } finally {
            setCreating(false);
        }
    }

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
                {/* Header */}
                <div className="p-4 border-b flex items-center justify-between">
                    <h2 className="text-xl font-bold">New Run</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Body */}
                <div className="p-4 space-y-4">
                    {/* Mode toggle */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Mode
                        </label>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setMode('agent')}
                                className={`flex-1 py-2 px-4 rounded-lg border ${mode === 'agent'
                                    ? 'bg-primary-50 border-primary-500 text-primary-700'
                                    : 'bg-gray-50 border-gray-300'
                                    }`}
                            >
                                🔧 Single Agent
                            </button>
                            <button
                                onClick={() => setMode('harness')}
                                className={`flex-1 py-2 px-4 rounded-lg border ${mode === 'harness'
                                    ? 'bg-primary-50 border-primary-500 text-primary-700'
                                    : 'bg-gray-50 border-gray-300'
                                    }`}
                            >
                                📋 Multi-Task Harness
                            </button>
                        </div>
                    </div>

                    {/* Agent-specific */}
                    {mode === 'agent' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Workspace Path *
                            </label>
                            <input
                                type="text"
                                value={workspace}
                                onChange={(e) => setWorkspace(e.target.value)}
                                placeholder="/path/to/repo"
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Absolute path to the git repository
                            </p>
                        </div>
                    )}

                    {/* Harness-specific */}
                    {mode === 'harness' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Tasks File *
                            </label>
                            <input
                                type="text"
                                value={tasksFile}
                                onChange={(e) => setTasksFile(e.target.value)}
                                placeholder="/path/to/tasks.json"
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                JSON file with task definitions
                            </p>
                        </div>
                    )}

                    {/* Model */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Model
                        </label>
                        <select
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            aria-label="LLM Model"
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                        >
                            <option value="gpt-4">GPT-4</option>
                            <option value="gpt-4-turbo">GPT-4 Turbo</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            <option value="claude-3-opus">Claude 3 Opus</option>
                            <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                        </select>
                    </div>

                    {/* Advanced */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Max Attempts
                            </label>
                            <input
                                type="number"
                                value={maxAttempts}
                                onChange={(e) => setMaxAttempts(parseInt(e.target.value) || 6)}
                                min={1}
                                max={20}
                                aria-label="Maximum attempts"
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Timeout (seconds)
                            </label>
                            <input
                                type="number"
                                value={timeout}
                                onChange={(e) => setTimeout(parseInt(e.target.value) || 3600)}
                                min={60}
                                max={86400}
                                aria-label="Timeout in seconds"
                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                            />
                        </div>
                    </div>

                    {/* Auto-start */}
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoStart}
                            onChange={(e) => setAutoStart(e.target.checked)}
                            className="rounded"
                        />
                        <span className="text-sm text-gray-700">Start run immediately</span>
                    </label>

                    {/* Error */}
                    {error && (
                        <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                            {error}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={creating}
                        className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium"
                    >
                        {creating ? 'Creating...' : autoStart ? 'Create & Start' : 'Create'}
                    </button>
                </div>
            </div>
        </div>
    );
}
