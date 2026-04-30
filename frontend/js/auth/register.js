async function login(email, password) {
    try {
        const response = await api.post('/accounts/login/', { email, password });
        if (response.tokens) {
            localStorage.setItem('access_token', response.tokens.access);
            localStorage.setItem('refresh_token', response.tokens.refresh);
            localStorage.setItem('user', JSON.stringify(response.user));
            window.location.href = 'chat.html';
        } else {
            alert(response.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('An error occurred during login');
    }
}

async function register(email, username, full_name, password) {
    try {
        const response = await api.post('/accounts/register/', { email, username, full_name, password });
        if (response.id) {
            alert('Registration successful! Please login.');
            window.location.href = 'login.html';
        } else {
            alert(JSON.stringify(response));
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('An error occurred during registration');
    }
}

function logout() {
    handleUnauthorized();
}
