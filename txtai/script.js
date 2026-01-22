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

    // Sample questions
    document.querySelectorAll('.sample-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            elements.messageInput.value = btn.dataset.question;
            sendMessage();
        });
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
            updateStatus('connected', `Connected - ${data.documents || 0} documents loaded`);
            if (data.documents > 0) {
                loadDocuments();
                loadMahareraDocuments();
            }
        } else {
            updateStatus('error', 'Server not responding');
        }
    } catch (error) {
        updateStatus('error', 'Server offline - Start backend first');
        showOfflineMessage();
    }
}

function updateStatus(status, text) {
    elements.statusIndicator.className = `status-indicator ${status}`;
    elements.statusText.textContent = text;
}

function showOfflineMessage() {
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.innerHTML = `
            <h2>Backend Server Required</h2>
            <p>Please start the Python backend server first:</p>
            <div style="background: #f0fdfa; padding: 1rem; border-radius: 8px; margin: 1rem 0; border: 1px solid #ccfbf1;">
                <code style="color: #10b981;">python api_server.py</code>
            </div>
            <p style="font-size: 0.875rem; color: #64748b;">
                The server provides the RAG functionality, document indexing, and LLM integration.
            </p>
        `;
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
    if (!confirm('Are you sure you want to delete ALL MahaRERA documents? They will be re-fetched automatically on next server restart.')) {
        return;
    }
    
    const btn = elements.deleteMahareraBtn;
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px; animation: spin 1s linear infinite;">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
        <span>Deleting...</span>
    `;
    
    try {
        const response = await fetch(`${API_BASE_URL}/maharera/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            loadMahareraDocuments();
            checkServerStatus(); // Refresh status
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (error) {
        console.error('Failed to delete MahaRERA documents:', error);
        alert('Failed to connect to server');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function renderMahareraList() {
    if (state.mahareraDocuments.length === 0) {
        elements.mahareraList.innerHTML = '<p class="empty-state">No regulations loaded</p>';
        elements.selectAllMaharera.checked = false;
        elements.selectAllMaharera.disabled = true;
        elements.checkComplianceBtn.disabled = true;
        return;
    }

    elements.selectAllMaharera.disabled = false;

    const docTypeIcons = {
        'central_law': '[LAW]',
        'rules': '[RULE]',
        'regulations': '[REG]',
        'circulars': '[CIR]',
        'orders': '[ORD]',
        'regulatory_orders': '[ORD]',
        'forms': '[FORM]'
    };

    elements.mahareraList.innerHTML = state.mahareraDocuments.map((doc) => {
        const icon = docTypeIcons[doc.doc_type] || '[DOC]';
        const charCount = doc.char_count ? doc.char_count.toLocaleString() : '0';
        const title = doc.title || doc.filename;
        const shortTitle = title.length > 35 ? title.substring(0, 35) + '...' : title;
        const date = doc.date || 'Unknown';
        const isChecked = state.selectedMahareraIds.has(doc.filename) ? 'checked' : '';
        
        return `
            <div class="document-item maharera-item" title="${title}">
                <label class="maharera-checkbox-label">
                    <input type="checkbox" class="maharera-checkbox" data-filename="${doc.filename}" ${isChecked} onchange="toggleMahareraSelection('${doc.filename}')">
                </label>
                <div class="doc-info">
                    <div class="doc-name"><span class="doc-type-icon">${icon}</span> ${shortTitle}</div>
                    <div class="doc-meta">${doc.doc_type} - ${date} - ${charCount} chars</div>
                </div>
            </div>
        `;
    }).join('');
    
    updateComplianceButtonState();
}

function renderDocumentList() {
    if (state.documents.length === 0) {
        elements.documentList.innerHTML = '<p class="empty-state">No documents loaded</p>';
        if (elements.selectAllUserDocs) {
            elements.selectAllUserDocs.checked = false;
            elements.selectAllUserDocs.disabled = true;
        }
        return;
    }
    
    if (elements.selectAllUserDocs) {
        elements.selectAllUserDocs.disabled = false;
    }

    elements.documentList.innerHTML = state.documents.map((doc, index) => {
        const charCount = doc.char_count ? doc.char_count.toLocaleString() : '0';
        const chunks = doc.chunks || 0;
        const isChecked = state.selectedUserDocIds.has(doc.filename) ? 'checked' : '';
        return `
            <div class="document-item" data-filename="${doc.filename}">
                <label class="user-doc-checkbox-label">
                    <input type="checkbox" class="user-doc-checkbox" data-filename="${doc.filename}" ${isChecked} onchange="toggleUserDocSelection('${doc.filename}')">
                </label>
                <div class="doc-info" style="flex-grow: 1;">
                    <div class="doc-name">${doc.filename}</div>
                    <div class="doc-meta">${charCount} chars - ${chunks} chunks</div>
                </div>
                <button class="delete-btn" onclick="deleteDocument('${doc.filename}', event)" title="Delete document" style="background: none; border: none; color: #ef4444; cursor: pointer; padding: 4px; opacity: 0.6; transition: opacity 0.2s;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            </div>
        `;
    }).join('');
}

async function deleteDocument(filename, event) {
    event.stopPropagation(); // Prevent selection
    
    if (!confirm(`Are you sure you want to delete "${filename}"? This will remove it from the index and delete the file.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename })
        });
        
        if (response.ok) {
            // Reload documents
            loadDocuments();
            // Clear selection if deleted doc was selected
            if (state.selectedDocument === filename) {
                state.selectedDocument = null;
            }
        } else {
            const data = await response.json();
            alert(`Error deleting document: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting document:', error);
        alert('Error deleting document. See console for details.');
    }
}

function toggleDocumentSelection(filename) {
    if (state.selectedDocument === filename) {
        state.selectedDocument = null;
    } else {
        state.selectedDocument = filename;
    }
    renderDocumentList();
}

// User Document Selection Functions
function toggleUserDocSelection(filename) {
    if (state.selectedUserDocIds.has(filename)) {
        state.selectedUserDocIds.delete(filename);
    } else {
        state.selectedUserDocIds.add(filename);
    }
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
    
    // Update all user doc checkboxes
    document.querySelectorAll('.user-doc-checkbox').forEach(cb => {
        cb.checked = isChecked;
    });
    
    updateComplianceButtonState();
}

function updateSelectAllUserDocsState() {
    if (!elements.selectAllUserDocs) return;
    
    const totalDocs = state.documents.length;
    const selectedCount = state.selectedUserDocIds.size;
    
    elements.selectAllUserDocs.checked = selectedCount === totalDocs && totalDocs > 0;
    elements.selectAllUserDocs.indeterminate = selectedCount > 0 && selectedCount < totalDocs;
}

// MahaRERA Selection Functions
function toggleMahareraSelection(filename) {
    if (state.selectedMahareraIds.has(filename)) {
        state.selectedMahareraIds.delete(filename);
    } else {
        state.selectedMahareraIds.add(filename);
    }
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
    
    // Update all checkboxes
    document.querySelectorAll('.maharera-checkbox').forEach(cb => {
        cb.checked = isChecked;
    });
    
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
    
    // Enable batch button when user docs are selected
    if (elements.batchProcessBtn) {
        elements.batchProcessBtn.disabled = state.selectedUserDocIds.size === 0;
    }
    
    // Update button text to show count
    const count = state.selectedMahareraIds.size;
    if (count > 0) {
        elements.checkComplianceBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
            Check (${count})
        `;
    } else {
        elements.checkComplianceBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
            Check Compliance
        `;
    }
}

async function checkCompliance() {
    if (state.selectedMahareraIds.size === 0) {
        alert('Please select at least one MahaRERA document to check compliance against.');
        return;
    }
    
    if (state.documents.length === 0) {
        alert('No user documents loaded. Please add documents to check compliance.');
        return;
    }
    
    // Use selected user documents (multi-select)
    const selectedUserDocs = Array.from(state.selectedUserDocIds);
    const userDocName = selectedUserDocs.length > 0 
        ? selectedUserDocs.join(', ') 
        : 'all user documents';
    
    // Build a compliance question
    const selectedDocs = Array.from(state.selectedMahareraIds);
    const docNames = selectedDocs.map(f => {
        const doc = state.mahareraDocuments.find(d => d.filename === f);
        return doc ? (doc.title || doc.filename) : f;
    }).join(', ');
    
    const complianceQuestion = `Analyze ${userDocName} for compliance with the following MahaRERA regulations: ${docNames}. Check if my real estate agreement follows all the guidelines, rules, and requirements specified in these regulatory documents. Highlight any compliance issues, missing clauses, or areas of concern.`;
    
    // Remove welcome message
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();
    
    // Add user message showing compliance check
    addMessage('user', `Compliance Check: "${userDocName}" against ${selectedDocs.length} MahaRERA document(s)`);
    
    // Show typing indicator
    showTypingIndicator();
    
    state.isLoading = true;
    elements.sendBtn.disabled = true;
    elements.checkComplianceBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: complianceQuestion,
                top_k: 10,  // Get more results for thorough compliance check
                language: state.settings.language,
                selected_documents: selectedUserDocs.length > 0 ? selectedUserDocs : null,  // Multi-select user docs
                selected_maharera: selectedDocs,  // Pass selected MahaRERA docs
                compliance_check: true  // Flag to trigger red flag detection
            })
        });
        
        removeTypingIndicator();
        
        if (response.ok) {
            const data = await response.json();
            addMessage('assistant', data.answer, data.sources, data.red_flags, data.decision, data.compliance_results, data.compliance_summary);
        } else {
            const errorData = await response.json();
            addMessage('assistant', `Error checking compliance: ${errorData.error || 'Unknown error'}`);
        }
    } catch (error) {
        removeTypingIndicator();
        addMessage('assistant', 'Failed to connect to server. Please ensure the backend is running.');
        console.error('Compliance check error:', error);
    } finally {
        state.isLoading = false;
        elements.sendBtn.disabled = false;
        updateComplianceButtonState();
    }
}

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isLoading) return;

    // Clear input
    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';

    // Remove welcome message
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    // Add user message
    addMessage('user', message);

    // Show typing indicator
    showTypingIndicator();

    state.isLoading = true;
    elements.sendBtn.disabled = true;

    try {
        // Include selected docs if any are checked
        const selectedMaharera = Array.from(state.selectedMahareraIds);
        const selectedUserDocs = Array.from(state.selectedUserDocIds);
        
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
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
            addMessage('assistant', 'Sorry, I encountered an error processing your question. Please try again.');
        }
    } catch (error) {
        removeTypingIndicator();
        addMessage('assistant', 'Unable to connect to server. Please ensure the backend is running.');
    } finally {
        state.isLoading = false;
        elements.sendBtn.disabled = false;
    }
}

function addMessage(role, content, sources = null, redFlags = null, decision = null, complianceResults = null, complianceSummary = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const userIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;
    const botIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>`;
    
    const avatar = role === 'user' ? userIcon : botIcon;
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    // Build compliance verification HTML (required clauses check)
    let complianceHTML = '';
    const isComplianceCheck = decision && decision.compliance_check === true;
    
    if (isComplianceCheck && complianceSummary) {
        const isFullyCompliant = complianceSummary.is_compliant;
        const compliantCount = complianceSummary.compliant_count || 0;
        const totalChecks = complianceSummary.total_checks || 0;
        const missingCritical = complianceSummary.critical_missing || [];
        const missingHigh = complianceSummary.high_missing || [];
        const missingMedium = complianceSummary.medium_missing || [];
        
        const importanceColors = {
            'CRITICAL': '#dc2626',
            'HIGH': '#ea580c',
            'MEDIUM': '#ca8a04'
        };
        
        const importanceIcons = {
            'CRITICAL': '[!]',
            'HIGH': '[!]',
            'MEDIUM': '[i]'
        };
        
        complianceHTML = `
            <div class="compliance-container ${isFullyCompliant ? 'compliant' : 'non-compliant'}">
                <div class="compliance-header ${isFullyCompliant ? '' : 'has-issues'}">
                    Required Clauses Verification: ${compliantCount}/${totalChecks} Found
                </div>
                ${!isFullyCompliant ? `
                    <div class="compliance-missing">
                        ${missingCritical.length > 0 ? `
                            <div class="missing-group critical">
                                <div class="missing-group-title">${importanceIcons['CRITICAL']} Critical Missing (${missingCritical.length})</div>
                                ${missingCritical.map(r => `
                                    <div class="missing-item" style="border-left-color: ${importanceColors['CRITICAL']}">
                                        <span class="missing-domain">${r.domain}</span>
                                        <span class="missing-desc">${escapeHtml(r.description)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                        ${missingHigh.length > 0 ? `
                            <div class="missing-group high">
                                <div class="missing-group-title">${importanceIcons['HIGH']} High Priority Missing (${missingHigh.length})</div>
                                ${missingHigh.map(r => `
                                    <div class="missing-item" style="border-left-color: ${importanceColors['HIGH']}">
                                        <span class="missing-domain">${r.domain}</span>
                                        <span class="missing-desc">${escapeHtml(r.description)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                        ${missingMedium.length > 0 ? `
                            <div class="missing-group medium">
                                <div class="missing-group-title">${importanceIcons['MEDIUM']} Medium Priority Missing (${missingMedium.length})</div>
                                ${missingMedium.map(r => `
                                    <div class="missing-item" style="border-left-color: ${importanceColors['MEDIUM']}">
                                        <span class="missing-domain">${r.domain}</span>
                                        <span class="missing-desc">${escapeHtml(r.description)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                ` : `
                    <div class="compliance-all-found">
                        All required clauses have been found in the document.
                    </div>
                `}
            </div>
        `;
    }

    // Build red flags HTML - ONLY show for compliance checks
    let redFlagsHTML = '';
    
    if (isComplianceCheck && redFlags && redFlags.length > 0) {
        const severityColors = {
            'CRITICAL': '#dc2626',
            'HIGH': '#ea580c',
            'MEDIUM': '#ca8a04',
            'LOW': '#65a30d'
        };
        const severityIcons = {
            'CRITICAL': '[!!]',
            'HIGH': '[!]',
            'MEDIUM': '[~]',
            'LOW': '[i]'
        };
        
        const isRedFlag = decision && decision.is_red_flag;
        const headerClass = isRedFlag ? 'red-flag-header critical' : 'red-flag-header';
        const headerText = isRedFlag ? 'RED FLAGS DETECTED - Non-Compliant Clauses Found' : 'Potential Issues Found';
        
        redFlagsHTML = `
            <div class="red-flags-container">
                <div class="${headerClass}">${headerText}</div>
                ${redFlags.map((flag, idx) => {
                    const color = severityColors[flag.severity] || '#666';
                    const icon = severityIcons[flag.severity] || '[?]';
                    const clauseSrc = flag.clause_source || {};
                    const authSupport = (flag.authority_support || []).slice(0, 2);
                    const hasAuthSupport = flag.has_authority_support !== false && authSupport.length > 0;
                    
                    return `
                        <div class="red-flag-item" style="border-left: 4px solid ${color}">
                            <div class="red-flag-title">
                                <span class="severity-badge" style="background: ${color}">${icon} ${flag.severity}</span>
                                <span class="rule-id">${flag.rule_id}</span>
                                <span class="domain-badge">${flag.domain}</span>
                            </div>
                            <div class="red-flag-reason">${escapeHtml(flag.reason)}</div>
                            ${clauseSrc.filename ? `
                                <div class="clause-source">
                                    <strong>Found in:</strong> ${escapeHtml(clauseSrc.filename)} ${clauseSrc.section || ''}
                                    ${clauseSrc.excerpt ? `<div class="clause-excerpt">"${escapeHtml(clauseSrc.excerpt.substring(0, 150))}..."</div>` : ''}
                                </div>
                            ` : ''}
                            ${hasAuthSupport ? `
                                <div class="authority-support">
                                    <strong>Authority Reference:</strong>
                                    ${authSupport.map(auth => `
                                        <div class="auth-item">- ${escapeHtml(auth.filename)}: "${escapeHtml(auth.excerpt.substring(0, 100))}..."</div>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } else if (isComplianceCheck && decision && decision.is_red_flag === false) {
        // No red flags detected - show compliance message (ONLY for compliance checks)
        redFlagsHTML = `
            <div class="no-red-flags-container">
                <div class="no-red-flags-header">No Red Flags Detected</div>
                <div class="no-red-flags-message">
                    The analyzed sections of your document appear to be compliant with the selected MahaRERA regulations 
                    based on our rule-based analysis. However, please note:
                    <ul>
                        <li>This analysis covers only the retrieved document sections</li>
                        <li>Manual review by a legal professional is still recommended</li>
                        <li>Some nuanced violations may require human interpretation</li>
                    </ul>
                </div>
            </div>
        `;
    }

    let sourcesHTML = '';
    if (sources && sources.length > 0 && state.settings.showSources) {
        sourcesHTML = `
            <div class="message-sources">
                <h4>Sources (${sources.length}):</h4>
                ${sources.map((src, idx) => `
                    <div class="source-item">
                        <div class="source-file">[${idx + 1}] <strong>${src.filename}</strong> - ${src.section || 'Section ' + (src.chunk_idx + 1)} - Score: ${src.score.toFixed(4)}</div>
                        <div class="source-text">${escapeHtml(src.text.substring(0, 200))}...</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    const copyIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
    const checkIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    const downloadIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`;
    
    // Show download button only for compliance checks
    const showDownloadBtn = isComplianceCheck && role === 'assistant';
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${complianceHTML}
            ${redFlagsHTML}
            <div class="message-bubble">
                ${escapeHtml(content)}
                <div class="message-actions">
                    <button class="copy-btn" title="Copy message">
                        ${copyIcon}
                    </button>
                    ${showDownloadBtn ? `
                        <button class="download-btn" title="Download Compliance Report">
                            ${downloadIcon}
                        </button>
                    ` : ''}
                </div>
            </div>
            ${sourcesHTML}
            <div class="message-time">${time}</div>
        </div>
    `;
    
    // Store data for download
    messageDiv._reportData = {
        content,
        redFlags,
        decision,
        complianceResults,
        complianceSummary,
        sources
    };
    
    // Add click handler for copy button
    const copyBtn = messageDiv.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            try {
                await navigator.clipboard.writeText(content);
                copyBtn.innerHTML = checkIcon;
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.innerHTML = copyIcon;
                    copyBtn.classList.remove('copied');
                }, 2000);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        });
    }
    
    // Add click handler for download button
    const downloadBtn = messageDiv.querySelector('.download-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            generateComplianceReport(messageDiv._reportData);
        });
    }

    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

    // Add to history
    state.chatHistory.push({ role, content, sources, time });
}

function generateComplianceReport(data) {
    const { content, redFlags, decision, complianceResults, complianceSummary, sources } = data;
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
    const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    
    // Initialize jsPDF
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    let yPos = 20;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    const maxWidth = pageWidth - (margin * 2);
    
    // Helper function to add text with word wrap and page breaks
    function addText(text, fontSize = 10, isBold = false, color = [0, 0, 0]) {
        doc.setFontSize(fontSize);
        doc.setFont('helvetica', isBold ? 'bold' : 'normal');
        doc.setTextColor(color[0], color[1], color[2]);
        
        const lines = doc.splitTextToSize(text, maxWidth);
        for (let i = 0; i < lines.length; i++) {
            if (yPos > pageHeight - 30) {
                doc.addPage();
                yPos = 20;
            }
            doc.text(lines[i], margin, yPos);
            yPos += fontSize * 0.5;
        }
        yPos += 2;
    }
    
    function addLine() {
        if (yPos > pageHeight - 30) {
            doc.addPage();
            yPos = 20;
        }
        doc.setDrawColor(200, 200, 200);
        doc.line(margin, yPos, pageWidth - margin, yPos);
        yPos += 8;
    }
    
    function addSection(title) {
        yPos += 5;
        if (yPos > pageHeight - 40) {
            doc.addPage();
            yPos = 20;
        }
        doc.setFillColor(59, 130, 246);
        doc.rect(margin, yPos - 5, maxWidth, 10, 'F');
        doc.setFontSize(12);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(255, 255, 255);
        doc.text(title, margin + 3, yPos + 2);
        yPos += 15;
    }
    
    // Title
    doc.setFillColor(30, 58, 138);
    doc.rect(0, 0, pageWidth, 35, 'F');
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('REAL ESTATE COMPLIANCE REPORT', pageWidth / 2, 15, { align: 'center' });
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated: ${dateStr} at ${timeStr}`, pageWidth / 2, 25, { align: 'center' });
    yPos = 50;
    
    // Executive Summary
    addSection('EXECUTIVE SUMMARY');
    
    if (complianceSummary) {
        const status = complianceSummary.is_compliant ? 'COMPLIANT' : 'NON-COMPLIANT';
        const statusColor = complianceSummary.is_compliant ? [22, 163, 74] : [220, 38, 38];
        
        addText(`Overall Status: `, 11, true);
        yPos -= 7;
        doc.setTextColor(statusColor[0], statusColor[1], statusColor[2]);
        doc.text(status, margin + 32, yPos);
        yPos += 7;
        
        addText(`Required Clauses Found: ${complianceSummary.compliant_count}/${complianceSummary.total_checks}`, 10, false);
        yPos += 3;
        
        if (!complianceSummary.is_compliant) {
            if (complianceSummary.critical_missing?.length > 0) {
                addText('CRITICAL MISSING CLAUSES:', 10, true, [220, 38, 38]);
                complianceSummary.critical_missing.forEach(r => {
                    addText(`  - ${r.domain}: ${r.description}`, 9, false, [127, 29, 29]);
                });
                yPos += 3;
            }
            if (complianceSummary.high_missing?.length > 0) {
                addText('HIGH PRIORITY MISSING:', 10, true, [234, 88, 12]);
                complianceSummary.high_missing.forEach(r => {
                    addText(`  - ${r.domain}: ${r.description}`, 9, false, [154, 52, 18]);
                });
                yPos += 3;
            }
            if (complianceSummary.medium_missing?.length > 0) {
                addText('MEDIUM PRIORITY MISSING:', 10, true, [202, 138, 4]);
                complianceSummary.medium_missing.forEach(r => {
                    addText(`  - ${r.domain}: ${r.description}`, 9, false, [133, 77, 14]);
                });
            }
        } else {
            addText('All required clauses have been verified as present in the document.', 10, false, [22, 163, 74]);
        }
    }
    
    // Red Flags Section
    addSection('RED FLAG ANALYSIS');
    
    if (redFlags && redFlags.length > 0) {
        const criticalFlags = redFlags.filter(f => f.severity === 'CRITICAL');
        const highFlags = redFlags.filter(f => f.severity === 'HIGH');
        const mediumFlags = redFlags.filter(f => f.severity === 'MEDIUM');
        const lowFlags = redFlags.filter(f => f.severity === 'LOW');
        
        addText(`Total Red Flags Detected: ${redFlags.length}`, 11, true, [220, 38, 38]);
        addText(`  Critical: ${criticalFlags.length}  |  High: ${highFlags.length}  |  Medium: ${mediumFlags.length}  |  Low: ${lowFlags.length}`, 9);
        yPos += 5;
        
        redFlags.forEach((flag, idx) => {
            const severityColors = {
                'CRITICAL': [220, 38, 38],
                'HIGH': [234, 88, 12],
                'MEDIUM': [202, 138, 4],
                'LOW': [101, 163, 13]
            };
            const color = severityColors[flag.severity] || [0, 0, 0];
            
            addText(`Red Flag #${idx + 1}: [${flag.severity}] ${flag.rule_id}`, 10, true, color);
            addText(`Domain: ${flag.domain}`, 9);
            addText(`Issue: ${flag.reason}`, 9);
            
            if (flag.clause_source?.filename) {
                addText(`Found in: ${flag.clause_source.filename}`, 9, false, [59, 130, 246]);
                if (flag.clause_source.excerpt) {
                    addText(`Excerpt: "${flag.clause_source.excerpt.substring(0, 150)}..."`, 8, false, [100, 100, 100]);
                }
            }
            yPos += 3;
        });
    } else {
        addText('No red flags detected in the analyzed document sections.', 10, false, [22, 163, 74]);
    }
    
    // AI Analysis Section
    addSection('AI ANALYSIS & RECOMMENDATIONS');
    addText(content, 10);
    
    // Sources Section
    if (sources && sources.length > 0) {
        addSection('DOCUMENT SOURCES REFERENCED');
        sources.forEach((src, idx) => {
            addText(`[${idx + 1}] ${src.filename}`, 10, true, [59, 130, 246]);
            addText(`    Section: ${src.section || 'Chunk ' + (src.chunk_idx + 1)} | Score: ${src.score.toFixed(4)}`, 9, false, [100, 100, 100]);
        });
    }
    
    // Disclaimer
    addSection('DISCLAIMER');
    doc.setFontSize(8);
    doc.setTextColor(100, 100, 100);
    const disclaimer = 'This report is generated by an AI-powered compliance analysis system for informational purposes only. It does not constitute legal advice. Manual review by a qualified legal professional is strongly recommended. The system analyzes only the sections retrieved; some clauses may be missed. For official compliance verification, please consult with a registered legal professional or contact MahaRERA directly.';
    const disclaimerLines = doc.splitTextToSize(disclaimer, maxWidth);
    disclaimerLines.forEach(line => {
        if (yPos > pageHeight - 20) {
            doc.addPage();
            yPos = 20;
        }
        doc.text(line, margin, yPos);
        yPos += 4;
    });
    
    // Footer on each page
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(150, 150, 150);
        doc.text(`Page ${i} of ${pageCount}`, pageWidth / 2, pageHeight - 10, { align: 'center' });
        doc.text('CloverAI - MahaRERA Compliance System', margin, pageHeight - 10);
    }
    
    // Save the PDF
    doc.save(`Compliance_Report_${now.toISOString().split('T')[0]}.pdf`);
}

function showTypingIndicator() {
    const botIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>`;
    const indicator = document.createElement('div');
    indicator.className = 'message assistant typing-message';
    indicator.innerHTML = `
        <div class="message-avatar">${botIcon}</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    elements.chatMessages.appendChild(indicator);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.querySelector('.typing-message');
    if (indicator) indicator.remove();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

function applySettings() {
    elements.languageSelect.value = state.settings.language;
    elements.topKInput.value = state.settings.topK;
    elements.showSourcesCheck.checked = state.settings.showSources;
}

function saveSettings() {
    localStorage.setItem('ragSettings', JSON.stringify(state.settings));
}

// ==================== BATCH PROCESSING FUNCTIONS ====================

function openBatchModal() {
    if (state.selectedUserDocIds.size === 0) {
        alert('Please select at least one user document to process.');
        return;
    }
    
    // Populate batch document list with selected documents
    const selectedDocs = state.documents.filter(d => state.selectedUserDocIds.has(d.filename));
    
    if (elements.batchDocList) {
        elements.batchDocList.innerHTML = selectedDocs.map(doc => `
            <div class="batch-doc-item">
                <input type="checkbox" id="batch-${doc.filename}" value="${doc.filename}" checked>
                <label for="batch-${doc.filename}">${doc.filename}</label>
                <span class="doc-type">USER</span>
            </div>
        `).join('');
    }
    
    // Reset progress
    if (elements.batchProgress) {
        elements.batchProgress.style.display = 'none';
        elements.batchProgressFill.style.width = '0%';
    }
    
    // Show modal
    if (elements.batchModal) {
        elements.batchModal.classList.add('active');
    }
}

function closeBatchModal() {
    if (elements.batchModal) {
        elements.batchModal.classList.remove('active');
    }
}

async function startBatchProcessing() {
    // Get selected documents from modal
    const checkboxes = elements.batchDocList.querySelectorAll('input[type="checkbox"]:checked');
    const documentIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (documentIds.length === 0) {
        alert('Please select at least one document to process.');
        return;
    }
    
    // Get options
    const options = {
        redFlags: document.getElementById('batchRedFlags')?.checked ?? true,
        compliance: document.getElementById('batchCompliance')?.checked ?? true,
        generatePdf: document.getElementById('batchGeneratePdf')?.checked ?? true
    };
    
    // Get selected MahaRERA docs
    const mahareraIds = Array.from(state.selectedMahareraIds);
    
    // Show progress
    elements.batchProgress.style.display = 'block';
    elements.startBatchBtn.disabled = true;
    elements.batchProgressText.textContent = 'Starting batch processing...';
    elements.batchProgressFill.style.width = '10%';
    
    try {
        const response = await fetch(`${API_BASE_URL}/batch-process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_ids: documentIds,
                maharera_ids: mahareraIds,
                options: options
            })
        });
        
        elements.batchProgressFill.style.width = '70%';
        elements.batchProgressText.textContent = 'Processing documents...';
        
        if (response.ok) {
            const data = await response.json();
            
            elements.batchProgressFill.style.width = '100%';
            elements.batchProgressText.textContent = 'Complete!';
            
            setTimeout(() => {
                closeBatchModal();
                displayBatchResults(data, options.generatePdf);
            }, 500);
            
        } else {
            const errorData = await response.json();
            elements.batchProgressText.textContent = `Error: ${errorData.error}`;
            elements.batchProgressFill.style.background = '#ef4444';
        }
    } catch (error) {
        elements.batchProgressText.textContent = 'Failed to connect to server';
        elements.batchProgressFill.style.background = '#ef4444';
        console.error('Batch processing error:', error);
    } finally {
        elements.startBatchBtn.disabled = false;
    }
}

function displayBatchResults(data, generatePdf = true) {
    const { summary, results } = data;
    
    // Remove welcome message
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();
    
    // Create batch results HTML
    let resultsHTML = `
        <div class="batch-results-container">
            <div class="batch-results-header">Batch Compliance Report - ${summary.total_documents} Documents Analyzed</div>
            
            <div class="batch-summary-grid">
                <div class="batch-summary-card">
                    <div class="count">${summary.processed}</div>
                    <div class="label">Processed</div>
                </div>
                <div class="batch-summary-card ${summary.documents_with_issues > 0 ? 'warning' : 'success'}">
                    <div class="count">${summary.documents_with_issues}</div>
                    <div class="label">With Issues</div>
                </div>
                <div class="batch-summary-card ${summary.total_critical > 0 ? 'critical' : ''}">
                    <div class="count">${summary.total_red_flags}</div>
                    <div class="label">Red Flags</div>
                </div>
                <div class="batch-summary-card ${summary.total_missing_clauses > 0 ? 'warning' : 'success'}">
                    <div class="count">${summary.total_missing_clauses}</div>
                    <div class="label">Missing Clauses</div>
                </div>
            </div>
            
            <div class="batch-doc-results">
                ${results.map(result => {
                    const hasIssues = result.red_flags?.length > 0 || 
                        (result.compliance_summary && !result.compliance_summary.is_compliant);
                    const isCritical = result.red_flags?.some(f => f.severity === 'CRITICAL');
                    const className = isCritical ? 'critical' : (hasIssues ? 'has-issues' : '');
                    
                    return `
                        <div class="batch-doc-result ${className}">
                            <div class="doc-name">${result.filename}</div>
                            <div class="doc-stats">
                                ${result.status === 'error' ? 
                                    `<span style="color: #dc2626;">Error: ${result.error}</span>` :
                                    `Red Flags: ${result.red_flags?.length || 0} | 
                                     Clauses Found: ${result.compliance_summary?.compliant_count || 0}/${result.compliance_summary?.total_checks || 0}`
                                }
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
    
    // Add message to chat
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    const botIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>`;
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    const downloadIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`;
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${botIcon}</div>
        <div class="message-content">
            ${resultsHTML}
            <div class="message-bubble">
                Batch compliance analysis complete. ${summary.documents_with_issues > 0 ? 
                    `${summary.documents_with_issues} document(s) have compliance issues that need attention.` :
                    'All documents passed the compliance check!'
                }
                <div class="message-actions">
                    <button class="download-btn" title="Download Batch Report" id="batchDownloadBtn">
                        ${downloadIcon}
                    </button>
                </div>
            </div>
            <div class="message-time">${time}</div>
        </div>
    `;
    
    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    
    // Add download handler
    const downloadBtn = messageDiv.querySelector('#batchDownloadBtn');
    if (downloadBtn && generatePdf) {
        downloadBtn.addEventListener('click', () => {
            generateBatchPdfReport(summary, results);
        });
    }
}

function generateBatchPdfReport(summary, results) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    let yPos = 20;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    const maxWidth = pageWidth - (margin * 2);
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
    const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    
    function checkPageBreak(needed = 20) {
        if (yPos + needed > pageHeight - 30) {
            doc.addPage();
            yPos = 20;
        }
    }
    
    // Title
    doc.setFillColor(139, 92, 246);
    doc.rect(0, 0, pageWidth, 40, 'F');
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('BATCH COMPLIANCE REPORT', pageWidth / 2, 18, { align: 'center' });
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`${summary.total_documents} Documents Analyzed`, pageWidth / 2, 28, { align: 'center' });
    doc.text(`Generated: ${dateStr} at ${timeStr}`, pageWidth / 2, 35, { align: 'center' });
    yPos = 55;
    
    // Executive Summary
    doc.setFillColor(245, 243, 255);
    doc.rect(margin, yPos - 5, maxWidth, 35, 'F');
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(91, 33, 182);
    doc.text('EXECUTIVE SUMMARY', margin + 5, yPos + 5);
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(0, 0, 0);
    yPos += 15;
    doc.text(`Documents Processed: ${summary.processed}/${summary.total_documents}`, margin + 5, yPos);
    yPos += 6;
    
    const issueColor = summary.documents_with_issues > 0 ? [220, 38, 38] : [22, 163, 74];
    doc.setTextColor(issueColor[0], issueColor[1], issueColor[2]);
    doc.text(`Documents with Issues: ${summary.documents_with_issues}`, margin + 5, yPos);
    yPos += 6;
    
    doc.setTextColor(summary.total_critical > 0 ? 220 : 0, summary.total_critical > 0 ? 38 : 0, summary.total_critical > 0 ? 38 : 0);
    doc.text(`Total Red Flags: ${summary.total_red_flags} (${summary.total_critical} Critical)`, margin + 5, yPos);
    yPos += 6;
    
    doc.setTextColor(0, 0, 0);
    doc.text(`Missing Required Clauses: ${summary.total_missing_clauses}`, margin + 5, yPos);
    yPos += 20;
    
    // Individual Document Results
    doc.setFillColor(139, 92, 246);
    doc.rect(margin, yPos - 5, maxWidth, 10, 'F');
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('DOCUMENT-WISE ANALYSIS', margin + 3, yPos + 2);
    yPos += 15;
    
    results.forEach((result, idx) => {
        checkPageBreak(50);
        
        const hasIssues = result.red_flags?.length > 0 || 
            (result.compliance_summary && !result.compliance_summary.is_compliant);
        const borderColor = hasIssues ? [245, 158, 11] : [34, 197, 94];
        
        doc.setDrawColor(borderColor[0], borderColor[1], borderColor[2]);
        doc.setLineWidth(0.5);
        doc.line(margin, yPos, margin, yPos + 30);
        
        doc.setFontSize(11);
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(55, 65, 81);
        doc.text(`${idx + 1}. ${result.filename}`, margin + 5, yPos + 5);
        
        if (result.status === 'error') {
            doc.setFontSize(9);
            doc.setTextColor(220, 38, 38);
            doc.text(`Error: ${result.error}`, margin + 5, yPos + 12);
        } else {
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            
            // Red flags
            const rfCount = result.red_flags?.length || 0;
            const rfColor = rfCount > 0 ? [220, 38, 38] : [22, 163, 74];
            doc.setTextColor(rfColor[0], rfColor[1], rfColor[2]);
            doc.text(`Red Flags: ${rfCount}`, margin + 5, yPos + 12);
            
            // Compliance
            const compliant = result.compliance_summary?.compliant_count || 0;
            const total = result.compliance_summary?.total_checks || 0;
            const compColor = compliant < total ? [245, 158, 11] : [22, 163, 74];
            doc.setTextColor(compColor[0], compColor[1], compColor[2]);
            doc.text(`Required Clauses: ${compliant}/${total}`, margin + 50, yPos + 12);
            
            // List red flags if any
            if (result.red_flags?.length > 0) {
                doc.setTextColor(100, 100, 100);
                let rfY = yPos + 18;
                result.red_flags.slice(0, 3).forEach(rf => {
                    doc.text(`  - [${rf.severity}] ${rf.rule_id}: ${rf.reason.substring(0, 60)}...`, margin + 5, rfY);
                    rfY += 5;
                });
                if (result.red_flags.length > 3) {
                    doc.text(`  ... and ${result.red_flags.length - 3} more`, margin + 5, rfY);
                }
            }
        }
        
        yPos += 40;
    });
    
    // Disclaimer
    checkPageBreak(40);
    yPos += 10;
    doc.setFillColor(249, 250, 251);
    doc.rect(margin, yPos - 5, maxWidth, 25, 'F');
    doc.setFontSize(8);
    doc.setTextColor(107, 114, 128);
    const disclaimer = 'This batch report is generated by an AI-powered compliance system for informational purposes only. Manual review by a qualified legal professional is recommended.';
    const lines = doc.splitTextToSize(disclaimer, maxWidth - 10);
    lines.forEach((line, i) => {
        doc.text(line, margin + 5, yPos + (i * 4));
    });
    
    // Footer on each page
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(150, 150, 150);
        doc.text(`Page ${i} of ${pageCount}`, pageWidth / 2, pageHeight - 10, { align: 'center' });
        doc.text('CloverAI - Batch Compliance Report', margin, pageHeight - 10);
    }
    
    doc.save(`Batch_Compliance_Report_${now.toISOString().split('T')[0]}.pdf`);
}

// ========== API Usage Functions ==========

async function fetchApiUsage() {
    try {
        const response = await fetch(`${API_BASE_URL}/usage`);
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.usage) {
                updateUsageDisplay(data.usage);
            }
        }
    } catch (error) {
        console.error('Failed to fetch API usage:', error);
    }
}

function updateUsageDisplay(usage) {
    // Update header panel
    if (elements.apiCallCount) {
        elements.apiCallCount.textContent = formatNumber(usage.total_requests || 0);
    }
    if (elements.apiTokenCount) {
        const totalTokens = (usage.estimated_input_tokens || 0) + (usage.estimated_output_tokens || 0);
        elements.apiTokenCount.textContent = formatNumber(totalTokens);
    }
    
    // Update modal if open
    const modalTotalRequests = document.getElementById('modalTotalRequests');
    const modalSuccessRequests = document.getElementById('modalSuccessRequests');
    const modalFailedRequests = document.getElementById('modalFailedRequests');
    const modalInputTokens = document.getElementById('modalInputTokens');
    const modalOutputTokens = document.getElementById('modalOutputTokens');
    const modalModelName = document.getElementById('modalModelName');
    const modalSessionStart = document.getElementById('modalSessionStart');
    
    if (modalTotalRequests) modalTotalRequests.textContent = formatNumber(usage.total_requests || 0);
    if (modalSuccessRequests) modalSuccessRequests.textContent = formatNumber(usage.successful_requests || 0);
    if (modalFailedRequests) modalFailedRequests.textContent = formatNumber(usage.failed_requests || 0);
    if (modalInputTokens) modalInputTokens.textContent = formatNumber(usage.estimated_input_tokens || 0);
    if (modalOutputTokens) modalOutputTokens.textContent = formatNumber(usage.estimated_output_tokens || 0);
    if (modalModelName) modalModelName.textContent = usage.model || 'N/A';
    if (modalSessionStart && usage.session_start) {
        const startDate = new Date(usage.session_start);
        modalSessionStart.textContent = startDate.toLocaleString('en-IN');
    }
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function openUsageModal() {
    fetchApiUsage(); // Refresh before showing
    if (elements.apiUsageModal) {
        elements.apiUsageModal.style.display = 'flex';
    }
}

function closeUsageModal() {
    if (elements.apiUsageModal) {
        elements.apiUsageModal.style.display = 'none';
    }
}

async function resetApiUsage() {
    try {
        const response = await fetch(`${API_BASE_URL}/usage/reset`, {
            method: 'POST'
        });
        if (response.ok) {
            fetchApiUsage(); // Refresh display
            // Show brief confirmation
            if (elements.resetUsageBtn) {
                const originalText = elements.resetUsageBtn.textContent;
                elements.resetUsageBtn.textContent = 'Done!';
                setTimeout(() => {
                    elements.resetUsageBtn.textContent = originalText;
                }, 2000);
            }
        }
    } catch (error) {
        console.error('Failed to reset API usage:', error);
    }
}

// Auto-check server status every 30 seconds
setInterval(checkServerStatus, 30000);

// Expose functions to global scope for inline HTML handlers
window.toggleMahareraSelection = toggleMahareraSelection;
window.toggleUserDocSelection = toggleUserDocSelection;
window.deleteDocument = deleteDocument;
