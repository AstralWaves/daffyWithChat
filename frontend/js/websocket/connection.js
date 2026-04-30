let chatSocket = null;

function connectWebSocket(conversationId) {
    if (chatSocket) {
        chatSocket.close();
    }

    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsScheme}://${window.location.host}/ws/chat/${conversationId}/`;
    
    const token = localStorage.getItem('access_token');
    const devWsUrl = `ws://localhost:8000/ws/chat/${conversationId}/?token=${token}`;

    chatSocket = new WebSocket(devWsUrl);

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        handleWebSocketMessage(data);
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
        // Optional: Implement reconnect logic
    };

    chatSocket.onerror = function(e) {
        console.error('WebSocket error:', e);
    };

    return chatSocket;
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'message':
            appendMessage(data);
            break;
        case 'typing':
            updateTypingIndicator(data);
            break;
        case 'status':
            updateUserStatus(data);
            break;
        case 'read':
            updateReadReceipt(data);
            break;
    }
}
