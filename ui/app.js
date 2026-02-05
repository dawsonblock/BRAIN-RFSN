// RFSN Control Center - Interactive Features

// Policy Arms Data
const POLICY_ARMS = [
    {
        id: 'traceback_minimal',
        name: 'Traceback Minimal',
        desc: 'Traceback files only, minimal fix, fast model',
        context: 'TRACEBACK_ONLY',
        patch: 'MINIMAL_FIX',
        model: 'FAST'
    },
    {
        id: 'traceback_grep_standard',
        name: 'Traceback + GREP',
        desc: 'Traceback + grep expansion, minimal fix',
        context: 'TRACEBACK_GREP',
        patch: 'MINIMAL_FIX',
        model: 'STANDARD'
    },
    {
        id: 'traceback_grep_defensive',
        name: 'Defensive Fix',
        desc: 'Traceback + grep, add error handling',
        context: 'TRACEBACK_GREP',
        patch: 'DEFENSIVE',
        model: 'STANDARD'
    },
    {
        id: 'deep_grep_minimal',
        name: 'Deep GREP',
        desc: 'Aggressive grep for all symbols',
        context: 'DEEP_GREP',
        patch: 'MINIMAL_FIX',
        model: 'STANDARD'
    },
    {
        id: 'deep_grep_edge_case',
        name: 'Edge Case Fix',
        desc: 'Deep grep, handle edge cases/types',
        context: 'DEEP_GREP',
        patch: 'TYPE_EDGE_CASE',
        model: 'CREATIVE'
    },
    {
        id: 'imports_minimal',
        name: 'Import Aware',
        desc: 'Traceback + import neighbors',
        context: 'TRACEBACK_IMPORTS',
        patch: 'MINIMAL_FIX',
        model: 'STANDARD'
    },
    {
        id: 'minimal_fast',
        name: 'Minimal Fast',
        desc: 'Just pytest output, fast model',
        context: 'MINIMAL',
        patch: 'MINIMAL_FIX',
        model: 'FAST'
    },
    {
        id: 'grep_assertion',
        name: 'Assertion Hardening',
        desc: 'Add assertions and guards',
        context: 'TRACEBACK_GREP',
        patch: 'ASSERTION_HARDENING',
        model: 'STANDARD'
    }
];

// Bandit state (simulated)
let banditState = {};
POLICY_ARMS.forEach(arm => {
    banditState[arm.id] = {
        alpha: 1 + Math.floor(Math.random() * 10),
        beta: 1 + Math.floor(Math.random() * 5)
    };
});

// Selected arm
let selectedArm = 'traceback_grep_standard';

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initArmsGrid();
    initBanditChart();
    loadState();
});

// Initialize arms grid
function initArmsGrid() {
    const grid = document.getElementById('arms-grid');
    grid.innerHTML = '';

    POLICY_ARMS.forEach(arm => {
        const card = document.createElement('div');
        card.className = `arm-card ${arm.id === selectedArm ? 'active' : ''}`;
        card.onclick = () => selectArm(arm.id);

        card.innerHTML = `
            <div class="arm-name">${arm.name}</div>
            <div class="arm-desc">${arm.desc}</div>
            <div class="arm-stats">
                <span class="arm-stat">${arm.context}</span>
                <span class="arm-stat">${arm.model}</span>
            </div>
        `;

        grid.appendChild(card);
    });
}

// Select arm
function selectArm(armId) {
    selectedArm = armId;
    initArmsGrid();

    // Update status
    addLedgerEntry('ARM_SELECT', `Selected arm: ${armId}`);
}

// Initialize bandit chart
function initBanditChart() {
    const chart = document.getElementById('bandit-chart');
    chart.innerHTML = '';

    // Calculate success rates
    const rates = POLICY_ARMS.map(arm => {
        const state = banditState[arm.id];
        const rate = state.alpha / (state.alpha + state.beta);
        return { id: arm.id, name: arm.name, rate, alpha: state.alpha, beta: state.beta };
    }).sort((a, b) => b.rate - a.rate);

    // Create bars
    rates.forEach(item => {
        const bar = document.createElement('div');
        bar.className = 'bandit-bar';

        bar.innerHTML = `
            <div class="bandit-label">${item.name}</div>
            <div class="bandit-track">
                <div class="bandit-fill" style="width: ${item.rate * 100}%"></div>
            </div>
            <div class="bandit-value">${(item.rate * 100).toFixed(1)}%</div>
        `;

        chart.appendChild(bar);
    });
}

// Add ledger entry
function addLedgerEntry(type, desc) {
    const entries = document.getElementById('ledger-entries');
    const now = new Date();
    const time = now.toTimeString().slice(0, 8);

    const entry = document.createElement('div');
    entry.className = 'ledger-entry';

    const badgeClass = {
        'ARM_SELECT': 'badge-info',
        'RUN_TESTS': 'badge-primary',
        'APPLY_PATCH': 'badge-warning',
        'READ_FILE': 'badge-secondary',
        'GIT_DIFF': 'badge-success',
        'ERROR': 'badge-danger'
    }[type] || 'badge-secondary';

    entry.innerHTML = `
        <span class="entry-time">${time}</span>
        <span class="entry-type badge ${badgeClass}">${type}</span>
        <span class="entry-desc">${desc}</span>
    `;

    // Remove placeholder if present
    if (entries.children[0]?.querySelector('.entry-desc')?.textContent === 'No ledger entries yet') {
        entries.innerHTML = '';
    }

    entries.insertBefore(entry, entries.firstChild);

    // Update counter
    const count = entries.children.length;
    document.getElementById('ledger-count').textContent = count;
}

// Start agent
function startAgent() {
    const workspace = document.getElementById('workspace-path').value;
    const taskId = document.getElementById('task-id').value;
    const attempts = document.getElementById('max-attempts').value;

    if (!workspace) {
        alert('Please enter a workspace path');
        return;
    }

    addLedgerEntry('RUN_TESTS', `Starting agent: ${taskId} (${attempts} attempts)`);

    // Simulate running
    document.querySelector('.nav-status span:last-child').textContent = 'Running...';
    document.querySelector('.status-dot').style.background = '#ed8936';

    // Simulate completion after delay
    setTimeout(() => {
        addLedgerEntry('RUN_TESTS', 'Baseline test run complete');

        // Simulate attempt
        setTimeout(() => {
            addLedgerEntry('READ_FILE', `Context: 6 files, 120KB`);

            setTimeout(() => {
                // Update bandit
                const state = banditState[selectedArm];
                if (Math.random() > 0.5) {
                    state.alpha += 1;
                    addLedgerEntry('APPLY_PATCH', 'Patch applied successfully ✓');
                } else {
                    state.beta += 1;
                    addLedgerEntry('ERROR', 'Patch failed to apply');
                }
                initBanditChart();

                document.querySelector('.nav-status span:last-child').textContent = 'System Online';
                document.querySelector('.status-dot').style.background = '#48bb78';
            }, 800);
        }, 600);
    }, 500);
}

// Stop agent
function stopAgent() {
    addLedgerEntry('ERROR', 'Agent stopped by user');
    document.querySelector('.nav-status span:last-child').textContent = 'System Online';
    document.querySelector('.status-dot').style.background = '#48bb78';
}

// Preview context
function previewContext() {
    const maxFiles = document.getElementById('ctx-max-files').value;
    const maxBytes = document.getElementById('ctx-max-bytes').value;

    const preview = document.getElementById('context-preview');
    preview.innerHTML = `
        <div style="color: #48bb78;">▸ Extracting traceback paths...</div>
        <div style="margin-left: 16px; color: #a0aec0;">
            • tests/test_main.py<br>
            • src/core.py<br>
            • src/utils.py
        </div>
        <div style="color: #48bb78; margin-top: 8px;">▸ GREP expansion (${maxFiles} files max)...</div>
        <div style="margin-left: 16px; color: #a0aec0;">
            • Found 3 additional files<br>
            • Total: 6 files
        </div>
        <div style="color: #48bb78; margin-top: 8px;">▸ Reading with budget ${(maxBytes / 1000).toFixed(0)}KB...</div>
        <div style="margin-left: 16px; color: #a0aec0;">
            • Read 6 files (89KB total)
        </div>
    `;

    addLedgerEntry('READ_FILE', `Context preview: ${maxFiles} files, ${maxBytes} bytes`);
}

// Run tests
function runTests() {
    const args = document.getElementById('pytest-args').value;
    const useSandbox = document.getElementById('use-sandbox').checked;

    document.getElementById('test-status').textContent = 'Running';
    document.getElementById('test-status').className = 'badge badge-warning';

    const output = document.getElementById('test-output');
    output.innerHTML = `<pre>$ pytest ${args}${useSandbox ? ' (sandboxed)' : ''}\n\nCollecting tests...</pre>`;

    addLedgerEntry('RUN_TESTS', `pytest ${args}${useSandbox ? ' [SANDBOX]' : ''}`);

    setTimeout(() => {
        output.innerHTML = `<pre>$ pytest ${args}${useSandbox ? ' (sandboxed)' : ''}

<span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span><span style="color: #48bb78;">.</span> [100%]

<span style="color: #48bb78;">92 passed</span> in 1.83s</pre>`;

        document.getElementById('test-status').textContent = 'Passed';
        document.getElementById('test-status').className = 'badge badge-success';

        addLedgerEntry('RUN_TESTS', '92 passed in 1.83s ✓');
    }, 1500);
}

// Run diff
function runDiff() {
    const context = document.getElementById('diff-context').value;
    const paths = document.getElementById('diff-paths').value;

    const output = document.getElementById('diff-output');

    addLedgerEntry('GIT_DIFF', `git diff -U${context}${paths ? ' -- ' + paths : ''}`);

    output.innerHTML = `<pre style="color: #a0aec0;">$ git diff -U${context}${paths ? ' -- ' + paths : ''}

<span style="color: #f56565;">--- a/src/core.py</span>
<span style="color: #48bb78;">+++ b/src/core.py</span>
<span style="color: #4299e1;">@@ -42,${context + 1} +42,${context + 1} @@</span>
 def process_data(data):
     """Process the input data."""
<span style="color: #f56565;">-    return data.strip()</span>
<span style="color: #48bb78;">+    if data is None:</span>
<span style="color: #48bb78;">+        return ""</span>
<span style="color: #48bb78;">+    return data.strip()</span>
</pre>`;
}

// Refresh ledger
function refreshLedger() {
    addLedgerEntry('READ_FILE', 'Ledger refreshed');
}

// Load state from localStorage
function loadState() {
    try {
        const saved = localStorage.getItem('rfsn_dashboard');
        if (saved) {
            const state = JSON.parse(saved);
            document.getElementById('workspace-path').value = state.workspace || '';
            document.getElementById('task-id').value = state.taskId || 'local_task';
        }
    } catch (e) {
        console.warn('Could not load state');
    }
}

// Save state on input change
document.getElementById('workspace-path')?.addEventListener('change', saveState);
document.getElementById('task-id')?.addEventListener('change', saveState);

function saveState() {
    const state = {
        workspace: document.getElementById('workspace-path').value,
        taskId: document.getElementById('task-id').value
    };
    localStorage.setItem('rfsn_dashboard', JSON.stringify(state));
}
