// ----------------------
// Global variables
// ----------------------
let currentSessionId = null;
let isLoading = false;

// DOM elements
const navTabs = document.querySelectorAll('.nav-tab');
const tabContents = document.querySelectorAll('.tab-content');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const generateSummaryBtn = document.getElementById('generateSummaryBtn');
const summaryContent = document.getElementById('summaryContent');
const loadingOverlay = document.getElementById('loadingOverlay');
const suggestionBtns = document.querySelectorAll('.suggestion-btn');

// Search elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchResults = document.getElementById('searchResults');
const searchWeekFilter = document.getElementById('searchWeekFilter');
const searchLimit = document.getElementById('searchLimit');
const weekSelector = document.getElementById('weekSelector');
const refreshNewsBtn = document.getElementById('refreshNewsBtn');

// ----------------------
// Initialize app
// ----------------------
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    initializeTabs();
    initializeChat();
    initializeSummary();
    initializeSearch();
    initializeNews();
    currentSessionId = generateSessionId();
}

// ----------------------
// Tabs
// ----------------------
function initializeTabs() {
    navTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });
}

function switchTab(tabName) {
    navTabs.forEach(tab => tab.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');
}

// ----------------------
// Chat
// ----------------------
function initializeChat() {
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            chatInput.value = this.getAttribute('data-message');
            sendMessage();
        });
    });
}

function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isLoading) return;

    addMessageToChat(message, 'user');
    chatInput.value = '';
    showLoading();

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: currentSessionId })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            addMessageToChat(data.response, 'ai');
            currentSessionId = data.session_id;
        } else {
            addMessageToChat('Sorry, I encountered an error. Please try again.', 'ai');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        addMessageToChat('Sorry, I encountered an error. Please try again.', 'ai');
    });
}

function addMessageToChat(message, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

    const content = document.createElement('div');
    content.className = 'message-content';

    // Convert Markdown → HTML and sanitize
    content.innerHTML = message
    .replace(/^###\s+/gm, '')                 // Remove headings
    .replace(/\*\*(.*?)\*\*/g, '$1')         // Remove bold markers
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Convert links to just the text
    .replace(/^- /gm, '• ')                   // Convert markdown bullets to nicer bullets
    .replace(/\n/g, '<br>');                 // Keep line breaks

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ----------------------
// Summary
// ----------------------
function initializeSummary() {
    generateSummaryBtn.addEventListener('click', generateSummary);
}

function generateSummary() {
    if (isLoading) return;
    showLoading();

    fetch('/api/summary')
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) displaySummary(data.summary);
        else displaySummary('Sorry, I encountered an error generating the summary.');
    })
    .catch(err => {
        hideLoading();
        console.error(err);
        displaySummary('Sorry, I encountered an error generating the summary.');
    });
}

function displaySummary(summary) {
    summaryContent.innerHTML = `
        <div class="summary-text">
            ${summary.split('\n').map(p => p.trim() ? `<p>${p}</p>` : '').join('')}
        </div>
    `;
}

// ----------------------
// Search
// ----------------------
function initializeSearch() {
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            performSearch();
        }
    });
}

function performSearch() {
    const query = searchInput.value.trim();
    if (!query || isLoading) return;

    const weekFilter = searchWeekFilter.value;
    const limit = parseInt(searchLimit.value);

    showLoading();
    fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, week_filter: weekFilter, limit })
    })
    .then(res => res.json())
    .then(data => {
        hideLoading();
        if (data.success) displaySearchResults(data);
        else displaySearchError(data.error || 'Search failed');
    })
    .catch(err => {
        hideLoading();
        console.error(err);
        displaySearchError('Search failed. Please try again.');
    });
}

function displaySearchResults(data) {
    const { results, query, total_results } = data;

    if (!results.length) {
        searchResults.innerHTML = `
            <div class="search-placeholder">
                <i class="fas fa-search"></i>
                <p>No articles found for "${query}"</p>
            </div>
        `;
        return;
    }

    const statsHtml = `
        <div class="search-stats">
            Found <strong>${total_results}</strong> articles for "<span>${query}</span>"
        </div>
    `;

    const resultsHtml = results.map(result => `
        <div class="search-result">
            <h3>${result.title} (${Math.round(result.confidence*100)}% match)</h3>
            <p>${result.summary}</p>
            <a href="${result.link}" target="_blank">Read Full Article</a>
            <button class="btn ask-about-search-btn" data-title="${result.title}">Ask About This</button>
        </div>
    `).join('');

    searchResults.innerHTML = statsHtml + resultsHtml;
    initializeSearchAskAboutButtons();
}

function displaySearchError(error) {
    searchResults.innerHTML = `<p>Error: ${error}</p>`;
}

function initializeSearchAskAboutButtons() {
    const buttons = document.querySelectorAll('.ask-about-search-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            const message = `Tell me more about this article: "${btn.dataset.title}"`;
            switchTab('chat');
            setTimeout(() => { chatInput.value = message; sendMessage(); }, 300);
        });
    });
}

// ----------------------
// News
// ----------------------
function initializeNews() {
    weekSelector.addEventListener('change', loadNewsForWeek);
    refreshNewsBtn.addEventListener('click', loadNewsForWeek);
}

function loadNewsForWeek() {
    const selectedWeek = weekSelector.value;
    showLoading();
    const url = selectedWeek === 'all' ? '/api/news' : `/api/news?week=${selectedWeek}`;

    fetch(url)
    .then(res => res.json())
    .then(data => { hideLoading(); displayNews(data); })
    .catch(err => { hideLoading(); console.error(err); alert('Failed to load news'); });
}

function displayNews(newsData) {
    const newsGrid = document.getElementById('newsGrid');
    if (!newsData.articles || newsData.articles.length === 0) {
        newsGrid.innerHTML = `<p>No articles found</p>`;
        return;
    }

    newsGrid.innerHTML = newsData.articles.map(article => `
        <div class="news-card">
            <h3>${article.title}</h3>
            <p>${article.summary}</p>
            <a href="${article.link}" target="_blank">Read Full Article</a>
            <button class="btn ask-about-btn" data-title="${article.title}">Ask About This</button>
        </div>
    `).join('');

    initializeAskAboutButtons();
}

// ----------------------
// Ask About
// ----------------------
function initializeAskAboutButtons() {
    const buttons = document.querySelectorAll('.ask-about-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            const message = `Tell me more about this article: "${btn.dataset.title}"`;
            switchTab('chat');
            setTimeout(() => { chatInput.value = message; sendMessage(); }, 300);
        });
    });
}

// ----------------------
// Loading
// ----------------------
function showLoading() { isLoading = true; loadingOverlay.classList.add('show'); sendBtn.disabled = true; generateSummaryBtn.disabled = true; }
function hideLoading() { isLoading = false; loadingOverlay.classList.remove('show'); sendBtn.disabled = false; generateSummaryBtn.disabled = false; }

// ----------------------
// Utilities
// ----------------------
function generateSessionId() { return 'session_' + Math.random().toString(36).substr(2,9) + '_' + Date.now(); }

chatInput.addEventListener('input', function() { this.style.height = 'auto'; this.style.height = this.scrollHeight + 'px'; });

window.addEventListener('resize', function() {
    if (document.getElementById('chat').classList.contains('active')) {
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.style.height = '600px';
    }
});
