// Agentic SOC Dashboard JavaScript

const API_BASE = window.location.origin || 'http://localhost:8000';
let autoRefreshInterval = null;
let workflows = [];
// Track active WebSocket connections globally
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
            const data = await resp.json();
            showToast(`Uploaded: ${data.message}`, 'success');
            // Connect websockets for newly submitted workflows
            (data.workflows || []).forEach(w => connectWorkflowWebSocket(w.workflow_id));
            await loadWorkflows();
        } catch (e) {
            console.error('Upload failed', e);
            showToast('Upload failed', 'error');
        } finally {
            showLoading(false);
        }
    });
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadMetrics();
        loadWorkflows();
    });
    document.getElementById('clearBtn').addEventListener('click', clearAllWorkflows);
    document.getElementById('autoRefresh').addEventListener('change', toggleAutoRefresh);
    document.getElementById('statusFilter').addEventListener('change', loadWorkflows);
    document.getElementById('priorityFilter').addEventListener('change', loadWorkflows);
    
    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('alertModal');
        if (e.target === modal) {
            closeModal();
        }
    });
}

// Auto-refresh functionality
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(async () => {
        if (document.getElementById('autoRefresh').checked) {
            await loadMetrics();
            await loadWorkflows();
        }
    }, 5000);
}

function toggleAutoRefresh() {
    const checkbox = document.getElementById('autoRefresh');
    const status = document.getElementById('autoRefreshStatus');
    
    if (checkbox.checked) {
        status.textContent = 'ON (5s)';
        status.style.color = 'var(--success-color)';
        startAutoRefresh();
    } else {
        status.textContent = 'OFF';
        status.style.color = 'var(--text-secondary)';
        clearInterval(autoRefreshInterval);
    }
}

// Load system metrics
async function loadMetrics() {
    try {
        const response = await fetch(`${API_BASE}/api/metrics`);
        const data = await response.json();
        
        document.getElementById('totalProcessed').textContent = data.total_alerts_processed || 0;
        document.getElementById('inProgress').textContent = data.alerts_in_progress || 0;
        document.getElementById('truePositives').textContent = data.true_positives || 0;
        document.getElementById('falsePositives').textContent = data.false_positives || 0;
        document.getElementById('benign').textContent = data.benign || 0;
        document.getElementById('avgMTTR').textContent = formatDuration(data.average_mttr || 0);
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

// Load workflows
async function loadWorkflows() {
    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const priorityFilter = document.getElementById('priorityFilter').value;
        
        let url = `${API_BASE}/api/alerts/list?limit=100`;
        if (statusFilter) url += `&status=${statusFilter}`;
        if (priorityFilter) url += `&priority=${priorityFilter}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        workflows = data.workflows || [];
        // Ensure websockets connected for active workflows
        workflows.forEach(wf => {
            if (wf.status !== 'COMPLETED' && wf.status !== 'FAILED' && wf.workflow_id) {
                connectWorkflowWebSocket(wf.workflow_id);
            }
        });
        renderWorkflowsTable(workflows);
    } catch (error) {
        console.error('Error loading workflows:', error);
        showToast('Error loading workflows', 'error');
    }
}

// Connect to WebSocket for a workflow and handle live updates
function connectWorkflowWebSocket(workflowId) {
    if (!workflowId || wsConnections[workflowId]) return; // already connected
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws/${workflowId}`;
    try {
        const ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            wsConnections[workflowId] = ws;
            // Optionally send a ping
            try { ws.send('ping'); } catch {}
        };
        ws.onmessage = (evt) => {
            let msg = null;
            try { msg = JSON.parse(evt.data); } catch { return; }
            if (msg.type === 'progress') {
                // Show agent stage transitions
                showToast(`Workflow ${workflowId}: ${msg.stage} ${msg.status}`, 'info');
            }
            if (msg.type === 'final') {
                showToast(`Workflow ${workflowId} completed: ${msg.status}`, 'success');
                // Refresh to show final status and LLM results
                loadMetrics();
                loadWorkflows();
                // Close ws
                try { ws.close(); } catch {}
                delete wsConnections[workflowId];
            }
        };
        ws.onerror = () => {
            // Ignore errors, will rely on polling
        };
        ws.onclose = () => {
            delete wsConnections[workflowId];
        };
    } catch (e) {
        console.warn('WS connect failed', e);
    }
}

// Render workflows table
function renderWorkflowsTable(workflowsList) {
    const tbody = document.getElementById('alertsTableBody');
    
    if (workflowsList.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-state">
                <td colspan="8">
                    <div class="empty-message">
                        <p>No alerts found</p>
                        <p class="empty-hint">Try adjusting filters or load sample alerts</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = workflowsList.map(workflow => `
        <tr>
            <td><code>${truncate(workflow.alert_id, 30)}</code></td>
            <td>${truncate(workflow.alert_id.split('-')[1] || 'N/A', 20)}</td>
            <td><span class="status-badge status-${workflow.status}">${workflow.status}</span></td>
            <td>${workflow.current_agent || 'N/A'}</td>
            <td>${workflow.verdict ? `<span class="verdict-badge verdict-${workflow.verdict}">${formatVerdict(workflow.verdict)}</span>` : '-'}</td>
            <td>${workflow.priority ? `<span class="priority-badge priority-${workflow.priority}">${workflow.priority}</span>` : '-'}</td>
            <td>${workflow.processing_time_seconds ? formatDuration(workflow.processing_time_seconds) : 'In progress...'}</td>
            <td>
                <button class="action-btn" onclick="viewAlertDetails('${workflow.workflow_id}')">
                    View Details
                </button>
            </td>
        </tr>
    `).join('');
}

// View alert details
async function viewAlertDetails(workflowId) {
    try {
        const response = await fetch(`${API_BASE}/api/alerts/status/${workflowId}?include_details=true`);
        const data = await response.json();
        
        renderAlertDetails(data);
        document.getElementById('alertModal').style.display = 'block';
    } catch (error) {
        console.error('Error loading alert details:', error);
        showToast('Error loading alert details', 'error');
    }
}

// Render alert details in modal
function renderAlertDetails(data) {
    const workflow = data.workflow;
    const details = data.details;
    
    let html = `
        <div class="detail-section">
            <h3>Alert Information</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Alert ID</div>
                    <div class="detail-value"><code>${workflow.alert_id}</code></div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Workflow ID</div>
                    <div class="detail-value"><code>${workflow.workflow_id}</code></div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">
                        <span class="status-badge status-${workflow.status}">${workflow.status}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Processing Time</div>
                    <div class="detail-value">${workflow.processing_time_seconds ? formatDuration(workflow.processing_time_seconds) : 'In progress'}</div>
                </div>
            </div>
        </div>
    `;
    
    if (details && details.alert) {
        html += `
            <div class="detail-section">
                <h3>Alert Details</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">Rule</div>
                        <div class="detail-value">${details.alert.rule_name || details.alert.rule_id}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Severity</div>
                        <div class="detail-value">${details.alert.severity}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Host</div>
                        <div class="detail-value">${details.alert.assets?.host || 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Source IP</div>
                        <div class="detail-value">${details.alert.assets?.source_ip || 'N/A'}</div>
                    </div>
                </div>
                <div class="detail-item" style="margin-top: 1rem;">
                    <div class="detail-label">Description</div>
                    <div class="detail-value">${details.alert.description}</div>
                </div>
            </div>
        `;
    }
    
    if (details && details.triage) {
        html += `
            <div class="detail-section">
                <h3>🔍 Triage Assessment</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">Verdict</div>
                        <div class="detail-value">
                            <span class="verdict-badge verdict-${details.triage.verdict}">
                                ${formatVerdict(details.triage.verdict)}
                            </span>
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Confidence</div>
                        <div class="detail-value">${(details.triage.confidence * 100).toFixed(0)}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Noise Score</div>
                        <div class="detail-value">${(details.triage.noise_score * 100).toFixed(0)}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Investigation Required</div>
                        <div class="detail-value">${details.triage.requires_investigation ? '✓ Yes' : '✗ No'}</div>
                    </div>
                </div>
                <div class="detail-item" style="margin-top: 1rem;">
                    <div class="detail-label">Reasoning</div>
                    <div class="detail-value">${details.triage.reasoning}</div>
                </div>
                ${details.triage.key_indicators && details.triage.key_indicators.length > 0 ? `
                    <div class="detail-item" style="margin-top: 1rem;">
                        <div class="detail-label">Key Indicators</div>
                        <ul class="detail-list">
                            ${details.triage.key_indicators.map(ind => `<li>${ind}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    if (details && details.investigation) {
        html += `
            <div class="detail-section">
                <h3>🔬 Investigation Results</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">Risk Score</div>
                        <div class="detail-value">${details.investigation.risk_score.toFixed(1)}/10</div>
                    </div>
                </div>
                ${details.investigation.findings && details.investigation.findings.length > 0 ? `
                    <div class="detail-item" style="margin-top: 1rem;">
                        <div class="detail-label">Findings</div>
                        <ul class="detail-list">
                            ${details.investigation.findings.map(finding => `<li>${finding}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                ${details.investigation.attack_chain && details.investigation.attack_chain.length > 0 ? `
                    <div class="detail-item" style="margin-top: 1rem;">
                        <div class="detail-label">Attack Chain</div>
                        <div class="detail-value">${details.investigation.attack_chain.join(' → ')}</div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    if (details && details.decision) {
        html += `
            <div class="detail-section">
                <h3>⚖️ Final Decision</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">Verdict</div>
                        <div class="detail-value">
                            <span class="verdict-badge verdict-${details.decision.final_verdict}">
                                ${formatVerdict(details.decision.final_verdict)}
                            </span>
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Priority</div>
                        <div class="detail-value">
                            <span class="priority-badge priority-${details.decision.priority}">
                                ${details.decision.priority}
                            </span>
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Confidence</div>
                        <div class="detail-value">${(details.decision.confidence * 100).toFixed(0)}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Escalation Required</div>
                        <div class="detail-value">${details.decision.escalation_required ? '✓ Yes' : '✗ No'}</div>
                    </div>
                </div>
                <div class="detail-item" style="margin-top: 1rem;">
                    <div class="detail-label">Rationale</div>
                    <div class="detail-value">${details.decision.rationale}</div>
                </div>
                <div class="detail-item" style="margin-top: 1rem;">
                    <div class="detail-label">Estimated Impact</div>
                    <div class="detail-value">${details.decision.estimated_impact}</div>
                </div>
                ${details.decision.recommended_actions && details.decision.recommended_actions.length > 0 ? `
                    <div class="detail-item" style="margin-top: 1rem;">
                        <div class="detail-label">Recommended Actions</div>
                        <ul class="detail-list">
                            ${details.decision.recommended_actions.map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    if (details && details.response) {
        html += `
            <div class="detail-section">
                <h3>🚨 Response Actions</h3>
                ${details.response.ticket_id ? `
                    <div class="detail-item">
                        <div class="detail-label">Ticket ID</div>
                        <div class="detail-value"><code>${details.response.ticket_id}</code></div>
                    </div>
                ` : ''}
                <div class="detail-item" style="margin-top: 1rem;">
                    <div class="detail-label">Summary</div>
                    <div class="detail-value">${details.response.summary}</div>
                </div>
                ${details.response.actions_taken && details.response.actions_taken.length > 0 ? `
                    <div class="detail-item" style="margin-top: 1rem;">
                        <div class="detail-label">Actions Taken</div>
                        <ul class="detail-list">
                            ${details.response.actions_taken.map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                ${details.response.notifications_sent && details.response.notifications_sent.length > 0 ? `
                    <div class="detail-item" style="margin-top: 1rem;">
                        <div class="detail-label">Notifications Sent</div>
                        <ul class="detail-list">
                            ${details.response.notifications_sent.map(notif => `<li>${notif}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    document.getElementById('alertDetailContent').innerHTML = html;
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
