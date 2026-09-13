/**
 * SupportIQ - Enterprise Agentic AI IT Support Controller
 * Vanilla ES6+ Frontend Client
 */

(function () {
  'use strict';

  // State Management
  const state = {
    currentTab: 'chat',
    adminApiKey: localStorage.getItem('supportiq_admin_key') || 'supportiq-admin-2026',
    theme: localStorage.getItem('supportiq_theme') || 'dark',
    chatHistory: [],
    lastResponse: null,
    isProcessing: false,
    allDocuments: [],
  };

  // DOM Elements
  const elements = {
    // Theme
    html: document.documentElement,
    themeToggleBtn: document.getElementById('theme-toggle-btn'),

    // Sidebar & Navigation
    sidebar: document.getElementById('sidebar'),
    sidebarToggleBtn: document.getElementById('sidebar-toggle-btn'),
    navBtns: document.querySelectorAll('.nav-item'),
    tabViews: document.querySelectorAll('.tab-view'),
    breadcrumbTitle: document.getElementById('breadcrumb-title'),
    lastRouteLabel: document.getElementById('last-route-label'),
    liveRouterPill: document.getElementById('live-router-pill'),
    kbCountBadge: document.getElementById('kb-count-badge'),
    globalStatusDot: document.getElementById('global-status-dot'),
    globalStatusText: document.getElementById('global-status-text'),
    pingLatency: document.getElementById('ping-latency'),

    // Chat
    chatMessages: document.getElementById('chat-messages'),
    welcomeHero: document.getElementById('welcome-hero'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    attachBtn: document.getElementById('attach-btn'),
    reasoningIndicator: document.getElementById('reasoning-indicator'),
    reasoningStepTitle: document.getElementById('reasoning-step-title'),
    reasoningSub: document.getElementById('reasoning-sub'),
    newChatBtn: document.getElementById('new-chat-btn'),
    exportChatBtn: document.getElementById('export-chat-btn'),
    starterCards: document.querySelectorAll('.starter-card'),

    // Knowledge Base
    kbDropzone: document.getElementById('kb-dropzone'),
    fileUploadInput: document.getElementById('file-upload-input'),
    uploadProgressBox: document.getElementById('upload-progress-box'),
    uploadFileName: document.getElementById('upload-file-name'),
    uploadPct: document.getElementById('upload-pct'),
    uploadProgressBar: document.getElementById('upload-progress-bar'),
    uploadStatusLog: document.getElementById('upload-status-log'),
    reindexAllBtn: document.getElementById('reindex-all-btn'),
    documentsGrid: document.getElementById('documents-grid'),
    docSearchInput: document.getElementById('doc-search-input'),
    docsTotalPill: document.getElementById('docs-total-pill'),

    // Diagnostics
    refreshDiagBtn: document.getElementById('refresh-diag-btn'),
    diagModel: document.getElementById('diag-model'),
    diagEmbed: document.getElementById('diag-embed'),
    diagIndex: document.getElementById('diag-index'),
    diagNamespace: document.getElementById('diag-namespace'),
    diagTopk: document.getElementById('diag-topk'),
    diagRetries: document.getElementById('diag-retries'),
    diagEnv: document.getElementById('diag-env'),
    adminApiKeyInput: document.getElementById('admin-api-key-input'),
    toggleKeyVisibility: document.getElementById('toggle-key-visibility'),
    saveAdminKeyBtn: document.getElementById('save-admin-key-btn'),
    auditTableBody: document.getElementById('audit-table-body'),
    auditDbPill: document.getElementById('audit-db-pill'),
    refreshAuditBtn: document.getElementById('refresh-audit-btn'),

    // Citation Modal
    citationModalOverlay: document.getElementById('citation-modal-overlay'),
    citationModalBody: document.getElementById('citation-modal-body'),
    closeCitationModal: document.getElementById('close-citation-modal'),
  };

  /* ==========================================================================
     Initialization
     ========================================================================== */
  function init() {
    applyTheme(state.theme);
    bindEvents();
    checkHealthAndStats();
    loadKBDocuments();

    // Auto-ping every 30s
    setInterval(checkHealthAndStats, 30000);
  }

  /* ==========================================================================
     Theme & UI Toggles
     ========================================================================== */
  function applyTheme(theme) {
    state.theme = theme;
    elements.html.setAttribute('data-theme', theme);
    localStorage.setItem('supportiq_theme', theme);
  }

  function toggleTheme() {
    const newTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme);
  }

  function switchTab(tabId) {
    state.currentTab = tabId;

    // Update Nav Buttons
    elements.navBtns.forEach((btn) => {
      if (btn.getAttribute('data-tab') === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update Tab Views
    elements.tabViews.forEach((view) => {
      if (view.id === `view-${tabId}`) {
        view.style.display = 'flex';
        view.classList.add('active');
      } else {
        view.style.display = 'none';
        view.classList.remove('active');
      }
    });

    // Update Breadcrumb
    const titles = {
      chat: 'AI Support Console',
      kb: 'Knowledge Base & Ingestion',
      workflow: 'Agent Flow Visualizer',
      diagnostics: 'System Health & Infrastructure',
    };
    elements.breadcrumbTitle.textContent = titles[tabId] || 'Workspace';

    // If navigating to diagnostics, refresh audit logs
    if (tabId === 'diagnostics') {
      loadAuditLogs();
    }

    // On mobile, close sidebar after clicking
    if (window.innerWidth < 680) {
      elements.sidebar.classList.remove('open');
    }
  }

  /* ==========================================================================
     Backend Health & Diagnostics
     ========================================================================== */
  async function checkHealthAndStats() {
    const startTime = performance.now();
    try {
      const res = await fetch('/api/health');
      const latency = Math.round(performance.now() - startTime);
      elements.pingLatency.textContent = `${latency}ms`;

      if (res.ok) {
        elements.globalStatusDot.className = 'status-dot online';
        elements.globalStatusText.textContent = 'Backend Connected';
      } else {
        throw new Error('Service unhealthy');
      }

      // Load Stats
      const statsRes = await fetch('/api/stats');
      if (statsRes.ok) {
        const stats = await statsRes.json();
        if (elements.diagModel) elements.diagModel.textContent = stats.groq_model || 'openai/gpt-oss-120b';
        if (elements.diagEmbed) elements.diagEmbed.textContent = stats.embedding_model || 'gemini-embedding-2-preview';
        if (elements.diagIndex) elements.diagIndex.textContent = stats.pinecone_index || 'supportiq';
        if (elements.diagNamespace) elements.diagNamespace.textContent = stats.pinecone_namespace || 'it-support-kb';
        if (elements.diagTopk) elements.diagTopk.textContent = `${stats.top_k || 4} Chunks`;
        if (elements.diagRetries) elements.diagRetries.textContent = `${stats.max_retries || 1} Loop`;
        if (elements.diagEnv) elements.diagEnv.textContent = stats.app_env || 'development';
      }

      // Refresh Audit Logs alongside health check
      loadAuditLogs();
    } catch (err) {
      elements.globalStatusDot.className = 'status-dot offline';
      elements.globalStatusText.textContent = 'Backend Disconnected';
      elements.pingLatency.textContent = '--';
    }
  }

  async function loadAuditLogs() {
    if (!elements.auditTableBody) return;
    try {
      const res = await fetch('/api/audit/logs?limit=50');
      if (!res.ok) throw new Error('Failed to fetch audit records');
      const data = await res.json();

      if (elements.auditDbPill && data.db_type) {
        elements.auditDbPill.textContent = `Database: ${data.db_type}`;
      }

      const logs = data.logs || [];
      if (logs.length === 0) {
        elements.auditTableBody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
              No audit logs recorded yet. Submit an incident query in the Chat Console to generate records.
            </td>
          </tr>
        `;
        return;
      }

      elements.auditTableBody.innerHTML = '';
      logs.forEach((log) => {
        const tr = document.createElement('tr');

        // Format timestamp
        let formattedTime = log.timestamp;
        try {
          const d = new Date(log.timestamp);
          if (!isNaN(d.getTime())) {
            formattedTime = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          }
        } catch (_) {}

        // Source badge class
        let srcClass = 'direct';
        let srcLabel = log.source_used || 'direct';
        if (srcLabel === 'private_kb') {
          srcClass = 'kb';
          srcLabel = 'KB Runbook';
        } else if (srcLabel === 'web') {
          srcClass = 'web';
          srcLabel = 'Web Search';
        } else if (srcLabel === 'direct') {
          srcClass = 'direct';
          srcLabel = 'Direct LLM';
        } else if (srcLabel === 'error') {
          srcClass = 'error';
          srcLabel = 'Error';
        }

        tr.innerHTML = `
          <td class="audit-id">#${log.id}</td>
          <td class="audit-time">${escapeHtml(formattedTime)}</td>
          <td><span class="audit-source-pill ${srcClass}">${escapeHtml(srcLabel)}</span></td>
          <td class="audit-latency">${log.latency_ms || 0}ms</td>
          <td>
            <div class="audit-query-preview">${escapeHtml(log.question)}</div>
            <div class="audit-answer-preview">${escapeHtml(log.answer)}</div>
          </td>
        `;
        elements.auditTableBody.appendChild(tr);
      });
    } catch (err) {
      elements.auditTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--accent-rose); padding: 18px;">
            Error loading audit logs: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }


  /* ==========================================================================
     Chat Console Logic
     ========================================================================== */
  async function sendChatMessage(promptText = null) {
    const query = (promptText || elements.chatInput.value).trim();
    if (!query || state.isProcessing) return;

    // Reset input
    elements.chatInput.value = '';
    elements.chatInput.style.height = 'auto';
    elements.sendBtn.disabled = true;
    state.isProcessing = true;

    // Hide welcome hero on first message
    if (elements.welcomeHero) {
      elements.welcomeHero.style.display = 'none';
    }

    // Append User Message Bubble
    appendUserMessage(query);

    // Show reasoning animation
    showReasoningFlow();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query }),
      });

      hideReasoningFlow();

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Server Error' }));
        throw new Error(errData.detail || 'Failed to generate response');
      }

      const data = await res.json();
      state.lastResponse = data;

      // Update Live Route Pill in header
      updateRouterStatusPill(data.source_used);

      // Highlight active path in Workflow Visualizer
      highlightWorkflowPath(data.source_used, data.rewritten_query !== query);

      // Append Assistant Message Bubble
      appendAssistantMessage(data, query);

      // Store in history
      state.chatHistory.push({ role: 'user', text: query });
      state.chatHistory.push({ role: 'assistant', data });
    } catch (error) {
      hideReasoningFlow();
      appendErrorMessage(error.message);
    } finally {
      state.isProcessing = false;
      elements.sendBtn.disabled = false;
      elements.chatInput.focus();
    }
  }

  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `
      <div class="message-bubble">
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
      <div class="avatar user-avatar">IT</div>
    `;
    elements.chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendAssistantMessage(data, originalQuery) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';

    // Source Tag
    let sourceTagHtml = '';
    let sourceLabel = '';
    const src = (data.source_used || '').toLowerCase();

    if (src.includes('kb') || src.includes('private')) {
      sourceTagHtml = `<span class="source-tag kb">🟢 Private KB Grounded</span>`;
      sourceLabel = 'Private KB Grounded';
    } else if (src.includes('web')) {
      sourceTagHtml = `<span class="source-tag web">🟠 Web Search Fallback</span>`;
      sourceLabel = 'Web Search Fallback';
    } else if (src.includes('direct')) {
      sourceTagHtml = `<span class="source-tag direct">🔵 Direct Response</span>`;
      sourceLabel = 'Direct Conversational';
    } else {
      sourceTagHtml = `<span class="source-tag insufficient">⚠️ Insufficient Evidence</span>`;
      sourceLabel = 'Insufficient Evidence';
    }

    // Rewritten Query Tag
    let rewriteHtml = '';
    if (data.rewritten_query && data.rewritten_query !== originalQuery) {
      rewriteHtml = `<span class="rewritten-tag" title="Query refined by agent for optimal search">Refined: "${escapeHtml(data.rewritten_query)}"</span>`;
    }

    // Parse Markdown safely
    const formattedAnswer = renderMarkdown(data.answer);

    // Citations Footer
    let citationsFooterHtml = '';
    const citations = data.citations || [];
    if (citations.length > 0) {
      citationsFooterHtml = `
        <div class="citations-footer">
          <button class="citation-chip-btn" data-citations='${escapeHtml(JSON.stringify(citations))}'>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            <span>${citations.length} Verified ${citations.length === 1 ? 'Source' : 'Sources'}</span>
          </button>
          <div class="message-actions">
            <button class="msg-action-btn copy-ans-btn" title="Copy answer">📋 Copy</button>
            <button class="msg-action-btn" title="Mark Helpful">👍</button>
          </div>
        </div>
      `;
    } else {
      citationsFooterHtml = `
        <div class="citations-footer">
          <span></span>
          <div class="message-actions">
            <button class="msg-action-btn copy-ans-btn" title="Copy answer">📋 Copy</button>
          </div>
        </div>
      `;
    }

    row.innerHTML = `
      <div class="avatar bot-avatar">AI</div>
      <div class="message-bubble">
        <div class="message-meta-header">
          ${sourceTagHtml}
          ${rewriteHtml}
        </div>
        <div class="message-text">${formattedAnswer}</div>
        ${citationsFooterHtml}
      </div>
    `;

    // Attach copy button handler
    const copyBtn = row.querySelector('.copy-ans-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(data.answer);
        copyBtn.textContent = '✓ Copied';
        setTimeout(() => (copyBtn.textContent = '📋 Copy'), 2000);
      });
    }

    // Attach citation view handler
    const citationBtn = row.querySelector('.citation-chip-btn');
    if (citationBtn) {
      citationBtn.addEventListener('click', () => {
        openCitationsModal(citations, sourceLabel);
      });
    }

    // Code block copy buttons
    row.querySelectorAll('.copy-code-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const codeText = btn.parentElement.nextElementSibling.innerText;
        navigator.clipboard.writeText(codeText);
        btn.textContent = 'Copied!';
        setTimeout(() => (btn.textContent = 'Copy'), 2000);
      });
    });

    elements.chatMessages.appendChild(row);
    scrollToBottom();
  }

  function appendErrorMessage(errorMsg) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `
      <div class="avatar bot-avatar" style="background: var(--accent-rose)">!</div>
      <div class="message-bubble" style="border-color: rgba(244, 63, 94, 0.4);">
        <div class="message-meta-header">
          <span class="source-tag insufficient">⚠️ Execution Exception</span>
        </div>
        <div class="message-text">
          <p><strong>SupportIQ encountered an error executing the workflow:</strong></p>
          <code>${escapeHtml(errorMsg)}</code>
          <p style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted);">Please check backend terminal logs or ensure Pinecone and Groq API keys are accessible.</p>
        </div>
      </div>
    `;
    elements.chatMessages.appendChild(row);
    scrollToBottom();
  }

  function showReasoningFlow() {
    elements.reasoningIndicator.style.display = 'flex';
    elements.reasoningStepTitle.textContent = 'Evaluating Intent Router...';
    elements.reasoningSub.textContent = 'Determining if query requires private runbooks or direct answer';

    setTimeout(() => {
      if (state.isProcessing) {
        elements.reasoningStepTitle.textContent = 'Querying Pinecone Vector Index...';
        elements.reasoningSub.textContent = 'Retrieving highest cosine similarity chunks (top_k=4)';
      }
    }, 1500);

    setTimeout(() => {
      if (state.isProcessing) {
        elements.reasoningStepTitle.textContent = 'Grading Evidence Sufficiency...';
        elements.reasoningSub.textContent = 'Assessing private KB relevance; checking if Tavily fallback is needed';
      }
    }, 3500);

    scrollToBottom();
  }

  function hideReasoningFlow() {
    elements.reasoningIndicator.style.display = 'none';
  }

  function updateRouterStatusPill(sourceUsed) {
    const pill = elements.liveRouterPill;
    const label = elements.lastRouteLabel;
    pill.classList.remove('kb', 'web', 'direct', 'insufficient');

    if (sourceUsed === 'private_kb') {
      label.textContent = 'KB Runbook Grounded';
      pill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    } else if (sourceUsed === 'web') {
      label.textContent = 'Web Search Fallback';
      pill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
    } else if (sourceUsed === 'direct') {
      label.textContent = 'Direct LLM Synthesis';
      pill.style.borderColor = 'rgba(99, 102, 241, 0.4)';
    } else {
      label.textContent = 'Insufficient Evidence';
      pill.style.borderColor = 'rgba(244, 63, 94, 0.4)';
    }
  }

  function scrollToBottom() {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  }

  /* ==========================================================================
     Knowledge Base Management
     ========================================================================== */
  async function loadKBDocuments() {
    try {
      const res = await fetch('/api/kb/documents');
      if (!res.ok) return;
      const data = await res.json();
      state.allDocuments = data.documents || [];

      // Update badge counts
      elements.kbCountBadge.textContent = state.allDocuments.length;
      elements.docsTotalPill.textContent = `${state.allDocuments.length} Documents`;

      renderDocumentsGrid(state.allDocuments);
    } catch (err) {
      console.warn('Could not load KB documents:', err);
    }
  }

  function renderDocumentsGrid(docs) {
    elements.documentsGrid.innerHTML = '';

    if (docs.length === 0) {
      elements.documentsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
          No documents found in knowledge base. Upload a runbook above to begin.
        </div>
      `;
      return;
    }

    docs.forEach((doc) => {
      const card = document.createElement('div');
      card.className = 'doc-card';
      const isPdf = doc.name.toLowerCase().endsWith('.pdf');
      const badgeClass = isPdf ? 'pdf' : 'txt';

      card.innerHTML = `
        <div class="doc-card-top">
          <span class="doc-type-badge ${badgeClass}">${doc.type || 'PDF'}</span>
          <div class="doc-name">${escapeHtml(doc.name)}</div>
        </div>
        <div class="doc-meta-row">
          <span>${doc.size_kb ? doc.size_kb + ' KB' : 'Standard'}</span>
          <span class="doc-status-chip">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>Indexed</span>
          </span>
        </div>
      `;
      elements.documentsGrid.appendChild(card);
    });
  }

  async function handleFileUpload(file) {
    if (!file) return;

    elements.uploadProgressBox.style.display = 'block';
    elements.uploadFileName.textContent = file.name;
    elements.uploadPct.textContent = '20%';
    elements.uploadProgressBar.style.width = '20%';
    elements.uploadStatusLog.textContent = 'Transmitting document to server...';

    const formData = new FormData();
    formData.append('file', file);

    try {
      elements.uploadPct.textContent = '50%';
      elements.uploadProgressBar.style.width = '50%';
      elements.uploadStatusLog.textContent = 'Splitting into semantic chunks and generating embeddings...';

      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'api_key': state.adminApiKey,
        },
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Upload error' }));
        throw new Error(errorData.detail || 'Ingestion failed');
      }

      const result = await res.json();
      elements.uploadPct.textContent = '100%';
      elements.uploadProgressBar.style.width = '100%';
      elements.uploadStatusLog.textContent = `✓ Ingestion Complete! ${result.message}`;

      // Refresh KB Documents list
      setTimeout(() => {
        loadKBDocuments();
      }, 1000);
    } catch (err) {
      elements.uploadProgressBar.style.background = 'var(--accent-rose)';
      elements.uploadStatusLog.textContent = `Error: ${err.message}`;
    }
  }

  async function reindexAllGuides() {
    elements.reindexAllBtn.disabled = true;
    elements.reindexAllBtn.innerHTML = `<span>Re-indexing in progress...</span>`;

    try {
      const res = await fetch('/api/kb/reindex-all', {
        method: 'POST',
        headers: {
          'api_key': state.adminApiKey,
        },
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Re-index error' }));
        throw new Error(errorData.detail || 'Reindexing failed');
      }

      const result = await res.json();
      alert(`Knowledge Base Re-indexed:\n${result.message}`);
      loadKBDocuments();
    } catch (err) {
      alert(`Re-index failed: ${err.message}\nMake sure your Admin API Key in System Health matches settings.`);
    } finally {
      elements.reindexAllBtn.disabled = false;
      elements.reindexAllBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
        </svg>
        <span>Re-index All Runbooks</span>
      `;
    }
  }

  /* ==========================================================================
     Agent Flow Visualizer Path Highlighter
     ========================================================================== */
  function highlightWorkflowPath(sourceUsed, wasRewritten) {
    // Clear previous highlights
    document.querySelectorAll('.flow-node').forEach((node) => {
      node.classList.remove('active-path', 'highlight-kb', 'highlight-web');
    });

    const nodeStart = document.getElementById('node-start');
    const nodeRoute = document.getElementById('node-route');
    const nodeDirect = document.getElementById('node-direct');
    const nodeRetrieveKb = document.getElementById('node-retrieve-kb');
    const nodeGradeKb = document.getElementById('node-grade-kb');
    const nodeGenKb = document.getElementById('node-gen-kb');
    const nodeSearchWeb = document.getElementById('node-search-web');
    const nodeGradeWeb = document.getElementById('node-grade-web');
    const nodeGenWeb = document.getElementById('node-gen-web');
    const nodeRewrite = document.getElementById('node-rewrite');
    const nodeEnd = document.getElementById('node-end');

    if (nodeStart) nodeStart.classList.add('active-path');
    if (nodeRoute) nodeRoute.classList.add('active-path');

    if (sourceUsed === 'direct') {
      if (nodeDirect) nodeDirect.classList.add('active-path');
      if (nodeEnd) nodeEnd.classList.add('active-path');
    } else if (sourceUsed === 'private_kb') {
      if (nodeRetrieveKb) nodeRetrieveKb.classList.add('active-path', 'highlight-kb');
      if (nodeGradeKb) nodeGradeKb.classList.add('active-path', 'highlight-kb');
      if (nodeGenKb) nodeGenKb.classList.add('active-path', 'highlight-kb');
      if (nodeEnd) nodeEnd.classList.add('active-path');
    } else if (sourceUsed === 'web') {
      if (nodeRetrieveKb) nodeRetrieveKb.classList.add('active-path');
      if (nodeGradeKb) nodeGradeKb.classList.add('active-path');
      if (nodeSearchWeb) nodeSearchWeb.classList.add('active-path', 'highlight-web');
      if (nodeGradeWeb) nodeGradeWeb.classList.add('active-path', 'highlight-web');
      if (wasRewritten && nodeRewrite) nodeRewrite.classList.add('active-path');
      if (nodeGenWeb) nodeGenWeb.classList.add('active-path', 'highlight-web');
      if (nodeEnd) nodeEnd.classList.add('active-path');
    }
  }

  /* ==========================================================================
     Citation Inspection Modal
     ========================================================================== */
  function openCitationsModal(citations, sourceLabel) {
    elements.citationModalBody.innerHTML = '';

    if (!citations || citations.length === 0) {
      elements.citationModalBody.innerHTML = '<p>No specific citations recorded for this response.</p>';
    } else {
      citations.forEach((c, idx) => {
        const card = document.createElement('div');
        card.className = 'citation-card';
        const srcTitle = c.source || `Document Citation #${idx + 1}`;
        const pageBadge = c.page ? `<span class="citation-page-badge">Page ${c.page}</span>` : (c.url ? `<a href="${c.url}" target="_blank" class="citation-page-badge" style="color:#38bdf8;">Open Link ↗</a>` : '');

        card.innerHTML = `
          <div class="citation-source-title">
            <span>📄 ${escapeHtml(srcTitle)}</span>
            ${pageBadge}
          </div>
          <div class="citation-text">"${escapeHtml(c.snippet || c.content_snippet || 'Context excerpt')}"</div>
        `;
        elements.citationModalBody.appendChild(card);
      });
    }

    elements.citationModalOverlay.style.display = 'flex';
  }

  function closeCitationsModal() {
    elements.citationModalOverlay.style.display = 'none';
  }

  /* ==========================================================================
     Event Bindings
     ========================================================================== */
  function bindEvents() {
    // Theme toggle
    elements.themeToggleBtn.addEventListener('click', toggleTheme);

    // Sidebar navigation tabs
    elements.navBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        switchTab(tab);
      });
    });

    // Mobile sidebar toggle
    elements.sidebarToggleBtn.addEventListener('click', () => {
      elements.sidebar.classList.toggle('open');
    });

    // Chat Input Keyboard
    elements.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });

    // Auto-resize chat textarea
    elements.chatInput.addEventListener('input', () => {
      elements.chatInput.style.height = 'auto';
      elements.chatInput.style.height = `${Math.min(elements.chatInput.scrollHeight, 140)}px`;
    });

    // Send Button
    elements.sendBtn.addEventListener('click', () => sendChatMessage());

    // Starter Prompt Cards
    elements.starterCards.forEach((card) => {
      card.addEventListener('click', () => {
        const prompt = card.getAttribute('data-prompt');
        if (prompt) sendChatMessage(prompt);
      });
    });

    // New Session
    elements.newChatBtn.addEventListener('click', () => {
      elements.chatMessages.innerHTML = '';
      if (elements.welcomeHero) {
        elements.chatMessages.appendChild(elements.welcomeHero);
        elements.welcomeHero.style.display = 'block';
      }
      state.chatHistory = [];
      updateRouterStatusPill('');
      elements.lastRouteLabel.textContent = 'Engine Ready';
    });

    // Export Conversation
    elements.exportChatBtn.addEventListener('click', () => {
      if (state.chatHistory.length === 0) {
        alert('No conversation to export yet.');
        return;
      }
      let exportText = `# SupportIQ Incident Troubleshooting Transcript\nDate: ${new Date().toLocaleString()}\n\n`;
      state.chatHistory.forEach((msg) => {
        if (msg.role === 'user') {
          exportText += `### 👤 User Query:\n${msg.text}\n\n`;
        } else {
          exportText += `### 🤖 SupportIQ Resolution:\nSource Used: ${msg.data.source_used}\n\n${msg.data.answer}\n\n---\n\n`;
        }
      });
      const blob = new Blob([exportText], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SupportIQ-Transcript-${Date.now()}.md`;
      a.click();
      URL.revokeObjectURL(url);
    });

    // Attach File shortcut in chat
    elements.attachBtn.addEventListener('click', () => {
      switchTab('kb');
      elements.fileUploadInput.click();
    });

    // File Upload via Dropzone
    elements.fileUploadInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) handleFileUpload(file);
    });

    elements.kbDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      elements.kbDropzone.classList.add('dragover');
    });

    elements.kbDropzone.addEventListener('dragleave', () => {
      elements.kbDropzone.classList.remove('dragover');
    });

    elements.kbDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      elements.kbDropzone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) handleFileUpload(file);
    });

    // Re-index all button
    elements.reindexAllBtn.addEventListener('click', reindexAllGuides);

    // Document Search Filter
    elements.docSearchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = state.allDocuments.filter((d) => d.name.toLowerCase().includes(q));
      renderDocumentsGrid(filtered);
    });

    // Diagnostics & Audit Refresh
    elements.refreshDiagBtn.addEventListener('click', checkHealthAndStats);
    if (elements.refreshAuditBtn) {
      elements.refreshAuditBtn.addEventListener('click', loadAuditLogs);
    }


    // Admin Key Settings
    elements.adminApiKeyInput.value = state.adminApiKey;
    elements.toggleKeyVisibility.addEventListener('click', () => {
      if (elements.adminApiKeyInput.type === 'password') {
        elements.adminApiKeyInput.type = 'text';
        elements.toggleKeyVisibility.textContent = 'Hide';
      } else {
        elements.adminApiKeyInput.type = 'password';
        elements.toggleKeyVisibility.textContent = 'Show';
      }
    });

    elements.saveAdminKeyBtn.addEventListener('click', () => {
      state.adminApiKey = elements.adminApiKeyInput.value.trim();
      localStorage.setItem('supportiq_admin_key', state.adminApiKey);
      elements.saveAdminKeyBtn.textContent = '✓ Saved';
      setTimeout(() => (elements.saveAdminKeyBtn.textContent = 'Save Key'), 2000);
    });

    // Citation Modal Close
    elements.closeCitationModal.addEventListener('click', closeCitationsModal);
    elements.citationModalOverlay.addEventListener('click', (e) => {
      if (e.target === elements.citationModalOverlay) closeCitationsModal();
    });
  }

  /* ==========================================================================
     Markdown & Utility Parsers
     ========================================================================== */
  function renderMarkdown(md) {
    if (!md) return '';

    let html = escapeHtml(md);

    // Code blocks with syntax copy
    html = html.replace(/```([a-zA-Z0-9_\-\+]*)\n([\s\S]*?)```/g, function (match, lang, code) {
      return `
        <div class="code-block-wrapper">
          <div class="code-block-header">
            <span>${lang || 'code'}</span>
            <button class="copy-code-btn">Copy</button>
          </div>
          <pre><code>${code.trim()}</code></pre>
        </div>
      `;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Bullet Lists
    html = html.replace(/^\s*-\s+(.*)$/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Numbered lists
    html = html.replace(/^\s*(\d+)\.\s+(.*)$/gim, '<li>$2</li>');

    // Paragraph breaks
    html = html.replace(/\n\n+/g, '</p><p>');
    html = `<p>${html}</p>`;
    html = html.replace(/<p><\/p>/g, '');

    return html;
  }

  function escapeHtml(string) {
    if (!string) return '';
    const entityMap = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '/': '&#x2F;',
    };
    return String(string).replace(/[&<>"'/]/g, (s) => entityMap[s]);
  }

  // Bootstrap when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
