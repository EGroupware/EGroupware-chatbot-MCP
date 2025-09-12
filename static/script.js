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
    const aiModelSelect = document.getElementById('ai-model');
    const egwUrlInput = document.getElementById('egw-url');
    const aiKeyInput = document.getElementById('ai-key');
    const baseUrlGroup = document.querySelector('.base-url-group');
    const baseUrlInput = document.getElementById('base-url');
    const baseUrlHint = document.getElementById('base-url-hint');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const submitButton = loginForm.querySelector('button[type="submit"]');
    const errorMessage = document.getElementById('error-message');
    const apiKeyHint = document.getElementById('api-key-hint');

    // Provider configuration
    const providerConfig = {
        'openai': {
            needsBaseUrl: false,
            keyHint: 'Enter your OpenAI API key (starts with sk-)',
            validateKey: (key) => key.startsWith('sk-'),
            defaultBaseUrl: null
        },
        'ionos': {
            needsBaseUrl: true,
            keyHint: 'Enter your IONOS API key',
            validateKey: (key) => key.length > 0,
            defaultBaseUrl: 'https://openai.inference.de-txl.ionos.com/v1',
            baseUrlHint: 'IONOS API endpoint'
        },
        'github': {
            needsBaseUrl: true,
            keyHint: 'Enter your GitHub Personal Access Token',
            validateKey: (key) => key.startsWith('ghp_') || key.startsWith('github_pat_'),
            defaultBaseUrl: 'https://models.github.ai/inference',
            baseUrlHint: 'GitHub AI models endpoint'
        },
        'openrouter': {
            needsBaseUrl: true,
            keyHint: 'Enter your OpenRouter API key',
            validateKey: (key) => key.length > 0,
            defaultBaseUrl: 'https://openrouter.ai/api/v1',
            baseUrlHint: 'OpenRouter API endpoint'
        },
        'anthropic': {
            needsBaseUrl: false,
            keyHint: 'Enter your Anthropic API key',
            validateKey: (key) => key.startsWith('sk-ant-'),
            defaultBaseUrl: null
        },
        'azure': {
            needsBaseUrl: true,
            keyHint: 'Enter your Azure OpenAI API key',
            validateKey: (key) => key.length > 0,
            defaultBaseUrl: 'https://your-resource-name.openai.azure.com',
            baseUrlHint: 'Azure OpenAI endpoint'
        }
    };

    // Validation state
    let validations = {
        egwUrl: false,
        aiKey: false,
        baseUrl: true,  // Default to true, will be set to false if required
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
        baseUrl: createValidationIndicator(baseUrlInput),
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

    // Handle AI model selection
    aiModelSelect.addEventListener('change', () => {
        const selectedProvider = aiModelSelect.value;
        const config = providerConfig[selectedProvider];

        // Update API key hint
        apiKeyHint.textContent = config.keyHint;

        // Show/hide base URL field
        if (config.needsBaseUrl) {
            baseUrlGroup.style.display = 'block';
            baseUrlInput.value = config.defaultBaseUrl || '';
            baseUrlHint.textContent = config.baseUrlHint || 'Required for this provider';
            validations.baseUrl = !!baseUrlInput.value.trim();
        } else {
            baseUrlGroup.style.display = 'none';
            baseUrlInput.value = '';
            validations.baseUrl = true;
        }

        // Clear and revalidate the AI key input when switching models
        aiKeyInput.value = '';
        validations.aiKey = false;
        updateIndicator(indicators.aiKey, false);
        updateIndicator(indicators.baseUrl, validations.baseUrl);
        updateSubmitButton();
    });

    // Validate AI Key based on selected model
    aiKeyInput.addEventListener('input', () => {
        const key = aiKeyInput.value.trim();
        const selectedProvider = aiModelSelect.value;
        const indicator = indicators.aiKey;
        const config = providerConfig[selectedProvider];

        if (!key) {
            validations.aiKey = false;
            updateIndicator(indicator, false, 'API key is required');
        } else {
            validations.aiKey = config.validateKey(key);
            updateIndicator(
                indicator,
                validations.aiKey,
                validations.aiKey ? `Valid ${selectedProvider} key format` : `Invalid ${selectedProvider} key format`
            );
        }
        updateSubmitButton();
    });

    // Validate base URL if visible
    baseUrlInput.addEventListener('input', () => {
        const url = baseUrlInput.value.trim();
        const selectedProvider = aiModelSelect.value;
        const indicator = indicators.baseUrl;

        if (providerConfig[selectedProvider].needsBaseUrl) {
            validations.baseUrl = url.length > 0;
            updateIndicator(
                indicator,
                validations.baseUrl,
                validations.baseUrl ? 'Base URL provided' : 'Base URL is required'
            );
        } else {
            validations.baseUrl = true;
        }
        updateSubmitButton();
    });

    // Validate username and password
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
            const selectedProvider = aiModelSelect.value;
            const response = await fetch('/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    egw_url: egwUrlInput.value.trim(),
                    ai_key: aiKeyInput.value.trim(),
                    provider_type: selectedProvider,
                    base_url: providerConfig[selectedProvider].needsBaseUrl ? baseUrlInput.value.trim() : undefined,
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

    // Initially set up for default provider (OpenAI)
    aiModelSelect.dispatchEvent(new Event('change'));

    // Initially disable submit button
    submitButton.disabled = true;
}

function setupChatPage() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatBox = document.getElementById('chat-box');
    const logoutBtn = document.getElementById('logout-btn');
    let eventSource = null;
    let quickReplyContainer = null;
    let mediaRecorder = null;
    let audioChunks = [];
    const voiceBtn = document.getElementById('voice-btn');
    let recording = false;
    // Disable voice if provider not OpenAI (decode JWT payload)
    try {
        const rawToken = localStorage.getItem('accessToken');
        if (rawToken) {
            const parts = rawToken.split('.');
            if (parts.length === 3) {
                const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
                if (payload.provider_type && payload.provider_type !== 'openai' && voiceBtn) {
                    voiceBtn.disabled = true;
                    voiceBtn.title = 'Voice input available only with OpenAI provider';
                }
            }
        }
    } catch (_) { /* ignore decode issues */ }

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

    if (voiceBtn && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        voiceBtn.addEventListener('click', toggleRecording);
    }

    async function toggleRecording() {
        if (!recording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = [];
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
                mediaRecorder.onstop = handleRecordingStop;
                mediaRecorder.start();
                recording = true;
                voiceBtn.classList.add('recording');
            } catch (err) {
                alert('Microphone access denied or unsupported.');
            }
        } else {
            mediaRecorder.stop();
            recording = false;
            voiceBtn.classList.remove('recording');
        }
    }

    async function handleRecordingStop() {
        if (!audioChunks.length) return;
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        const token = localStorage.getItem('accessToken');
        formData.append('token', token || '');
        formData.append('audio', blob, 'voice.webm');
        try {
            voiceBtn.disabled = true;
            const resp = await fetch('/transcribe', { method: 'POST', body: formData });
            if (!resp.ok) throw new Error('Transcription failed');
            const data = await resp.json();
            if (data.text) {
                if (messageInput.value) messageInput.value += (messageInput.value.endsWith(' ') ? '' : ' ') + data.text;
                else messageInput.value = data.text;
                messageInput.dispatchEvent(new Event('input'));
            }
        } catch (e) {
            console.error(e);
        } finally {
            voiceBtn.disabled = false;
        }
    }

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        addUserMessageToBox(message);
        messageInput.value = '';
        messageInput.style.height = 'auto'; // Reset textarea height
        messageInput.focus();

    clearQuickReplies();
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
    // Insert quick replies container after response finishes
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
             fetchSuggestions();
        });
    }

    function ensureQuickReplyContainer() {
        if (!quickReplyContainer) {
            quickReplyContainer = document.createElement('div');
            quickReplyContainer.className = 'quick-replies';
            chatBox.appendChild(quickReplyContainer);
        }
        return quickReplyContainer;
    }

    function clearQuickReplies() {
        if (quickReplyContainer) {
            quickReplyContainer.remove();
            quickReplyContainer = null;
        }
    }

    async function fetchSuggestions() {
        const token = localStorage.getItem('accessToken');
        if (!token) return;
        try {
            const resp = await fetch(`/suggestions?token=${encodeURIComponent(token)}&count=4`);
            if (!resp.ok) return;
            const data = await resp.json();
            renderQuickReplies(data.suggestions || []);
        } catch (_) { /* silent */ }
    }

    function renderQuickReplies(suggestions) {
        if (!suggestions.length) return;
        const container = ensureQuickReplyContainer();
        container.innerHTML = '';
        suggestions.forEach(text => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'quick-reply-btn';
            btn.textContent = text;
            btn.addEventListener('click', () => {
                messageInput.value = text;
                chatForm.requestSubmit();
            });
            container.appendChild(btn);
        });
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Fetch initial suggestions on load (for greeting state)
    fetchSuggestions();
}