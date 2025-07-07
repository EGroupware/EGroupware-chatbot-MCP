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
    if (!loginForm) return;

    // Get form elements
    const egwUrlInput = document.getElementById('egw-url');
    const aiKeyInput = document.getElementById('ai-key');
    const ionosUrlGroup = document.querySelector('.ionos-url-group');
    const ionosBaseUrlInput = document.getElementById('ionos-base-url');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const submitButton = loginForm.querySelector('button[type="submit"]');
    const errorMessage = document.getElementById('error-message');

    // Validation state
    let validations = {
        egwUrl: false,
        aiKey: false,
        username: false,
        password: false
    };

    function updateSubmitButton() {
        const allValid = Object.values(validations).every(v => v);
        submitButton.disabled = !allValid;
    }

    // Add validation indicators next to each input
    function createValidationIndicator(input) {
        const indicator = document.createElement('span');
        indicator.className = 'validation-indicator';
        input.parentNode.appendChild(indicator);
        return indicator;
    }

    const indicators = {
        egwUrl: createValidationIndicator(egwUrlInput),
        aiKey: createValidationIndicator(aiKeyInput),
        username: createValidationIndicator(usernameInput),
        password: createValidationIndicator(passwordInput)
    };

    function updateIndicator(indicator, isValid, message = '') {
        indicator.className = 'validation-indicator ' + (isValid ? 'valid' : 'invalid');
        indicator.title = message;
    }

    // Validate EGroupware URL
    let egwUrlTimeout;
    egwUrlInput.addEventListener('input', () => {
        clearTimeout(egwUrlTimeout);
        const indicator = indicators.egwUrl;
        indicator.className = 'validation-indicator validating';

        egwUrlTimeout = setTimeout(async () => {
            const url = egwUrlInput.value.trim();
            if (!url) {
                validations.egwUrl = false;
                updateIndicator(indicator, false, 'EGroupware URL is required');
                updateSubmitButton();
                return;
            }

            try {
                const response = await fetch('/validate/egroupware-url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await response.json();
                validations.egwUrl = data.valid;
                updateIndicator(indicator, data.valid, data.valid ? 'Valid EGroupware URL' : data.detail);
            } catch (error) {
                validations.egwUrl = false;
                updateIndicator(indicator, false, 'Error validating URL');
            }
            updateSubmitButton();
        }, 500);
    });

    // Validate AI API Key
    let aiKeyTimeout;
    aiKeyInput.addEventListener('input', () => {
        clearTimeout(aiKeyTimeout);
        const indicator = indicators.aiKey;
        indicator.className = 'validation-indicator validating';

        // Show/hide IONOS URL field based on key format
        const isOpenAiKey = aiKeyInput.value.trim().startsWith('sk-');
        ionosUrlGroup.style.display = isOpenAiKey ? 'none' : 'block';

        aiKeyTimeout = setTimeout(async () => {
            const apiKey = aiKeyInput.value.trim();
            if (!apiKey) {
                validations.aiKey = false;
                updateIndicator(indicator, false, 'AI API key is required');
                updateSubmitButton();
                return;
            }

            try {
                const payload = {
                    api_key: apiKey,
                    ionos_base_url: isOpenAiKey ? undefined : ionosBaseUrlInput.value
                };

                const response = await fetch('/validate/ai-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                validations.aiKey = data.valid;
                updateIndicator(indicator, data.valid,
                    data.valid ? `Valid ${isOpenAiKey ? 'OpenAI' : 'IONOS'} API key` : data.detail);

                // If it's an invalid IONOS key that needs a base URL, show the field
                if (!data.valid && data.is_ionos) {
                    ionosUrlGroup.style.display = 'block';
                }
            } catch (error) {
                validations.aiKey = false;
                updateIndicator(indicator, false, 'Error validating API key');
            }
            updateSubmitButton();
        }, 500);
    });

    // Revalidate when IONOS base URL changes
    ionosBaseUrlInput.addEventListener('input', () => {
        if (!aiKeyInput.value.trim().startsWith('sk-')) {
            // Trigger AI key validation to check with new base URL
            aiKeyInput.dispatchEvent(new Event('input'));
        }
    });

    // Simple validation for username and password
    usernameInput.addEventListener('input', () => {
        const value = usernameInput.value.trim();
        validations.username = value.length > 0;
        updateIndicator(indicators.username, validations.username,
            validations.username ? 'Username provided' : 'Username is required');
        updateSubmitButton();
    });

    passwordInput.addEventListener('input', () => {
        const value = passwordInput.value.trim();
        validations.password = value.length > 0;
        updateIndicator(indicators.password, validations.password,
            validations.password ? 'Password provided' : 'Password is required');
        updateSubmitButton();
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!Object.values(validations).every(v => v)) {
            errorMessage.textContent = 'Please fix validation errors before submitting';
            return;
        }

        errorMessage.textContent = 'Logging in...';

        try {
            const isOpenAiKey = aiKeyInput.value.trim().startsWith('sk-');
            const response = await fetch('/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    egw_url: egwUrlInput.value.trim(),
                    ai_key: aiKeyInput.value.trim(),
                    ionos_base_url: isOpenAiKey ? undefined : ionosBaseUrlInput.value.trim(),
                    username: usernameInput.value.trim(),
                    password: passwordInput.value.trim()
                })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Login failed.');
            localStorage.setItem('accessToken', data.access_token);
            window.location.href = '/chat-ui';
        } catch (error) {
            errorMessage.textContent = error.message;
        }
    });

    // Initially disable submit button
    submitButton.disabled = true;
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