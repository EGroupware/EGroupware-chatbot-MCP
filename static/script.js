document.addEventListener("DOMContentLoaded", () => {
    // This script now only handles page routing and setup.
    // All theme logic has been removed.

    const path = window.location.pathname;
    const token = localStorage.getItem('accessToken');

    if (path.includes('chat-ui')) {
        if (!token) {
            window.location.href = '/'; // Not logged in, redirect to login
        } else {
            setupChatPage(); // Logged in, set up the chat page
        }
    } else { // This handles the root path '/' and any other path
        if (token) {
            window.location.href = '/chat-ui'; // Already logged in, redirect to chat
        } else {
            setupLoginPage(); // Not logged in, set up the login page
        }
    }
});

function setupLoginPage() {
    const loginForm = document.getElementById('login-form');
    const aiProvider = document.getElementById('ai-provider');
    const ionosBaseUrlField = document.getElementById('ionos-base-url');

    if (!loginForm) return;

    // Handle AI provider change
    aiProvider.addEventListener('change', (e) => {
        if (e.target.value === 'ionos') {
            ionosBaseUrlField.classList.remove('hidden');
            ionosBaseUrlField.required = true;
        } else {
            ionosBaseUrlField.classList.add('hidden');
            ionosBaseUrlField.required = false;
        }
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = {
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            egroupwareUrl: document.getElementById('egroupware-url').value,
            aiProvider: document.getElementById('ai-provider').value,
            aiApiKey: document.getElementById('ai-api-key').value,
            ionosBaseUrl: document.getElementById('ionos-base-url').value
        };
        const errorMessage = document.getElementById('error-message');
        errorMessage.textContent = 'Logging in...';

        try {
            // First set the environment configuration
            const configResponse = await fetch('/configure', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    egroupware_url: formData.egroupwareUrl,
                    ai_provider: formData.aiProvider,
                    ai_api_key: formData.aiApiKey,
                    ionos_base_url: formData.ionosBaseUrl
                })
            });

            if (!configResponse.ok) {
                throw new Error('Failed to set configuration');
            }

            // Then proceed with login
            const loginResponse = await fetch('/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    username: formData.username,
                    password: formData.password
                })
            });

            const data = await loginResponse.json();
            if (!loginResponse.ok) throw new Error(data.detail || 'Login failed.');

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

    if (!chatForm || !messageInput) return;

    // --- ADJUSTABLE TEXTAREA LOGIC ---
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto'; // Reset height to recalculate
        messageInput.style.height = `${messageInput.scrollHeight}px`;
    });

    messageInput.addEventListener('keydown', (e) => {
        // Submit on Enter, but allow new lines with Shift+Enter
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        addUserMessageToBox(message);
        messageInput.value = '';
        messageInput.style.height = 'auto'; // Reset textarea height
        messageInput.focus();

        getAIResponse(message);
    });

    // The rest of the functions are the same as before.
    function addUserMessageToBox(text) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'user-message');
        messageElement.textContent = text;
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function createBotMessageElements() {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'bot-message');
        const mainTextP = document.createElement('p');
        mainTextP.className = 'main-response-text';
        const statusDiv = document.createElement('div');
        statusDiv.className = 'status-updates';
        messageElement.appendChild(mainTextP);
        messageElement.appendChild(statusDiv);
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
        return { mainTextElement: mainTextP, statusElement: statusDiv };
    }

    async function getAIResponse(message) {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            alert('Your session has expired. Please log in again.');
            window.location.href = '/';
            return;
        }

        const { mainTextElement, statusElement } = createBotMessageElements();
        mainTextElement.innerHTML = '<span class="blinking-cursor">...</span>';

        const url = `/chat?message=${encodeURIComponent(message)}&token=${encodeURIComponent(token)}`;
        eventSource = new EventSource(url);
        let firstChunk = true;

        eventSource.onmessage = (event) => {
            if (firstChunk) {
                mainTextElement.innerHTML = '';
                firstChunk = false;
            }
            const data = JSON.parse(event.data);
            if (data.type === 'token') {
                mainTextElement.textContent += data.content;
            } else if (data.type === 'tool_call') {
                statusElement.innerHTML += `<i>🤖 Calling tool: ${data.tool_name}...</i><br>`;
            } else if (data.type === 'tool_result') {
                statusElement.innerHTML += `<i>✅ Tool finished. Generating response...</i><br>`;
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        };

        eventSource.onerror = () => {
            mainTextElement.textContent = 'Error connecting to the server. Please check your connection and try again.';
            eventSource.close();
        };

        eventSource.addEventListener('end', () => {
             eventSource.close();
        });
    }
}