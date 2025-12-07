// Agentic SOC Dashboard JavaScript

const API_BASE = window.location.origin || 'http://localhost:8000';
let workflows = [];
let uploadedFiles = [];
let allAlerts = [];
let selectedAlerts = new Set();
let selectedFileId = null;
// Track active WebSocket connections globally
const wsConnections = {};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    setupEventListeners();
});

// Initialize dashboard
async function initializeDashboard() {
    await loadMetrics();
}

// Setup event listeners
function setupEventListeners() {
    // Upload file - auto submit on selection
    const uploadInput = document.getElementById('uploadInput');
    if (uploadInput) {
        uploadInput.addEventListener('change', handleFileUpload);
    }

    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAllWorkflows);
    }

    // Collapse buttons
    const collapseLeftBtn = document.getElementById('collapseLeftBtn');
    if (collapseLeftBtn) {
        collapseLeftBtn.addEventListener('click', toggleLeftPanel);
    }

    const collapseRightBtn = document.getElementById('collapseRightBtn');
    if (collapseRightBtn) {
        collapseRightBtn.addEventListener('click', toggleRightPanel);
    }

    // Select all alerts
    const selectAllAlerts = document.getElementById('selectAllAlerts');
    if (selectAllAlerts) {
        selectAllAlerts.addEventListener('change', handleSelectAll);
    }

    // Start analysis button
    const startAnalysisBtn = document.getElementById('startAnalysisBtn');
    if (startAnalysisBtn) {
        startAnalysisBtn.addEventListener('click', startAnalysis);
    }

    // Modal close
    const closeModalBtn = document.querySelector('.close');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    window.addEventListener('click', (e) => {
        const modal = document.getElementById('alertModal');
        if (e.target === modal) {
            closeModal();
        }
    });
}

// Handle file upload (auto-submit)
async function handleFileUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    showLoading(true);
    
    for (let file of files) {
        try {
            const content = await file.text();
            const alerts = JSON.parse(content);
            
            // Store file info
            const fileId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            const fileInfo = {
                id: fileId,
                name: file.name,
                alertCount: Array.isArray(alerts) ? alerts.length : (alerts.alerts ? alerts.alerts.length : 1),
                uploadTime: new Date().toLocaleTimeString(),
                alerts: Array.isArray(alerts) ? alerts : (alerts.alerts || [alerts])
            };
            
            uploadedFiles.push(fileInfo);
            
        } catch (error) {
            console.error('Error processing file:', error);
            // showToast(`Error processing ${file.name}`, 'error');
        }
    }
    
    renderFileList();
    showLoading(false);
    // showToast(`${files.length} file(s) uploaded successfully`, 'success');
    
    // Clear input
    event.target.value = '';
}

// Toggle left panel
function toggleLeftPanel() {
    const panel = document.getElementById('leftPanel');
    const btn = document.getElementById('collapseLeftBtn');
    panel.classList.toggle('collapsed');
    btn.textContent = panel.classList.contains('collapsed') ? '▶' : '◀';
}

// Toggle right panel
function toggleRightPanel() {
    const panel = document.getElementById('rightPanel');
    const btn = document.getElementById('collapseRightBtn');
    panel.classList.toggle('collapsed');
    btn.textContent = panel.classList.contains('collapsed') ? '◀' : '▶';
}

// Render file list
function renderFileList() {
    const fileList = document.getElementById('fileList');
    
    if (uploadedFiles.length === 0) {
        fileList.innerHTML = '<div class="empty-message"><p>No files uploaded yet</p></div>';
        return;
    }
    
    fileList.innerHTML = uploadedFiles.map(file => `
        <div class="file-item ${selectedFileId === file.id ? 'selected' : ''}" onclick="selectFile('${file.id}')">
            <div class="file-name">${file.name}</div>
            <div class="file-info">${file.uploadTime}</div>
            <div class="file-badge">${file.alertCount} alerts</div>
        </div>
    `).join('');
}

// Select file and show its alerts
function selectFile(fileId) {
    selectedFileId = fileId;
    renderFileList();
    
    const file = uploadedFiles.find(f => f.id === fileId);
    if (file) {
        allAlerts = file.alerts.map((alert, index) => ({
            ...alert,
            fileId: fileId,
            alertIndex: index,
            displayId: `${file.name}-${index + 1}`
        }));
        selectedAlerts.clear();
        renderAlertsList();
        updateSelectedCount();
    }
}

// Render alerts list
function renderAlertsList() {
    const alertsList = document.getElementById('alertsList');
    
    if (allAlerts.length === 0) {
        alertsList.innerHTML = '<div class="empty-message"><p>No alerts to display</p><p class="empty-hint">Upload a file to get started</p></div>';
        return;
    }
    
    alertsList.innerHTML = allAlerts.map((alert, index) => {
        const isSelected = selectedAlerts.has(index);
        return `
            <div class="alert-item ${isSelected ? 'selected' : ''}" onclick="toggleAlertSelection(${index}, event)">
                <input type="checkbox" class="alert-checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleAlertSelection(${index}, event)">
                <div class="alert-header">
                    <div class="alert-id">${alert.displayId || alert.alert_id || `Alert-${index + 1}`}</div>
                </div>
                <div class="alert-details">
                    <div class="alert-detail-item">
                        <span class="alert-detail-label">Rule:</span>
                        <span class="alert-detail-value">${alert.rule_name || alert.rule_id || 'N/A'}</span>
                    </div>
                    <div class="alert-detail-item">
                        <span class="alert-detail-label">Severity:</span>
                        <span class="alert-detail-value">${alert.severity || 'N/A'}</span>
                    </div>
                    <div class="alert-detail-item">
                        <span class="alert-detail-label">Host:</span>
                        <span class="alert-detail-value">${alert.assets?.host || alert.host || 'N/A'}</span>
                    </div>
                    <div class="alert-detail-item">
                        <span class="alert-detail-label">Source IP:</span>
                        <span class="alert-detail-value">${alert.assets?.source_ip || alert.source_ip || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Toggle alert selection
function toggleAlertSelection(index, event) {
    if (selectedAlerts.has(index)) {
        selectedAlerts.delete(index);
    } else {
        selectedAlerts.add(index);
    }
    renderAlertsList();
    updateSelectedCount();
    updateStartButton();
}

// Handle select all
function handleSelectAll(event) {
    if (event.target.checked) {
        allAlerts.forEach((_, index) => selectedAlerts.add(index));
    } else {
        selectedAlerts.clear();
    }
    renderAlertsList();
    updateSelectedCount();
    updateStartButton();
}

// Update selected count
function updateSelectedCount() {
    document.getElementById('selectedCount').textContent = `${selectedAlerts.size} selected`;
}

// Update start button state
function updateStartButton() {
    const btn = document.getElementById('startAnalysisBtn');
    btn.disabled = selectedAlerts.size === 0;
}

// Start analysis
async function startAnalysis() {
    if (selectedAlerts.size === 0) {
        // showToast('Please select at least one alert', 'warning');
        return;
    }
    
    const selectedAlertsList = Array.from(selectedAlerts).map(index => allAlerts[index]);
    // Clear previous terminal logs on new analysis start
    addTerminalLog('clear');
    // Ungrouped start message(s)
    addTerminalLog(null, `Starting analysis for ${selectedAlertsList.length} alert(s)...`);
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/api/alerts/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(selectedAlertsList)
        });
        
        const data = await response.json();
        addTerminalLog(null, `Analysis started for ${selectedAlertsList.length} alerts`);
        
        // Connect websockets for real-time updates
        if (data.workflows) {
            data.workflows.forEach(wf => {
                connectWorkflowWebSocket(wf.workflow_id);
                addTerminalLog(null, `Connected to workflow: ${wf.workflow_id}`);
            });
        }
        
        // showToast(`Analysis started for ${selectedAlertsList.length} alerts`, 'success');
        
        // Refresh metrics
        setTimeout(() => loadMetrics(), 1000);
        
    } catch (error) {
        console.error('Error starting analysis:', error);
        addTerminalLog('error', `✗ Failed to start analysis: ${error.message}`);
        // showToast('Error starting analysis', 'error');
    } finally {
        showLoading(false);
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

// Modify the addTerminalLog function to group logs by msg.stage and keep other logs ungrouped
// Also show a progress icon (↻) in the header when status is 'progress',
// hide it on 'completed' or 'failed', and color failed status red.
function addTerminalLog(stage, message, status = null) {
    const terminalOutput = document.getElementById('terminalOutput');

    // Clear previous logs if "start analysis" is triggered
    if (stage === 'clear') {
        terminalOutput.innerHTML = '';
        return;
    }

    // Handle ungrouped logs
    if (!stage) {
        const logLine = document.createElement('div');
        logLine.className = 'terminal-line';
        logLine.innerHTML = `<span class="message">${message}</span>`;
        terminalOutput.appendChild(logLine);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
        return;
    }

    // Check if a group for this stage already exists
    let group = terminalOutput.querySelector(`.terminal-group[data-stage="${stage}"]`);
    if (!group) {
        // Create a new group if it doesn't exist
        group = document.createElement('div');
        group.className = 'terminal-group';
        group.dataset.stage = stage;
        group.innerHTML = `
            <div class="terminal-group-header">
                <span class="group-stage">${stage.toUpperCase()}</span>
                <span class="group-progress" style="margin-left: 8px; display: none;">↻</span>
                <span class="group-toggle" style="margin-left: 8px;">▶</span>
                <span class="group-status-right" style="margin-left:auto; font-size: 0.85rem; color: #94a3b8;"></span>
            </div>
            <div class="terminal-group-content" style="display: none;"></div>
        `;
        terminalOutput.appendChild(group);

        // Add event listener to toggle group visibility when clicking on the group name or toggle icon
        const groupHeader = group.querySelector('.terminal-group-header');
        groupHeader.addEventListener('click', () => {
            const content = group.querySelector('.terminal-group-content');
            const toggleElement = group.querySelector('.group-toggle');
            const isCollapsed = content.style.display === 'none';
            content.style.display = isCollapsed ? 'block' : 'none';
            toggleElement.textContent = isCollapsed ? '▼' : '▶';
        });
    }

    // Update header status/progress if provided
    if (status) {
        const header = group.querySelector('.terminal-group-header');
        const progressEl = group.querySelector('.group-progress');
        const statusRight = group.querySelector('.group-status-right');
        if (statusRight) {
            statusRight.textContent = status;
            // Color red on failed
            if (String(status).toLowerCase() === 'failed') {
                statusRight.style.color = '#ef4444';
            } else {
                statusRight.style.color = '#94a3b8';
            }
        }
        // Show/hide progress icon
        if (String(status).toLowerCase() === 'progress') {
            progressEl.style.display = 'inline';
            progressEl.classList.add('spin');
        } else {
            progressEl.style.display = 'none';
            progressEl.classList.remove('spin');
        }
    }

    // Add the log message to the group content
    const groupContent = group.querySelector('.terminal-group-content');
    const logLine = document.createElement('div');
    logLine.className = 'terminal-line';
    logLine.innerHTML = `<span class="message">${message}</span>`;
    groupContent.appendChild(logLine);

    // Scroll to the bottom of the terminal
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
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
        // Modify WebSocket message handling to log agent data
        ws.onmessage = (evt) => {
            let msg = null;
            try { msg = JSON.parse(evt.data); } catch { return; }

            const shortId = workflowId.substring(0, 8);
            
            if (msg.stage && msg.status) {
                // Group by msg.stage only; show message under that group and update status/progress
                const stageName = `${msg.stage} agent`;
                addTerminalLog(stageName, `[${shortId}] ${msg.status}`, msg.status);
                console.log(`Data received from agent: ${msg.stage}`, msg.status);
            }

            if (msg.type === 'progress') {
                // Progress belongs to the same stage group
                const stageName = `${msg.stage} agent`;
                addTerminalLog(stageName, `[${shortId}] ${msg.status}`, msg.status);
                // showToast(`${msg.stage}: ${msg.status}`, 'info');
            }
            
            if (msg.type === 'agent_output' && msg.details) {
                // Log detailed agent output under the agent's stage if present
                const stageName = msg.stage ? `${msg.stage} agent` : null;
                if (stageName) {
                    addTerminalLog(stageName, `[${shortId}] ${msg.details}`, msg.status);
                } else {
                    addTerminalLog(null, `[${shortId}] ${msg.agent || 'Agent'}: ${msg.details}`);
                }
            }
            
            if (msg.type === 'final') {
                addTerminalLog(null, `[${shortId}] ✓ Workflow completed: ${msg.status}`);
                addTerminalLog(null, 'End');
                // showToast(`Workflow completed: ${msg.status}`, 'success');
                // Refresh to show final status and LLM results
                loadMetrics();
                // Close ws
                try { ws.close(); } catch {}
                delete wsConnections[workflowId];
            }
            
            if (msg.type === 'error') {
                console.log('error', `[${shortId}] ✗ Error: ${msg.message || 'Unknown error'}`);
            }
        };
        ws.onerror = (error) => {
            console.log('error', `WebSocket error for ${shortId}: Connection failed`);
        };
        ws.onclose = () => {
            const shortId = workflowId.substring(0, 8);
            console.log('system', `WebSocket closed for ${shortId}`);
            delete wsConnections[workflowId];
        };
    } catch (e) {
        console.warn('WS connect failed', e);
        console.log('error', `Failed to connect WebSocket: ${e.message}`);
    }
}

// Keep for backward compatibility but not actively used in new UI
function renderWorkflowsTable(workflowsList) {
    // This function is kept for potential future use or API compatibility
    console.log('Workflows loaded:', workflowsList.length);
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
        // showToast('Error loading alert details', 'error');
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

// Load sample alerts - simplified version
async function loadSampleAlerts() {
    addTerminalLog('system', 'Loading sample alerts...');
    // This can be extended if needed
}

// Clear all workflows
async function clearAllWorkflows() {
    if (!confirm('Are you sure you want to clear all data? This will remove all uploaded files and workflows.')) {
        return;
    }
    
    try {
        showLoading(true);
        addTerminalLog('system', 'Clearing all data...');
        
        await fetch(`${API_BASE}/api/workflows/clear`, { method: 'DELETE' });
        
        // Clear local data
        uploadedFiles = [];
        allAlerts = [];
        selectedAlerts.clear();
        selectedFileId = null;
        
        // Clear UI
        renderFileList();
        renderAlertsList();
        updateSelectedCount();
        updateStartButton();
        
        // Clear terminal
        document.getElementById('terminalOutput').innerHTML = `
            <div class="terminal-line system">
                <span class="message">Agent terminal ready. Waiting for analysis...</span>
            </div>
        `;
        
        // showToast('All data cleared', 'success');
        addTerminalLog('success', '✓ All data cleared successfully');
        
        await loadMetrics();
        
        showLoading(false);
    } catch (error) {
        console.error('Error clearing workflows:', error);
        // showToast('Error clearing workflows', 'error');
        addTerminalLog('error', `✗ Error clearing data: ${error.message}`);
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

// // Show toast notification
// function showToast(message, type = 'info') {
//     const container = document.getElementById('toastContainer');
//     const toast = document.createElement('div');
//     toast.className = `toast ${type}`;
//     toast.textContent = message;
    
//     container.appendChild(toast);
    
//     setTimeout(() => {
//         toast.remove();
//     }, 4000);
// }

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

// Function to handle 'Details' link click and display alert information
function viewAlertDetailsPopup(alertId) {
    const alert = allAlerts.find(a => a.id === alertId);
    if (!alert) {
        console.error('Alert not found:', alertId);
        return;
    }

    const modalContent = document.getElementById('alertDetailContent');
    modalContent.innerHTML = `
        <div class="detail-section">
            <h3>Alert Information</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Alert ID</div>
                    <div class="detail-value">${alert.id}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Priority</div>
                    <div class="detail-value">${alert.priority}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">${alert.status}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Description</div>
                    <div class="detail-value">${alert.description}</div>
                </div>
            </div>
        </div>
    `;

    const modal = document.getElementById('alertModal');
    modal.style.display = 'block';
}

// Close modal when clicking outside or on close button
window.addEventListener('click', (event) => {
    const modal = document.getElementById('alertModal');
    if (event.target === modal || event.target.classList.contains('close')) {
        modal.style.display = 'none';
    }
});
