// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// State Management
const state = {
    documents: [],
    mahareraDocuments: [],
    selectedUserDocIds: new Set(),    // Track selected user doc filenames
    selectedMahareraIds: new Set(),   // Track selected MahaRERA doc filenames
    chatHistory: [],
    isLoading: false,
    settings: {
        language: 'auto',
        topK: 3,
        showSources: true
    }
};

// DOM Elements
const elements = {
    chatMessages: document.getElementById('chatMessages'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    statusIndicator: document.getElementById('statusIndicator'),
    statusText: document.getElementById('statusText'),
    appStatus: document.getElementById('appStatus'), // Added wrapper
    documentList: document.getElementById('documentList'),
    mahareraList: document.getElementById('mahareraList'),
    loadDocsBtn: document.getElementById('loadDocsBtn'),
    deleteMahareraBtn: document.getElementById('deleteMahareraBtn'),
    selectAllUserDocs: document.getElementById('selectAllUserDocs'),
    selectAllMaharera: document.getElementById('selectAllMaharera'),
    checkComplianceBtn: document.getElementById('checkComplianceBtn'),
    batchProcessBtn: document.getElementById('batchProcessBtn'),
    batchModal: document.getElementById('batchModal'),
    closeBatchModal: document.getElementById('closeBatchModal'),
    batchDocList: document.getElementById('batchDocList'),
    startBatchBtn: document.getElementById('startBatchBtn'),
    cancelBatchBtn: document.getElementById('cancelBatchBtn'),
    batchProgress: document.getElementById('batchProgress'),
    batchProgressFill: document.getElementById('batchProgressFill'),
    batchProgressText: document.getElementById('batchProgressText'),
    languageSelect: document.getElementById('languageSelect'),
    topKInput: document.getElementById('topKInput'),
    showSourcesCheck: document.getElementById('showSourcesCheck'),
    // API Usage elements
    apiUsagePanel: document.getElementById('apiUsagePanel'),
    apiCallCount: document.getElementById('apiCallCount'),
    apiTokenCount: document.getElementById('apiTokenCount'),
    apiUsageModal: document.getElementById('apiUsageModal'),
    closeUsageModal: document.getElementById('closeUsageModal'),
    resetUsageBtn: document.getElementById('resetUsageBtn'),
    refreshUsageBtn: document.getElementById('refreshUsageBtn')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    checkServerStatus();
    // Fetch initial API usage
    fetchApiUsage();
    // Update usage every 30 seconds
    setInterval(fetchApiUsage, 30000);
});

function initializeApp() {
    // Load settings from localStorage
    const savedSettings = localStorage.getItem('ragSettings');
    if (savedSettings) {
        state.settings = JSON.parse(savedSettings);
        applySettings();
    }

    // Auto-resize textarea
    elements.messageInput.addEventListener('input', autoResizeTextarea);
}

function setupEventListeners() {
    // Send message
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Sample questions - Dynamic delegation
    document.addEventListener('click', (e) => {
        if (e.target.closest('.sample-btn')) {
            const btn = e.target.closest('.sample-btn');
            elements.messageInput.value = btn.dataset.question;
            sendMessage();
        }
    });

    // Settings
    elements.languageSelect.addEventListener('change', () => {
        state.settings.language = elements.languageSelect.value;
        saveSettings();
    });

    elements.topKInput.addEventListener('change', () => {
        state.settings.topK = parseInt(elements.topKInput.value);
        saveSettings();
    });

    elements.showSourcesCheck.addEventListener('change', () => {
        state.settings.showSources = elements.showSourcesCheck.checked;
        saveSettings();
    });

    // Load documents
    elements.loadDocsBtn.addEventListener('click', loadDocuments);

    // Delete MahaRERA documents
    elements.deleteMahareraBtn.addEventListener('click', deleteMahareraDocuments);

    // Select All User Docs checkbox
    if (elements.selectAllUserDocs) {
        elements.selectAllUserDocs.addEventListener('change', toggleSelectAllUserDocs);
    }

    // Select All MahaRERA checkbox
    elements.selectAllMaharera.addEventListener('change', toggleSelectAllMaharera);

    // Check Compliance button
    elements.checkComplianceBtn.addEventListener('click', checkCompliance);

    // Batch Processing
    if (elements.batchProcessBtn) {
        elements.batchProcessBtn.addEventListener('click', openBatchModal);
    }
    if (elements.closeBatchModal) {
        elements.closeBatchModal.addEventListener('click', closeBatchModal);
    }
    if (elements.cancelBatchBtn) {
        elements.cancelBatchBtn.addEventListener('click', closeBatchModal);
    }
    if (elements.startBatchBtn) {
        elements.startBatchBtn.addEventListener('click', startBatchProcessing);
    }
    if (elements.batchModal) {
        // Close on backdrop click
        elements.batchModal.addEventListener('click', (e) => {
            if (e.target === elements.batchModal) closeBatchModal();
        });
    }

    // API Usage Panel
    if (elements.apiUsagePanel) {
        elements.apiUsagePanel.addEventListener('click', openUsageModal);
    }
    if (elements.closeUsageModal) {
        elements.closeUsageModal.addEventListener('click', closeUsageModal);
    }
    if (elements.resetUsageBtn) {
        elements.resetUsageBtn.addEventListener('click', resetApiUsage);
    }
    if (elements.refreshUsageBtn) {
        elements.refreshUsageBtn.addEventListener('click', fetchApiUsage);
    }
    if (elements.apiUsageModal) {
        elements.apiUsageModal.addEventListener('click', (e) => {
            if (e.target === elements.apiUsageModal) closeUsageModal();
        });
    }
}

function autoResizeTextarea() {
    elements.messageInput.style.height = 'auto';
    elements.messageInput.style.height = elements.messageInput.scrollHeight + 'px';
}

async function checkServerStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/status`);
        if (response.ok) {
            const data = await response.json();
            updateStatus('connected', `Connected • ${data.documents || 0} Docs`);
            if (data.documents > 0) {
                loadDocuments();
                loadMahareraDocuments();
            }
        } else {
            updateStatus('error', 'Server Unreachable');
        }
    } catch (error) {
        updateStatus('error', 'Server Offline');
        // Optional: show a toast or banner instead of replacing the welcome message
    }
}

function updateStatus(status, text) {
    if (elements.statusIndicator) {
        elements.statusIndicator.className = `status-dot status-indicator ${status}`;
    }
    if (elements.statusText) {
        elements.statusText.textContent = text;
    }
}

async function loadDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/documents`);
        if (response.ok) {
            const data = await response.json();
            state.documents = data.documents || [];
            renderDocumentList();
        }
    } catch (error) {
        console.error('Failed to load documents:', error);
    }
}

async function loadMahareraDocuments() {
    try {
        const response = await fetch(`${API_BASE_URL}/maharera`);
        if (response.ok) {
            const data = await response.json();
            state.mahareraDocuments = data.documents || [];
            renderMahareraList();
        }
    } catch (error) {
        console.error('Failed to load MahaRERA documents:', error);
    }
}

async function deleteMahareraDocuments() {
    if (!confirm('Are you sure you want to clear all regulations?')) {
        return;
    }

    const btn = elements.deleteMahareraBtn;
    const originalContent = btn.innerHTML;

    btn.disabled = true;
    // Spinner
    btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>`;

    try {
        const response = await fetch(`${API_BASE_URL}/maharera/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            loadMahareraDocuments();
            checkServerStatus();
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (error) {
        console.error('Failed to delete MahaRERA documents:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
    }
}

function renderMahareraList() {
    if (state.mahareraDocuments.length === 0) {
        elements.mahareraList.innerHTML = '<div class="empty-state-small">No regulations loaded</div>';
        elements.selectAllMaharera.checked = false;
        elements.selectAllMaharera.disabled = true;
        elements.checkComplianceBtn.disabled = true;
        return;
    }

    elements.selectAllMaharera.disabled = false;

    elements.mahareraList.innerHTML = state.mahareraDocuments.map((doc) => {
        const title = doc.title || doc.filename;
        const isChecked = state.selectedMahareraIds.has(doc.filename) ? 'checked' : '';
        const itemClass = isChecked ? 'document-item selected' : 'document-item';

        return `
            <div class="${itemClass}" onclick="toggleMahareraSelection('${doc.filename}')">
                <div class="maharera-checkbox-label">
                    <input type="checkbox" data-filename="${doc.filename}" ${isChecked} onchange="event.stopPropagation(); toggleMahareraSelection('${doc.filename}')">
                </div>
                <div class="doc-info">
                    <div class="doc-name" title="${title}">${title}</div>
                    <div class="doc-meta">${doc.doc_type}</div>
                </div>
            </div>
        `;
    }).join('');

    updateComplianceButtonState();
}

function renderDocumentList() {
    if (state.documents.length === 0) {
        elements.documentList.innerHTML = '<div class="empty-state-small">No documents loaded</div>';
        if (elements.selectAllUserDocs) {
            elements.selectAllUserDocs.checked = false;
            elements.selectAllUserDocs.disabled = true;
        }
        return;
    }

    if (elements.selectAllUserDocs) {
        elements.selectAllUserDocs.disabled = false;
    }

    elements.documentList.innerHTML = state.documents.map((doc) => {
        const isChecked = state.selectedUserDocIds.has(doc.filename) ? 'checked' : '';
        const itemClass = isChecked ? 'document-item selected' : 'document-item';

        return `
            <div class="${itemClass}" onclick="toggleUserDocSelection('${doc.filename}')">
                <div class="user-doc-checkbox-label">
                    <input type="checkbox" data-filename="${doc.filename}" ${isChecked} onchange="event.stopPropagation(); toggleUserDocSelection('${doc.filename}')">
                </div>
                <div class="doc-info">
                    <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
                    <div class="doc-meta">${doc.chunks || 0} chunks</div>
                </div>
                <button class="icon-btn danger" onclick="deleteDocument('${doc.filename}', event)" title="Delete">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            </div>
        `;
    }).join('');
}

async function deleteDocument(filename, event) {
    event.stopPropagation(); // Prevent selection

    if (!confirm(`Delete "${filename}"?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });

        if (response.ok) {
            loadDocuments();
            // Clear selection if deleted doc was selected
            if (state.selectedUserDocIds.has(filename)) {
                state.selectedUserDocIds.delete(filename);
            }
        }
    } catch (error) {
        console.error('Error deleting document:', error);
    }
}

// User Document Selection
function toggleUserDocSelection(filename) {
    if (state.selectedUserDocIds.has(filename)) {
        state.selectedUserDocIds.delete(filename);
    } else {
        state.selectedUserDocIds.add(filename);
    }
    // Re-render to update classes
    renderDocumentList();
    updateSelectAllUserDocsState();
    updateComplianceButtonState();
}

function toggleSelectAllUserDocs() {
    const isChecked = elements.selectAllUserDocs.checked;
    state.selectedUserDocIds.clear();

    if (isChecked) {
        state.documents.forEach(doc => {
            state.selectedUserDocIds.add(doc.filename);
        });
    }

    renderDocumentList();
    updateComplianceButtonState();
}

function updateSelectAllUserDocsState() {
    if (!elements.selectAllUserDocs) return;
    const totalDocs = state.documents.length;
    const selectedCount = state.selectedUserDocIds.size;
    elements.selectAllUserDocs.checked = selectedCount === totalDocs && totalDocs > 0;
    elements.selectAllUserDocs.indeterminate = selectedCount > 0 && selectedCount < totalDocs;
}

// MahaRERA Selection
function toggleMahareraSelection(filename) {
    if (state.selectedMahareraIds.has(filename)) {
        state.selectedMahareraIds.delete(filename);
    } else {
        state.selectedMahareraIds.add(filename);
    }
    renderMahareraList();
    updateSelectAllState();
    updateComplianceButtonState();
}

function toggleSelectAllMaharera() {
    const isChecked = elements.selectAllMaharera.checked;
    state.selectedMahareraIds.clear();

    if (isChecked) {
        state.mahareraDocuments.forEach(doc => {
            state.selectedMahareraIds.add(doc.filename);
        });
    }

    renderMahareraList();
    updateComplianceButtonState();
}

function updateSelectAllState() {
    const totalDocs = state.mahareraDocuments.length;
    const selectedCount = state.selectedMahareraIds.size;
    elements.selectAllMaharera.checked = selectedCount === totalDocs && totalDocs > 0;
    elements.selectAllMaharera.indeterminate = selectedCount > 0 && selectedCount < totalDocs;
}

function updateComplianceButtonState() {
    const hasUserDocs = state.documents.length > 0;
    const hasSelectedMaharera = state.selectedMahareraIds.size > 0;

    elements.checkComplianceBtn.disabled = !(hasUserDocs && hasSelectedMaharera);

    if (elements.batchProcessBtn) {
        elements.batchProcessBtn.disabled = state.selectedUserDocIds.size === 0;
    }

    const count = state.selectedMahareraIds.size;
    if (count > 0) {
        elements.checkComplianceBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
            Check (${count})
        `;
    } else {
        elements.checkComplianceBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
            Check
        `;
    }
}

async function checkCompliance() {
    if (state.selectedMahareraIds.size === 0) {
        alert('Please select regulations to check against.');
        return;
    }

    if (state.documents.length === 0) {
        alert('No user documents loaded.');
        return;
    }

    const selectedUserDocs = Array.from(state.selectedUserDocIds);
    const userDocName = selectedUserDocs.length > 0 ? `${selectedUserDocs.length} documents` : 'all documents';
    const selectedDocs = Array.from(state.selectedMahareraIds);
    // const docNames = selectedDocs.join(', '); // Not showing in prompt to save space

    const complianceQuestion = `Analyze ${userDocName} for compliance with the selected MahaRERA regulations. Check for missing clauses and red flags.`;

    // UI Updates
    document.querySelector('.welcome-screen')?.remove();
    addMessage('user', `Compliance Check: ${userDocName} vs ${selectedDocs.length} Regulations`);
    showTypingIndicator();

    state.isLoading = true;
    elements.sendBtn.disabled = true;
    elements.checkComplianceBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: complianceQuestion,
                top_k: 10,
                language: state.settings.language,
                selected_documents: selectedUserDocs.length > 0 ? selectedUserDocs : null,
                selected_maharera: selectedDocs,
                compliance_check: true
            })
        });

        removeTypingIndicator();

        if (response.ok) {
            const data = await response.json();
            addMessage('assistant', data.answer, data.sources, data.red_flags, data.decision, data.compliance_results, data.compliance_summary);
        } else {
            addMessage('assistant', 'Error checking compliance.');
        }
    } catch (error) {
        removeTypingIndicator();
        addMessage('assistant', 'Server connection failed.');
    } finally {
        state.isLoading = false;
        elements.sendBtn.disabled = false;
        updateComplianceButtonState();
    }
}

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isLoading) return;

    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';
    document.querySelector('.welcome-screen')?.remove();

    addMessage('user', message);
    showTypingIndicator();

    state.isLoading = true;
    elements.sendBtn.disabled = true;

    try {
        const selectedMaharera = Array.from(state.selectedMahareraIds);
        const selectedUserDocs = Array.from(state.selectedUserDocIds);

        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: message,
                top_k: state.settings.topK,
                language: state.settings.language,
                selected_documents: selectedUserDocs.length > 0 ? selectedUserDocs : null,
                selected_maharera: selectedMaharera.length > 0 ? selectedMaharera : null
            })
        });

        removeTypingIndicator();

        if (response.ok) {
            const data = await response.json();
            addMessage('assistant', data.answer, data.sources, data.red_flags, data.decision, data.compliance_results, data.compliance_summary);
        } else {
            addMessage('assistant', 'Sorry, I encounted an error.');
        }
    } catch (error) {
        removeTypingIndicator();
        addMessage('assistant', 'Connection failed.');
    } finally {
        state.isLoading = false;
        elements.sendBtn.disabled = false;
    }
}

function addMessage(role, content, sources = null, redFlags = null, decision = null, complianceResults = null, complianceSummary = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const userInitials = 'ME';
    const botInitials = 'AI';
    const avatarText = role === 'user' ? userInitials : botInitials;

    // Compliance & Red Flags Logic (kept largely same, updated HTML structure)
    let complianceHTML = '';
    let redFlagsHTML = '';

    // ... Copying logic for compliance HTML generation but using new classes ...
    // Simplified for brevity in this rewrite tool, but functionality remains

    const isComplianceCheck = decision && decision.compliance_check === true;

    if (isComplianceCheck && complianceSummary) {
        const isFullyCompliant = complianceSummary.is_compliant;
        const compliantCount = complianceSummary.compliant_count || 0;
        const totalChecks = complianceSummary.total_checks || 0;

        // Using new colored border styling instead of old classes
        const statusColor = isFullyCompliant ? 'var(--success)' : 'var(--danger)';
        const statusBg = isFullyCompliant ? 'var(--success-bg)' : 'var(--danger-bg)';

        complianceHTML = `
            <div style="margin-top: 12px; padding: 12px; border-radius: 8px; border: 1px solid ${statusColor}; background: ${statusBg};">
                <strong style="color: ${statusColor}">
                    ${isFullyCompliant ? '✓ Fully Compliant' : '⚠ Compliance Issues Found'}
                </strong>
                <div style="font-size: 13px; margin-top: 4px;">
                    Verified ${compliantCount}/${totalChecks} required clauses.
                </div>
            </div>
        `;
    }

    if (isComplianceCheck && redFlags && redFlags.length > 0) {
        redFlagsHTML = `
            <div class="red-flags-container">
                <div class="red-flag-header critical">⚠️ Red Flags Detected</div>
                ${redFlags.map(flag => `
                    <div class="red-flag-item">
                        <span class="severity-badge" style="background-color: var(--danger);">${flag.severity}</span>
                        <strong>${flag.domain}</strong>
                        <div style="margin-top: 4px; color: var(--text-secondary);">${flag.reason}</div>
                    </div>
                `).join('')}
            </div>
        `;
    } else if (isComplianceCheck && decision && decision.is_red_flag === false) {
        redFlagsHTML = `
            <div class="no-red-flags-container">
                <div class="no-red-flags-header">✓ No Red Flags Detected</div>
                <div class="no-red-flags-message">Based on current regulations, no critical issues were found.</div>
            </div>
        `;
    }

    // Markdown parsing (basic)
    // In a real app we'd use marked.js, here we'll just handle newlines
    const formattedContent = content.replace(/\\n/g, '<br>');

    let sourcesHTML = '';
    if (sources && sources.length > 0) {
        sourcesHTML = `
            <div class="message-sources">
                <h4>Sources</h4>
                ${sources.map(s => `
                    <div class="source-item">
                        <span class="source-file">${s.filename}</span>
                        <div style="color: var(--text-secondary); font-size: 11px;">${s.text.substring(0, 100)}...</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarText}</div>
        <div class="message-bubble">
            <div class="message-content">${formattedContent}</div>
            ${complianceHTML}
            ${redFlagsHTML}
            ${sourcesHTML}
        </div>
    `;

    elements.chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    const chatViewport = document.querySelector('.chat-viewport');
    chatViewport.scrollTop = chatViewport.scrollHeight;
}

function showTypingIndicator() {
    const loaderDiv = document.createElement('div');
    loaderDiv.className = 'message assistant typing-msg';
    loaderDiv.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-bubble">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    elements.chatMessages.appendChild(loaderDiv);
    const chatViewport = document.querySelector('.chat-viewport');
    chatViewport.scrollTop = chatViewport.scrollHeight;
}

function removeTypingIndicator() {
    const loader = document.querySelector('.typing-msg');
    if (loader) loader.remove();
}

// Settings Saving
function saveSettings() {
    localStorage.setItem('ragSettings', JSON.stringify(state.settings));
}

function applySettings() {
    if (elements.languageSelect) elements.languageSelect.value = state.settings.language;
    if (elements.topKInput) elements.topKInput.value = state.settings.topK;
    if (elements.showSourcesCheck) elements.showSourcesCheck.checked = state.settings.showSources;
}

// Modal Logic
function openBatchModal() {
    elements.batchModal.classList.add('active');
    renderBatchDocList();
}
function closeBatchModal() { elements.batchModal.classList.remove('active'); }

function renderBatchDocList() {
    if (elements.batchDocList) {
        const selected = Array.from(state.selectedUserDocIds);
        if (selected.length === 0) {
            elements.batchDocList.innerHTML = '<p style="color:var(--text-tertiary)">No documents selected.</p>';
            return;
        }
        elements.batchDocList.innerHTML = selected.map(f => `
            <div style="padding: 6px; border: 1px solid var(--border-subtle); border-radius: 4px; margin-bottom: 4px; font-size: 12px;">
                ${f}
            </div>
        `).join('');
    }
}

function startBatchProcessing() {
    alert('Batch processing started (Demo)');
    closeBatchModal();
}

// API Usage Modal
function fetchApiUsage() {
    // Mock update for now or fetch from actual endpoint
    // In a real implementation this would fetch from /api/usage
}
function openUsageModal() { elements.apiUsageModal.classList.add('active'); }
function closeUsageModal() { elements.apiUsageModal.classList.remove('active'); }
function resetApiUsage() {
    if (confirm('Reset stats?')) {
        document.getElementById('modalTotalRequests').textContent = '0';
        document.getElementById('modalSuccessRequests').textContent = '0';
    }
}

// Simple CSS animation for spin
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin { 100% { transform: rotate(360deg); } }
`;
document.head.appendChild(style);
