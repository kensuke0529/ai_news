// Global variables
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
const askAboutBtns = document.querySelectorAll('.ask-about-btn');
const suggestionBtns = document.querySelectorAll('.suggestion-btn');

// Search elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchResults = document.getElementById('searchResults');
const searchWeekFilter = document.getElementById('searchWeekFilter');
const searchLimit = document.getElementById('searchLimit');
const weekSelector = document.getElementById('weekSelector');
const refreshNewsBtn = document.getElementById('refreshNewsBtn');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize tab switching
    initializeTabs();
    
    // Initialize chat functionality
    initializeChat();
    
    // Initialize summary functionality
    initializeSummary();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize news functionality
    initializeNews();
    
    // Initialize ask about buttons
    initializeAskAboutButtons();
    
    // Generate session ID
    currentSessionId = generateSessionId();
}

// Tab switching functionality
function initializeTabs() {
    navTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });
}

function switchTab(tabName) {
    // Remove active class from all tabs and contents
    navTabs.forEach(tab => tab.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Add active class to selected tab and content
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');
}

// Chat functionality
function initializeChat() {
    // Send button click
    sendBtn.addEventListener('click', sendMessage);
    
    // Enter key press
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Suggestion buttons
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const message = this.getAttribute('data-message');
            chatInput.value = message;
            sendMessage();
        });
    });
}

function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isLoading) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    chatInput.value = '';
    
    // Show loading
    showLoading();
    
    // Send to API
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            session_id: currentSessionId
        })
    })
    .then(response => response.json())
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
    content.innerHTML = `<p>${message}</p>`;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Summary functionality
function initializeSummary() {
    generateSummaryBtn.addEventListener('click', generateSummary);
}

function generateSummary() {
    if (isLoading) return;
    
    showLoading();
    
    fetch('/api/summary')
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displaySummary(data.summary);
        } else {
            displaySummary('Sorry, I encountered an error generating the summary. Please try again.');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        displaySummary('Sorry, I encountered an error generating the summary. Please try again.');
    });
}

function displaySummary(summary) {
    summaryContent.innerHTML = `
        <div class="summary-text">
            ${summary.split('\n').map(paragraph => 
                paragraph.trim() ? `<p>${paragraph}</p>` : ''
            ).join('')}
        </div>
    `;
}

// Search functionality
function initializeSearch() {
    // Search button click
    searchBtn.addEventListener('click', performSearch);
    
    // Enter key press in search input
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
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            week_filter: weekFilter,
            limit: limit
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displaySearchResults(data);
        } else {
            displaySearchError(data.error || 'Search failed');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Search error:', error);
        displaySearchError('Search failed. Please try again.');
    });
}

function displaySearchResults(data) {
    const { results, query, total_results } = data;
    
    if (results.length === 0) {
        searchResults.innerHTML = `
            <div class="search-placeholder">
                <i class="fas fa-search"></i>
                <p>No articles found for "${query}"</p>
                <p>Try different keywords or check your spelling</p>
            </div>
        `;
        return;
    }
    
    const statsHtml = `
        <div class="search-stats">
            <div class="search-stats-info">
                Found <strong>${total_results}</strong> articles for 
                <span class="search-stats-query">"${query}"</span>
            </div>
        </div>
    `;
    
    const resultsHtml = results.map(result => `
        <div class="search-result">
            <div class="search-result-header">
                <h3 class="search-result-title">${result.title}</h3>
                <span class="search-result-confidence">${Math.round(result.confidence * 100)}% match</span>
            </div>
            <div class="search-result-summary">
                <p>${result.summary}</p>
            </div>
            <div class="search-result-actions">
                <a href="${result.link}" target="_blank" class="search-result-link">
                    <i class="fas fa-external-link-alt"></i>
                    Read Full Article
                </a>
                <button class="btn btn-secondary ask-about-search-btn" data-title="${result.title}">
                    <i class="fas fa-question-circle"></i>
                    Ask About This
                </button>
            </div>
        </div>
    `).join('');
    
    searchResults.innerHTML = statsHtml + resultsHtml;
    
    // Re-initialize ask about buttons for search results
    initializeSearchAskAboutButtons();
}

function displaySearchError(error) {
    searchResults.innerHTML = `
        <div class="search-placeholder">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Error: ${error}</p>
        </div>
    `;
}

function initializeSearchAskAboutButtons() {
    const searchAskAboutBtns = document.querySelectorAll('.ask-about-search-btn');
    searchAskAboutBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const title = this.getAttribute('data-title');
            const message = `Tell me more about this article: "${title}"`;
            
            // Switch to chat tab
            switchTab('chat');
            
            // Set the message and send it
            setTimeout(() => {
                chatInput.value = message;
                sendMessage();
            }, 300);
        });
    });
}

// News functionality
function initializeNews() {
    // Week selector change
    weekSelector.addEventListener('change', loadNewsForWeek);
    
    // Refresh button click
    refreshNewsBtn.addEventListener('click', loadNewsForWeek);
}

function loadNewsForWeek() {
    const selectedWeek = weekSelector.value;
    
    showLoading();
    
    const url = selectedWeek === 'all' ? '/api/news' : `/api/news?week=${selectedWeek}`;
    
    fetch(url)
    .then(response => response.json())
    .then(data => {
        hideLoading();
        displayNews(data);
    })
    .catch(error => {
        hideLoading();
        console.error('Error loading news:', error);
        alert('Failed to load news. Please try again.');
    });
}

function displayNews(newsData) {
    const newsGrid = document.getElementById('newsGrid');
    
    if (!newsData.articles || newsData.articles.length === 0) {
        newsGrid.innerHTML = `
            <div class="search-placeholder">
                <i class="fas fa-newspaper"></i>
                <p>No articles found for this week</p>
            </div>
        `;
        return;
    }
    
    const articlesHtml = newsData.articles.map(article => `
        <article class="news-card">
            <div class="news-card-header">
                <h3 class="news-title">${article.title}</h3>
                <span class="news-date">${article.date}</span>
            </div>
            <div class="news-summary">
                <p>${article.summary}</p>
            </div>
            <div class="news-actions">
                <a href="${article.link}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i>
                    Read Full Article
                </a>
                <button class="btn btn-secondary ask-about-btn" data-title="${article.title}">
                    <i class="fas fa-question-circle"></i>
                    Ask About This
                </button>
            </div>
        </article>
    `).join('');
    
    newsGrid.innerHTML = articlesHtml;
    
    // Re-initialize ask about buttons
    initializeAskAboutButtons();
}

// Ask about buttons functionality
function initializeAskAboutButtons() {
    askAboutBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const title = this.getAttribute('data-title');
            const message = `Tell me more about this article: "${title}"`;
            
            // Switch to chat tab
            switchTab('chat');
            
            // Set the message and send it
            setTimeout(() => {
                chatInput.value = message;
                sendMessage();
            }, 300);
        });
    });
}

// Loading functions
function showLoading() {
    isLoading = true;
    loadingOverlay.classList.add('show');
    sendBtn.disabled = true;
    generateSummaryBtn.disabled = true;
}

function hideLoading() {
    isLoading = false;
    loadingOverlay.classList.remove('show');
    sendBtn.disabled = false;
    generateSummaryBtn.disabled = false;
}

// Utility functions
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

// Auto-resize chat input
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
});

// Smooth scrolling for chat messages
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add some visual feedback for interactions
document.addEventListener('click', function(e) {
    if (e.target.matches('.btn, .suggestion-btn, .ask-about-btn')) {
        e.target.style.transform = 'scale(0.95)';
        setTimeout(() => {
            e.target.style.transform = '';
        }, 150);
    }
});

// Handle window resize
window.addEventListener('resize', function() {
    // Recalculate chat height if needed
    if (document.getElementById('chat').classList.contains('active')) {
        const chatContainer = document.querySelector('.chat-container');
        chatContainer.style.height = '600px';
    }
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + 1, 2, 3, 4 for tab switching
    if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '4') {
        e.preventDefault();
        const tabIndex = parseInt(e.key) - 1;
        const tabs = ['news', 'search', 'summary', 'chat'];
        if (tabs[tabIndex]) {
            switchTab(tabs[tabIndex]);
        }
    }
    
    // Escape to clear chat input
    if (e.key === 'Escape' && chatInput === document.activeElement) {
        chatInput.value = '';
        chatInput.blur();
    }
});

// Add some animations for better UX
function addFadeInAnimation(element) {
    element.style.opacity = '0';
    element.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
        element.style.transition = 'all 0.5s ease';
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
    }, 100);
}

// Initialize animations for news cards
document.addEventListener('DOMContentLoaded', function() {
    const newsCards = document.querySelectorAll('.news-card');
    newsCards.forEach((card, index) => {
        setTimeout(() => {
            addFadeInAnimation(card);
        }, index * 100);
    });
});


