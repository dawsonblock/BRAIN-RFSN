// FILE: ui/frontend/src/pages/SettingsPage.tsx
// LLM and policy settings page

import { useEffect, useState } from 'react';
import { getSettings, saveSettings } from '../api/client';

export function SettingsPage() {
    const [model, setModel] = useState('gpt-4');
    const [baseUrl, setBaseUrl] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [hasExistingKey, setHasExistingKey] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        loadSettings();
    }, []);

    async function loadSettings() {
        try {
            const data = await getSettings();
            setModel(data.model);
            setBaseUrl(data.base_url);
            setHasExistingKey(data.has_api_key);
        } catch (err) {
            console.error('Failed to load settings:', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleSave() {
        setSaving(true);
        setSaved(false);
        try {
            await saveSettings({
                model,
                base_url: baseUrl,
                api_key: apiKey,
            });
            setSaved(true);
            setApiKey('');
            setHasExistingKey(!!apiKey || hasExistingKey);
            setTimeout(() => setSaved(false), 3000);
        } catch (err) {
            console.error('Failed to save settings:', err);
            alert('Failed to save settings');
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return <div className="p-8 text-gray-500">Loading settings...</div>;
    }

    return (
        <div className="p-6 max-w-2xl">
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

            <div className="bg-white border rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">LLM Configuration</h2>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Model
                        </label>
                        <select
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        >
                            <option value="gpt-4">GPT-4</option>
                            <option value="gpt-4-turbo">GPT-4 Turbo</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            <option value="claude-3-opus">Claude 3 Opus</option>
                            <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                            <option value="deepseek-coder">DeepSeek Coder</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            API Base URL (optional)
                        </label>
                        <input
                            type="url"
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            placeholder="https://api.openai.com/v1"
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Leave empty for default OpenAI endpoint
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            API Key
                        </label>
                        <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder={hasExistingKey ? '••••••••' : 'sk-...'}
                            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        />
                        {hasExistingKey && !apiKey && (
                            <p className="text-xs text-green-600 mt-1">
                                ✓ API key is configured
                            </p>
                        )}
                        <p className="text-xs text-gray-500 mt-1">
                            Stored locally in ./ui_runs/.settings.json
                        </p>
                    </div>
                </div>
            </div>

            <div className="bg-white border rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Policy Arms</h2>
                <p className="text-gray-600 text-sm mb-4">
                    The agent uses Thompson Sampling to select between different repair strategies.
                    Policy arms are configured in <code className="bg-gray-100 px-1 rounded">upstream_learner/policy_arms.py</code>.
                </p>
                <div className="grid grid-cols-2 gap-3">
                    {[
                        { id: 'traceback_minimal', name: 'Traceback Minimal' },
                        { id: 'traceback_grep_standard', name: 'Traceback + GREP' },
                        { id: 'traceback_grep_defensive', name: 'Defensive Fix' },
                        { id: 'deep_grep_minimal', name: 'Deep GREP' },
                        { id: 'deep_grep_edge_case', name: 'Edge Case Fix' },
                        { id: 'imports_minimal', name: 'Import Aware' },
                        { id: 'minimal_fast', name: 'Minimal Fast' },
                        { id: 'grep_assertion', name: 'Assertion Hardening' },
                    ].map((arm) => (
                        <div
                            key={arm.id}
                            className="px-3 py-2 bg-gray-50 border rounded text-sm"
                        >
                            <div className="font-medium">{arm.name}</div>
                            <div className="text-xs text-gray-500 font-mono">{arm.id}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex items-center gap-4">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium"
                >
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
                {saved && (
                    <span className="text-green-600 text-sm">✓ Settings saved</span>
                )}
            </div>
        </div>
    );
}
