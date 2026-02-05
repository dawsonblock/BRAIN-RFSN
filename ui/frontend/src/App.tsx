// FILE: ui/frontend/src/App.tsx
// Main app with routing and layout

import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useParams, useNavigate } from 'react-router-dom';
import { RunList } from './components/RunList';
import { RunPage } from './pages/RunPage';
import { LogsPage } from './pages/LogsPage';
import { LedgerPage } from './pages/LedgerPage';
import { ArtifactsPage } from './pages/ArtifactsPage';
import { SettingsPage } from './pages/SettingsPage';
import { NewRunModal } from './pages/NewRunModal';

function AppLayout() {
    const [showNewRun, setShowNewRun] = useState(false);
    const { runId } = useParams();
    const navigate = useNavigate();

    const navItems = runId
        ? [
            { to: `/run/${runId}`, label: '📊 Overview', icon: '📊' },
            { to: `/run/${runId}/logs`, label: '📋 Logs', icon: '📋' },
            { to: `/run/${runId}/ledger`, label: '🔗 Ledger', icon: '🔗' },
            { to: `/run/${runId}/artifacts`, label: '📁 Artifacts', icon: '📁' },
        ]
        : [];

    return (
        <div className="h-screen flex bg-white">
            {/* Sidebar */}
            <div className="w-64 flex-shrink-0 flex flex-col bg-white border-r">
                {/* Logo */}
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-gray-900">
                        <span className="text-primary-600">RFSN</span> Control Center
                    </h1>
                    <p className="text-xs text-gray-500 mt-1">
                        Safety Kernel Dashboard
                    </p>
                </div>

                {/* Run List */}
                <div className="flex-1 overflow-hidden">
                    <RunList onCreateNew={() => setShowNewRun(true)} />
                </div>

                {/* Bottom nav */}
                <div className="p-3 border-t">
                    <NavLink
                        to="/settings"
                        className={({ isActive }) =>
                            `flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isActive
                                ? 'bg-primary-50 text-primary-700'
                                : 'text-gray-600 hover:bg-gray-100'
                            }`
                        }
                    >
                        ⚙️ Settings
                    </NavLink>
                </div>
            </div>

            {/* Main content area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Tab navigation for run */}
                {navItems.length > 0 && (
                    <div className="flex border-b bg-gray-50 px-4">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                end={item.to === `/run/${runId}`}
                                className={({ isActive }) =>
                                    `px-4 py-3 text-sm font-medium border-b-2 -mb-px ${isActive
                                        ? 'border-primary-600 text-primary-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                    }`
                                }
                            >
                                {item.label}
                            </NavLink>
                        ))}
                    </div>
                )}

                {/* Page content */}
                <div className="flex-1 overflow-auto bg-gray-50">
                    <Routes>
                        <Route path="/" element={<WelcomePage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                        <Route path="/run/:runId" element={<RunPage />} />
                        <Route path="/run/:runId/logs" element={<LogsPage />} />
                        <Route path="/run/:runId/ledger" element={<LedgerPage />} />
                        <Route path="/run/:runId/artifacts" element={<ArtifactsPage />} />
                    </Routes>
                </div>
            </div>

            {/* New Run Modal */}
            <NewRunModal
                isOpen={showNewRun}
                onClose={() => setShowNewRun(false)}
                onCreated={(id) => {
                    navigate(`/run/${id}/logs`);
                }}
            />
        </div>
    );
}

function WelcomePage() {
    return (
        <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
                <div className="text-6xl mb-4">🛡️</div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    RFSN Control Center
                </h2>
                <p className="text-gray-500 mb-4">
                    Monitor and control safety-gated agent runs. All proposals pass
                    through the kernel gate with cryptographic audit trail.
                </p>
                <div className="text-sm text-gray-400">
                    Select a run from the sidebar or create a new one
                </div>
            </div>
        </div>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="*" element={<AppLayout />} />
            </Routes>
        </BrowserRouter>
    );
}
