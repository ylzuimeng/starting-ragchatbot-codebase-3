// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let authToken = null;
let currentUser = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles;

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    // Add switching animation class
    const themeToggle = document.getElementById('themeToggle');
    themeToggle.classList.add('switching');

    // Set new theme
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Update icon after animation
    setTimeout(() => {
        updateThemeIcon(newTheme);
        themeToggle.classList.remove('switching');
    }, 250);
}

function updateThemeIcon(theme) {
    const themeToggle = document.getElementById('themeToggle');
    const icon = themeToggle.querySelector('i');

    if (theme === 'light') {
        icon.className = 'fas fa-sun';
    } else {
        icon.className = 'fas fa-moon';
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();

    // Setup theme toggle button
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);

        // Add keyboard support
        themeToggle.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleTheme();
            }
        });
    }

    // Check authentication first
    checkAuth();

    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');

    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Check authentication
function checkAuth() {
    authToken = localStorage.getItem('token');
    currentUser = JSON.parse(localStorage.getItem('user') || 'null');

    if (!authToken || !currentUser) {
        // Not logged in, redirect to login
        if (window.location.pathname !== '/login.html') {
            window.location.href = '/login.html';
        }
        return false;
    }

    // Logged in, setup UI
    const usernameEl = document.getElementById('username');
    if (usernameEl) {
        usernameEl.textContent = currentUser.username;
    }

    // Setup logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    return true;
}

// Handle logout
async function handleLogout() {
    // 显示确认对话框
    const confirmed = confirm('确定要退出登录吗？');

    if (!confirmed) {
        return; // 用户取消
    }

    try {
        await fetch(`${API_URL}/api/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
    } catch (error) {
        console.error('Logout error:', error);
    }

    localStorage.removeItem('token');
    localStorage.removeItem('user');
    authToken = null;
    currentUser = null;
    currentSessionId = null;

    window.location.href = '/login.html';
}

// Make authenticated API call
async function authenticatedFetch(url, options = {}) {
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${authToken}`
    };

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
        throw new Error('Session expired');
    }

    return response;
}

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });


    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            // ✅ 使用 currentTarget 而不是 target，确保获取 button 元素
            const question = e.currentTarget.getAttribute('data-question');
            console.log('[Suggested Question] Clicked:', question);
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    console.log('[sendMessage] Query:', query);

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    console.log('[sendMessage] About to call addMessage...');

    // Add user message
    addMessage(query, 'user');

    console.log('[sendMessage] User message added');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await authenticatedFetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`错误: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    // Check if marked library is loaded to avoid errors
    let displayContent;
    if (type === 'assistant') {
        try {
            displayContent = (typeof marked !== 'undefined') ? marked.parse(content) : escapeHtml(content);
        } catch (e) {
            console.error('Markdown parsing error:', e);
            displayContent = escapeHtml(content);
        }
    } else {
        displayContent = escapeHtml(content);
    }

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        // Render sources with optional links
        const sourcesHtml = sources.map(source => {
            // Handle new format (object with text and link)
            if (typeof source === 'object' && source.text) {
                if (source.link) {
                    // Render as clickable link
                    return `<a href="${escapeHtml(source.link)}"
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class="source-link"
                                  title="点击观看视频">
                        ${escapeHtml(source.text)}
                        <svg class="source-link-icon" viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
                            <path d="M14 3h7v7h-2V6.4L8.4 17 7 15.6 17 6.4V9h-2v7h7V3z"/>
                        </svg>
                    </a>`;
                } else {
                    // No link available, render as plain text
                    return `<span class="source-item">${escapeHtml(source.text)}</span>`;
                }
            }
            // Handle old format (string) for backward compatibility
            return `<span class="source-item">${escapeHtml(source)}</span>`;
        }).join('<span class="source-separator">, </span>');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">来源</summary>
                <div class="sources-content">${sourcesHtml}</div>
            </details>
        `;
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function createNewSession() {
    // Reset session ID to null (new session will be created on next query)
    currentSessionId = null;

    // Clear chat messages from UI
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Clear input field
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = '';
    }

    // Show welcome message
    addMessage('欢迎使用 RAG 课程助手！我可以帮您回答关于课程、课程内容和具体内容的问题。您想了解什么？', 'assistant', null, true);

    // Focus on input field for new conversation
    if (chatInput) {
        chatInput.focus();
    }

    // Log session start for debugging
    console.log('New session started');
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');

        // Show loading state
        if (totalCourses) totalCourses.innerHTML = '<span class="loading">加载中...</span>';
        if (courseTitles) courseTitles.innerHTML = '<span class="loading">加载中...</span>';

        const response = await authenticatedFetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');

        const data = await response.json();
        console.log('Course data received:', data);

        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }

        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">暂无课程</span>';
            }
        }

    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">加载课程失败</span>';
        }
    }
}
