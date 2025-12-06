// Global state
let uploadedFiles = [];
let currentFile = null;
let isAnalysisRunning = false;
let currentAgentIndex = 0;
let pollingInterval = null;
let ws = null;

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const filesContainer = document.getElementById('filesContainer');
const runAgentBtn = document.getElementById('runAgentBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const activityFeed = document.getElementById('activityFeed');
const resultsSection = document.getElementById('resultsSection');
const resultsContent = document.getElementById('resultsContent');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');
const systemStatus = document.getElementById('systemStatus');

const agents = ['triage', 'investigation', 'decision', 'response'];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    // File upload
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/json') {
            addFile(file);
        }
    });
    
    // Run analysis
    runAgentBtn.addEventListener('click', runAnalysis);
    
    // New analysis
    newAnalysisBtn.addEventListener('click', resetUI);
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        addFile(file);
    }
    fileInput.value = ''; // Reset input to allow selecting the same file again
}

function addFile(file) {
    if (file.type !== 'application/json') {
        showNotification('Please upload a JSON file', 'error');
        return;
    }
    
    // Check if file already exists
    const existingFile = uploadedFiles.find(f => f.name === file.name && f.size === file.size);
    if (existingFile) {
        showNotification('This file is already uploaded', 'info');
        return;
    }
    
    const fileObj = {
        id: Date.now(),
        file: file,
        name: file.name,
        size: file.size
    };
    
    uploadedFiles.push(fileObj);
    currentFile = fileObj;
    renderFilesList();
    runAgentBtn.disabled = false;
}

function removeFile(fileId) {
    uploadedFiles = uploadedFiles.filter(f => f.id !== fileId);
    
    if (currentFile && currentFile.id === fileId) {
        currentFile = uploadedFiles.length > 0 ? uploadedFiles[0] : null;
    }
    
    renderFilesList();
    runAgentBtn.disabled = uploadedFiles.length === 0;
}

function selectFile(fileId) {
    currentFile = uploadedFiles.find(f => f.id === fileId);
    renderFilesList();
}

function renderFilesList() {
    if (uploadedFiles.length === 0) {
        filesContainer.innerHTML = `
            <div class="empty-state">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                    <polyline points="13 2 13 9 20 9"></polyline>
                </svg>
                <p>No files uploaded yet</p>
            </div>
        `;
        return;
    }
    
    filesContainer.innerHTML = uploadedFiles.map(fileObj => `
        <div class="file-item ${currentFile && currentFile.id === fileObj.id ? 'active' : ''}" data-file-id="${fileObj.id}">
            <div class="file-item-info" onclick="selectFile(${fileObj.id})">
                <div class="file-item-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                    </svg>
                </div>
                <div class="file-item-details">
                    <span class="file-item-name" title="${fileObj.name}">${fileObj.name}</span>
                    <span class="file-item-size">${formatFileSize(fileObj.size)}</span>
                </div>
            </div>
            <button class="file-item-remove" onclick="removeFile(${fileObj.id})" title="Remove file">×</button>
        </div>
    `).join('');
}

// Make functions globally accessible for onclick handlers
window.selectFile = selectFile;
window.removeFile = removeFile;
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function runAnalysis() {
    if (!currentFile || isAnalysisRunning) return;
    
    isAnalysisRunning = true;
    runAgentBtn.disabled = true;
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    
    updateSystemStatus('Processing...', 'warning');
    
    // Reset agent states
    agents.forEach(agent => {
        const stepElement = document.querySelector(`.agent-step-horizontal[data-agent="${agent}"]`);
        stepElement.classList.remove('active', 'completed', 'error');
    });
    
    // Upload file
    const formData = new FormData();
    formData.append('file', currentFile.file);
    
    try {
        const response = await fetch('/api/upload-and-run', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to start analysis');
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Prefer WebSocket realtime updates if available
            if (data.workflow_id) {
                startRealtime(data.workflow_id);
            } else {
                startPolling();
            }
        } else {
            throw new Error(data.message || 'Analysis failed');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showNotification('Failed to start analysis: ' + error.message, 'error');
        updateSystemStatus('Error', 'error');
        isAnalysisRunning = false;
        runAgentBtn.disabled = false;
    }
}

function startPolling() {
    // Clear any existing polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    // Poll every 500ms for updates
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            updateProgress(data);
            
            if (data.completed) {
                clearInterval(pollingInterval);
                showResults(data.results);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 500);
}

function startRealtime(workflowId) {
    // Close any existing connection
    if (ws) {
        try { ws.close(); } catch (_) {}
        ws = null;
    }
    // Fallback: if WebSocket unavailable, use polling
    const protocol = (location.protocol === 'https:') ? 'wss' : 'ws';
    const url = `${protocol}://${location.host}/ws/${workflowId}`;
    try {
        ws = new WebSocket(url);
    } catch (e) {
        console.warn('WebSocket failed, falling back to polling:', e);
        startPolling();
        return;
    }

    ws.onopen = () => {
        // Optional: send a ping to keep connection
        try { ws.send('ping'); } catch (_) {}
    };

    ws.onmessage = (event) => {
        let payload = null;
        try {
            payload = JSON.parse(event.data);
        } catch (e) {
            return;
        }

        // Normalize payload to UI-V2 shape
        const data = { activities: [] };
        if (payload.type === 'status') {
            // Initial or status updates
            data.currentAgent = payload.current_agent || null;
            data.progress = 10; // minimal progress indicator on status
        } else if (payload.type === 'progress') {
            data.currentAgent = payload.current_agent || null;
            data.agentStatus = payload.agent_status || null;
            data.progress = typeof payload.progress === 'number' ? payload.progress : 50;
            if (payload.message) {
                data.activities.push({
                    agent: payload.agent || 'System',
                    message: payload.message,
                    type: payload.level || 'info',
                    timestamp: payload.timestamp || null
                });
            }
        } else if (payload.type === 'final') {
            // Final results
            data.completed = true;
            data.progress = 100;
            data.results = {
                severity: payload.priority || null,
                recommendation: payload.verdict || null,
            };
            if (payload.errors && payload.errors.length) {
                data.activities.push({
                    agent: 'System',
                    message: `Completed with errors: ${payload.errors.join(', ')}`,
                    type: 'error',
                    timestamp: null
                });
            } else {
                data.activities.push({
                    agent: 'System',
                    message: 'Analysis completed successfully',
                    type: 'success',
                    timestamp: null
                });
            }
        }

        updateProgress(data);
        if (data.completed) {
            showResults(data.results);
            try { ws.close(); } catch (_) {}
            ws = null;
        }
    };

    ws.onerror = (err) => {
        console.warn('WebSocket error, switching to polling:', err);
        // Use polling as backup
        try { ws.close(); } catch (_) {}
        ws = null;
        startPolling();
    };

    ws.onclose = () => {
        // No-op; if not completed, polling will continue
    };
}

function updateProgress(data) {
    // Update progress bar
    const progress = data.progress || 0;
    progressFill.style.width = progress + '%';
    progressText.textContent = progress + '%';
    
    // Update agent steps
    if (data.currentAgent) {
        updateAgentSteps(data.currentAgent, data.agentStatus);
    }
    
    // Update activity feed
    if (data.activities && data.activities.length > 0) {
        updateActivityFeed(data.activities);
    }
}

function updateAgentSteps(currentAgent, agentStatus) {
    agents.forEach((agent, index) => {
        const stepElement = document.querySelector(`.agent-step-horizontal[data-agent="${agent}"]`);
        
        // Remove all status classes
        stepElement.classList.remove('active', 'completed', 'error');
        
        if (agentStatus && agentStatus[agent]) {
            const status = agentStatus[agent];
            
            if (status === 'completed') {
                stepElement.classList.add('completed');
            } else if (status === 'running') {
                stepElement.classList.add('active');
            } else if (status === 'error') {
                stepElement.classList.add('error');
            }
        } else if (agent === currentAgent) {
            stepElement.classList.add('active');
        }
    });
}

function updateActivityFeed(activities) {
    // Clear placeholder
    const placeholder = activityFeed.querySelector('.activity-placeholder');
    if (placeholder) {
        placeholder.remove();
    }
    
    // Add new activities (only add ones we haven't seen)
    const existingActivities = activityFeed.querySelectorAll('.activity-item');
    const existingCount = existingActivities.length;
    
    if (activities.length > existingCount) {
        const newActivities = activities.slice(existingCount);
        
        newActivities.forEach(activity => {
            const activityElement = createActivityElement(activity);
            activityFeed.appendChild(activityElement);
        });
        
        // Scroll to bottom
        activityFeed.scrollTop = activityFeed.scrollHeight;
    }
}

function createActivityElement(activity) {
    const div = document.createElement('div');
    div.className = 'activity-item';
    
    const icon = getActivityIcon(activity.type);
    
    div.innerHTML = `
        <div class="activity-icon">
            ${icon}
        </div>
        <div class="activity-content">
            <div class="activity-title">${activity.agent || 'System'}</div>
            <div class="activity-description">${activity.message}</div>
            <div class="activity-time">${activity.timestamp || getTimestamp()}</div>
        </div>
    `;
    
    return div;
}

function getActivityIcon(type) {
    const icons = {
        start: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>',
        processing: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
        success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="20 6 9 17 4 12"></polyline></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };
    
    return icons[type] || icons.info;
}

function getTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString();
}

function showResults(results) {
    updateSystemStatus('Completed', 'success');
    progressFill.style.width = '100%';
    progressText.textContent = '100%';
    
    // Mark all agents as completed
    agents.forEach(agent => {
        const stepElement = document.querySelector(`.agent-step-horizontal[data-agent="${agent}"]`);
        stepElement.classList.remove('active');
        stepElement.classList.add('completed');
    });
    
    // Show results
    setTimeout(() => {
        resultsSection.style.display = 'block';
        resultsContent.innerHTML = formatResults(results);
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 1000);
}

function formatResults(results) {
    if (!results) {
        return '<p>Analysis completed successfully.</p>';
    }
    
    let html = '';
    
    if (results.severity) {
        html += `
            <div class="result-item">
                <div class="result-label">Threat Severity</div>
                <div class="result-value" style="color: ${getSeverityColor(results.severity)}">
                    ${results.severity.toUpperCase()}
                </div>
            </div>
        `;
    }
    
    if (results.recommendation) {
        html += `
            <div class="result-item">
                <div class="result-label">Recommendation</div>
                <div class="result-value">${results.recommendation}</div>
            </div>
        `;
    }
    
    if (results.actions) {
        html += `
            <div class="result-item">
                <div class="result-label">Recommended Actions</div>
                <div class="result-value">
                    <ul style="margin-left: 20px;">
                        ${results.actions.map(action => `<li>${action}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    }
    
    if (results.summary) {
        html += `
            <div class="result-item">
                <div class="result-label">Summary</div>
                <div class="result-value">${results.summary}</div>
            </div>
        `;
    }
    
    return html || '<p>Analysis completed successfully.</p>';
}

function getSeverityColor(severity) {
    const colors = {
        critical: '#ef4444',
        high: '#f59e0b',
        medium: '#f59e0b',
        low: '#10b981',
        info: '#6366f1'
    };
    return colors[severity.toLowerCase()] || '#6366f1';
}

function resetUI() {
    // Hide sections
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    
    // Reset progress
    progressFill.style.width = '0%';
    progressText.textContent = '0%';
    
    // Reset agents
    agents.forEach(agent => {
        const stepElement = document.querySelector(`.agent-step-horizontal[data-agent="${agent}"]`);
        stepElement.classList.remove('active', 'completed', 'error');
    });
    
    // Reset activity feed
    activityFeed.innerHTML = `
        <div class="activity-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <p>Waiting for agents to start...</p>
        </div>
    `;
    
    // Reset state
    isAnalysisRunning = false;
    currentAgentIndex = 0;
    
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    
    updateSystemStatus('System Ready', 'success');
}

function updateSystemStatus(text, type) {
    const statusBadge = systemStatus;
    const statusDot = statusBadge.querySelector('.status-dot');
    
    statusBadge.textContent = '';
    statusBadge.appendChild(statusDot);
    statusBadge.appendChild(document.createTextNode(text));
    
    // Reset colors
    statusBadge.style.background = '';
    statusBadge.style.borderColor = '';
    statusBadge.style.color = '';
    
    if (type === 'warning') {
        statusBadge.style.background = 'rgba(245, 158, 11, 0.1)';
        statusBadge.style.borderColor = 'rgba(245, 158, 11, 0.3)';
        statusBadge.style.color = '#f59e0b';
        statusDot.style.background = '#f59e0b';
    } else if (type === 'error') {
        statusBadge.style.background = 'rgba(239, 68, 68, 0.1)';
        statusBadge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
        statusBadge.style.color = '#ef4444';
        statusDot.style.background = '#ef4444';
    } else {
        // success/default
        statusBadge.style.background = 'rgba(16, 185, 129, 0.1)';
        statusBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        statusBadge.style.color = '#10b981';
        statusDot.style.background = '#10b981';
    }
}

function showNotification(message, type = 'info') {
    // Simple console notification for now
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // You could implement a toast notification here
    alert(message);
}
