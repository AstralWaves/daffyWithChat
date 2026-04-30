let currentConversation = null;
let currentUser = null;

// Initialize chat
document.addEventListener('DOMContentLoaded', async () => {
    currentUser = JSON.parse(localStorage.getItem('user'));
    
    if (!currentUser) {
        window.location.href = 'login.html';
        return;
    }
    
    displayUserInfo();
    await loadConversations();
    setupEventListeners();
});

function displayUserInfo() {
    document.getElementById('userName').textContent = currentUser.full_name;
    document.getElementById('userStatus').textContent = currentUser.is_online ? 'Online' : 'Offline';
    if (currentUser.avatar) {
        document.getElementById('userAvatar').src = currentUser.avatar;
    }
}

async function loadConversations() {
    try {
        const conversations = await api.get('/chat/conversations/');
        displayConversations(conversations);
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

function displayConversations(conversations) {
    const container = document.getElementById('conversationsList');
    container.innerHTML = '';
    
    conversations.forEach(conv => {
        const otherParticipant = conv.participants.find(p => p.id !== currentUser.id) || currentUser;
        const div = document.createElement('div');
        div.className = 'conversation-item';
        div.setAttribute('data-conversation-id', conv.id);
        div.innerHTML = `
            <img src="${otherParticipant.avatar || 'assets/default-avatar.png'}" class="avatar" alt="${otherParticipant.full_name}">
            <div class="conversation-info">
                <strong>${otherParticipant.full_name}</strong>
                <small>${conv.last_message || 'No messages yet'}</small>
            </div>
            <div class="conversation-time">${conv.last_message_time ? new Date(conv.last_message_time).toLocaleTimeString() : ''}</div>
        `;
        
        div.addEventListener('click', () => selectConversation(conv.id, otherParticipant));
        container.appendChild(div);
    });
}

async function selectConversation(conversationId, otherParticipant) {
    currentConversation = {
        id: conversationId,
        otherParticipant: otherParticipant
    };
    
    // Update chat header
    document.getElementById('chatUserName').textContent = otherParticipant.full_name;
    document.getElementById('chatUserStatus').textContent = otherParticipant.is_online ? 'Online' : 'Offline';
    document.getElementById('chatAvatar').src = otherParticipant.avatar || 'assets/default-avatar.png';
    
    // Connect WebSocket
    connectWebSocket(conversationId);
    
    // Load messages
    await loadMessages(conversationId);
}

async function loadMessages(conversationId) {
    try {
        const messages = await api.get(`/chat/messages/${conversationId}/`);
        displayMessages(messages);
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

function displayMessages(messages) {
    const container = document.getElementById('messagesList');
    container.innerHTML = '';
    
    messages.forEach(msg => {
        appendMessage(msg);
    });
    
    scrollToBottom();
}

function appendMessage(msg) {
    const container = document.getElementById('messagesList');
    const isOwnMessage = msg.sender_id === currentUser.id;
    const div = document.createElement('div');
    div.className = `message ${isOwnMessage ? 'own-message' : 'other-message'}`;
    div.innerHTML = `
        <div class="message-content">
            <p>${escapeHtml(msg.content || msg.message)}</p>
            <small>${new Date(msg.created_at || msg.timestamp).toLocaleTimeString()}</small>
            ${isOwnMessage ? `<span class="message-status">${msg.is_read ? '✓✓' : '✓'}</span>` : ''}
        </div>
    `;
    container.appendChild(div);
    scrollToBottom();
}

function setupEventListeners() {
    // Video Call
    document.getElementById('videoCallBtn').addEventListener('click', () => {
        if (!currentConversation) return;
        const callId = `call_${Date.now()}`;
        window.open(`video-call.html?id=${callId}&caller=true`, '_blank', 'width=1280,height=720');
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', () => {
        if (confirm('Are you sure you want to logout?')) {
            logout();
        }
    });

    // Send message
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    document.getElementById('messageInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // Search users
    const searchInput = document.getElementById('searchUsers');
    searchInput.addEventListener('input', debounce(async (e) => {
        const query = e.target.value.trim();
        if (query.length > 2) {
            const users = await api.get(`/accounts/search/?q=${query}`);
            displaySearchResults(users);
        } else if (query.length === 0) {
            loadConversations();
        }
    }, 500));
}

function displaySearchResults(users) {
    const container = document.getElementById('conversationsList');
    container.innerHTML = '<h3>Search Results</h3>';
    
    users.forEach(user => {
        const div = document.createElement('div');
        div.className = 'conversation-item';
        div.innerHTML = `
            <img src="${user.avatar || 'assets/default-avatar.png'}" class="avatar" alt="${user.full_name}">
            <div class="conversation-info">
                <strong>${user.full_name}</strong>
                <small>${user.email}</small>
            </div>
        `;
        
        div.addEventListener('click', () => startNewConversation(user));
        container.appendChild(div);
    });
}

async function startNewConversation(user) {
    try {
        const conversation = await api.post('/chat/conversations/', {
            participants: [user.id]
        });
        selectConversation(conversation.id, user);
        loadConversations();
    } catch (error) {
        console.error('Error starting conversation:', error);
    }
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    
    if (!content || !chatSocket) return;
    
    chatSocket.send(JSON.stringify({
        type: 'message',
        content: content
    }));
    
    input.value = '';
}

function updateTypingIndicator(data) {
    const indicator = document.getElementById('typingIndicator');
    if (data.is_typing && data.user_id !== currentUser.id) {
        indicator.textContent = `${data.user_name} is typing...`;
        indicator.style.display = 'block';
    } else {
        indicator.style.display = 'none';
    }
}

function updateUserStatus(data) {
    if (currentConversation && currentConversation.otherParticipant.id === data.user_id) {
        document.getElementById('chatUserStatus').textContent = data.status === 'online' ? 'Online' : 'Offline';
    }
}

function updateReadReceipt(data) {
    // Logic to update UI for read messages
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
