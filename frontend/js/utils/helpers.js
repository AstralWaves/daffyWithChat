const API_BASE_URL = 'http://localhost:8000/api';

const api = {
    async get(endpoint) {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Authorization': token ? `Bearer ${token}` : '',
                'Content-Type': 'application/json'
            }
        });
        if (response.status === 401) {
            handleUnauthorized();
            return null;
        }
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.detail || 'API request failed');
        }
        return response.json();
    },

    async post(endpoint, data) {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Authorization': token ? `Bearer ${token}` : '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (response.status === 401) {
            handleUnauthorized();
            return null;
        }
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.detail || 'API request failed');
        }
        return response.json();
    }
};

function handleUnauthorized() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    if (!window.location.pathname.endsWith('login.html') && !window.location.pathname.endsWith('register.html')) {
        window.location.href = 'login.html';
    }
}

function showNotification(message, type = 'info') {
    // Simple alert for now, can be improved to a toast
    console.log(`[${type}] ${message}`);
}
