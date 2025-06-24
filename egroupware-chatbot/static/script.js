document.addEventListener("DOMContentLoaded", () => {
    // Basic routing based on token existence
    if (window.location.pathname.includes('login') || window.location.pathname === '/') {
        if (localStorage.getItem('accessToken')) {
            window.location.href = '/chat-ui';
        } else {
            setupLoginPage();
        }
    } else if (window.location.pathname.includes('chat-ui')) {
        if (!localStorage.getItem('accessToken')) {
            window.location.href = '/';
        } else {
            setupChatPage();
        }
    }
});

function setupLoginPage() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = 'Logging in...';

        try {
            const response = await fetch('/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ username, password })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Login failed due to an unknown error.');
            }

            localStorage.setItem('accessToken', data.access_token);
            window.location.href = '/chat-ui';
        } catch (error) {
            errorMessage.textContent = error.message;
        }
    });
}

function setupChatPage() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatBox = document.getElementById('chat-box');
    const logoutBtn = document.getElementById('logout-btn');
    let eventSource = null;

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (eventSource) eventSource.close();
            localStorage.removeItem('accessToken');
            window.location.href = '/';
        });
    }

    if (!chatForm) return;

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        addMessageToBox(message, 'user-message');
        messageInput.value = '';
        messageInput.focus();

        getAIResponse(message);
    });

    function addMessageToBox(text, className) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', className);

        const p = document.createElement('p');
        p.textContent = text;
        messageElement.appendChild(p);

        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
        return messageElement;
    }

    async function getAIResponse(message) {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            alert('Your session has expired. Please log in again.');
            window.location.href = '/';
            return;
        }

        const botMessageElement = addMessageToBox('', 'bot-message');
        const pElement = botMessageElement.querySelector('p');

        // Use a cursor/blinking effect for the placeholder
        pElement.style.minHeight = '1.2em';
        pElement.innerHTML = 'Thinking <span class="blinking-cursor"></span>';

        const url = `/chat?message=${encodeURIComponent(message)}&token=${encodeURIComponent(token)}`;
        eventSource = new EventSource(url);
        let firstChunk = true;

        eventSource.onmessage = (event) => {
            if (firstChunk) {
                pElement.innerHTML = ''; // Clear "Thinking..."
                firstChunk = false;
            }
            const data = JSON.parse(event.data);

            if (data.type === 'token') {
                pElement.textContent += data.content;
            } else if (data.type === 'tool_call') {
                 pElement.innerHTML += `<br><i>🤖 Calling tool: ${data.tool_name}...</i>`;
            } else if (data.type === 'tool_result') {
                 pElement.innerHTML += `<br><i>✅ Tool finished. Generating response...</i>`;
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        };

        eventSource.onerror = (err) => {
            pElement.innerHTML = 'Error connecting to the server. Please check your connection and try again.';
            eventSource.close();
        };

        eventSource.addEventListener('end', () => {
             eventSource.close();
        });
    }
}