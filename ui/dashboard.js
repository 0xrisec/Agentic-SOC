// Agentic SOC Dashboard JavaScript (scoped to avoid globals)
(function () {
const API_BASE = window.location.origin || 'http://localhost:8000';
let autoRefreshInterval = null;
let workflows = [];
// Track active WebSocket connections globally (scoped)
const wsConnections = {};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    setupEventListeners();
    startAutoRefresh();
});

// Initialize dashboard
async function initializeDashboard() {
    await loadMetrics();
    await loadWorkflows();
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('loadSampleBtn').addEventListener('click', loadSampleAlerts);
    // Upload controls
    const uploadInput = document.getElementById('uploadInput');
    document.getElementById('uploadSubmitBtn').addEventListener('click', async () => {
        if (!uploadInput.files || uploadInput.files.length === 0) {
            showToast('Please select a JSON file to upload', 'warning');
            return;
        }
        const file = uploadInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        showLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/api/upload-alert`, { method: 'POST', body: formData });
            if (!resp.ok) {
                const text = await resp.text();
                showToast(`Upload failed (${resp.status}): ${text}`, 'error');
                showLoading(false);
                return;
            }
            const data = await resp.json();
            showToast('Alert uploaded and processing started', 'success');
            // Optionally refresh metrics/workflows shortly after upload
            setTimeout(() => {
                loadMetrics();
                loadWorkflows();
            }, 1500);
            showLoading(false);
        } catch (e) {
            console.error('Upload error:', e);
            showToast('Upload error', 'error');
            showLoading(false);
        }
    });

    // Alert Triage Agent controls (second page markup)
    const fileInput = document.getElementById('fileInput');
    const processBtn = document.getElementById('processBtn');
    const resetBtn = document.getElementById('resetBtn');
    const logEl = document.getElementById('log');
    const finalStatusEl = document.getElementById('finalStatus');

    if (fileInput && processBtn) {
        fileInput.addEventListener('change', () => {
            processBtn.disabled = !(fileInput.files && fileInput.files.length > 0);
        });

        processBtn.addEventListener('click', async () => {
            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Please select a JSON file to upload', 'warning');
                return;
            }
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            processBtn.disabled = true;
            finalStatusEl && (finalStatusEl.textContent = '');
            logEl && (logEl.textContent = '');
            appendLog(logEl, 'Submitting alert to backend...');
            try {
                const resp = await fetch(`${API_BASE}/api/upload-alert`, { method: 'POST', body: formData });
                if (!resp.ok) {
                    const text = await resp.text();
                    appendLog(logEl, `Upload failed (${resp.status}): ${text}`);
                    showToast(`Upload failed (${resp.status})`, 'error');
                    processBtn.disabled = false;
                    return;
                }
                const data = await resp.json();
                showToast('Alert uploaded. Starting live updates...', 'success');
                appendLog(logEl, `Uploaded ${data.workflows?.length || 1} alert(s).`);

                // Open WebSocket(s) for live stream
                const items = Array.isArray(data.workflows) ? data.workflows : [];
                items.forEach(({ workflow_id }) => {
                    if (!workflow_id) return;
                    openWorkflowStream(workflow_id, logEl, finalStatusEl);
                });
            } catch (e) {
                console.error('Upload error:', e);
                appendLog(logEl, 'Upload error');
                showToast('Upload error', 'error');
                processBtn.disabled = false;
            }
        });
    }

    if (resetBtn && fileInput && processBtn) {
        resetBtn.addEventListener('click', () => {
            fileInput.value = '';
            processBtn.disabled = true;
            if (logEl) logEl.textContent = '';
            if (finalStatusEl) finalStatusEl.textContent = '';
        });
    }
}

// Load sample alerts
async function loadSampleAlerts() {
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE}/api/alerts/sample`);
        const data = await response.json();
        
        if (!data.alerts || data.alerts.length === 0) {
            showToast('No sample alerts found', 'warning');
            showLoading(false);
            return;
        }
        
        // Process alerts in batch
        const batchResponse = await fetch(`${API_BASE}/api/alerts/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data.alerts)
        });
        
        const batchData = await batchResponse.json();
        
        showToast(`Processing ${data.alerts.length} sample alerts`, 'success');
        showLoading(false);
        
        // Refresh after a delay
        setTimeout(() => {
            loadMetrics();
            loadWorkflows();
        }, 2000);
        
    } catch (error) {
        console.error('Error loading sample alerts:', error);
        showToast('Error loading sample alerts', 'error');
        showLoading(false);
    }
}

// Clear all workflows
async function clearAllWorkflows() {
    if (!confirm('Are you sure you want to clear all workflows? This cannot be undone.')) {
        return;
    }
    
    try {
        showLoading(true);
        
        await fetch(`${API_BASE}/api/workflows/clear`, { method: 'DELETE' });
        
        showToast('All workflows cleared', 'success');
        
        await loadMetrics();
        await loadWorkflows();
        
        showLoading(false);
    } catch (error) {
        console.error('Error clearing workflows:', error);
        showToast('Error clearing workflows', 'error');
        showLoading(false);
    }
}

// Close modal
function closeModal() {
    document.getElementById('alertModal').style.display = 'none';
}

// Show loading overlay
function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

// Show toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Utility functions
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
}

function formatVerdict(verdict) {
    return verdict.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function truncate(str, maxLength) {
    if (!str) return 'N/A';
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

// Missing helpers: implement minimal versions
async function loadMetrics() {
    try {
        const resp = await fetch(`${API_BASE}/api/metrics`);
        if (!resp.ok) return;
        const data = await resp.json();
        const el = document.getElementById('metricsContent');
        if (el) el.textContent = JSON.stringify(data);
    } catch {}
}

async function loadWorkflows() {
    try {
        // Correct endpoint per backend: /api/alerts/list
        const resp = await fetch(`${API_BASE}/api/alerts/list`);
        if (!resp.ok) return;
        const data = await resp.json();
        workflows = Array.isArray(data.workflows) ? data.workflows : [];
        const el = document.getElementById('workflowsContent');
        if (el) el.textContent = `${workflows.length} workflows`;
    } catch {}
}

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        loadMetrics();
        loadWorkflows();
    }, 5000);
}

// Helper: append log line in Live Agent view
function appendLog(logEl, text) {
    if (!logEl) return;
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = text;
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
}

// Open WS and stream status updates
function openWorkflowStream(workflowId, logEl, finalStatusEl) {
    try {
        const wsUrl = `${API_BASE.replace('http', 'ws')}/ws/${workflowId}`;
        const ws = new WebSocket(wsUrl);
        wsConnections[workflowId] = ws;
        appendLog(logEl, `Connected to workflow ${workflowId}`);
        ws.onmessage = (evt) => {
            try {
                const msg = JSON.parse(evt.data);
                if (msg.type === 'status') {
                    appendLog(logEl, `Status: ${msg.status} | Agent: ${msg.current_agent || 'n/a'}`);
                } else if (msg.type === 'progress') {
                    appendLog(logEl, `Progress: ${JSON.stringify(msg)}`);
                } else if (msg.type === 'final') {
                    appendLog(logEl, `Final: ${JSON.stringify(msg)}`);
                    if (finalStatusEl) {
                        const verdict = msg.verdict || 'unknown';
                        const priority = msg.priority || 'n/a';
                        finalStatusEl.textContent = `Status: ${msg.status} | Verdict: ${verdict} | Priority: ${priority}`;
                    }
                }
            } catch (_) {
                appendLog(logEl, evt.data);
            }
        };
        ws.onerror = () => appendLog(logEl, 'WebSocket error');
        ws.onclose = () => appendLog(logEl, 'WebSocket closed');
    } catch (e) {
        appendLog(logEl, `WS error: ${e.message}`);
    }
}

// Close IIFE
})();
