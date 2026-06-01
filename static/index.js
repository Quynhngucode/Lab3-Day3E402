/* ==========================================================================
   CineBot Chatbot & ReAct Agent Frontend Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

    // State Variables
    let currentProvider = 'mimo';   // 'mimo', 'google', or 'local'
    let currentMode = 'agent';      // 'agent' or 'chatbot'
    let isGenerating = false;

    // DOM Elements
    const btnMimo = document.getElementById('btnMimo');
    const btnGoogle = document.getElementById('btnGoogle');
    const btnLocal = document.getElementById('btnLocal');
    
    const mimoConfig = document.getElementById('mimoConfig');
    const googleConfig = document.getElementById('googleConfig');
    const localConfig = document.getElementById('localConfig');
    
    const mimoApiKeyInput = document.getElementById('mimoApiKeyInput');
    const apiKeyInput = document.getElementById('apiKeyInput');
    
    const toggleMimoApiKeyVisible = document.getElementById('toggleMimoApiKeyVisible');
    const mimoEyeIcon = document.getElementById('mimoEyeIcon');
    
    const toggleApiKeyVisible = document.getElementById('toggleApiKeyVisible');
    const eyeIcon = document.getElementById('eyeIcon');
    
    const btnAgent = document.getElementById('btnAgent');
    const btnChatbot = document.getElementById('btnChatbot');
    const modeHelpText = document.getElementById('modeHelpText');
    
    const presetBtns = document.querySelectorAll('.preset-btn');

    const telemetryLatency = document.getElementById('telemetryLatency');
    const telemetrySteps = document.getElementById('telemetrySteps');
    const telemetryTokens = document.getElementById('telemetryTokens');

    const currentModelDesc = document.getElementById('currentModelDesc');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const messagesContainer = document.getElementById('messagesContainer');
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const serverStatus = document.getElementById('serverStatus');

    // ─────────────────────────────────────────────────────────────────────────────
    // 1. PROVIDER & MODE TOGGLE LOGIC
    // ─────────────────────────────────────────────────────────────────────────────

    function switchProvider(provider) {
        if (isGenerating) return;
        currentProvider = provider;

        // Reset active states
        btnMimo.classList.remove('active');
        btnGoogle.classList.remove('active');
        btnLocal.classList.remove('active');
        
        mimoConfig.classList.remove('active');
        googleConfig.classList.remove('active');
        localConfig.classList.remove('active');

        if (provider === 'mimo') {
            btnMimo.classList.add('active');
            mimoConfig.classList.add('active');
            currentModelDesc.textContent = 'Sử dụng mô hình MiMo-v2.5-Pro Token Plan qua cổng Singapore';
        } else if (provider === 'google') {
            btnGoogle.classList.add('active');
            googleConfig.classList.add('active');
            currentModelDesc.textContent = 'Sử dụng Google gemini-3-flash-preview thông qua API';
        } else {
            btnLocal.classList.add('active');
            localConfig.classList.add('active');
            currentModelDesc.textContent = 'Sử dụng Phi-3-mini GGUF chạy cục bộ (Offline CPU)';
        }
    }

    function switchMode(mode) {
        if (isGenerating) return;
        currentMode = mode;

        if (mode === 'agent') {
            btnAgent.classList.add('active');
            btnChatbot.classList.remove('active');
            modeHelpText.innerHTML = '<strong>ReAct Agent:</strong> Có khả năng sử dụng các công cụ rạp phim để tra cứu và đặt vé chính xác.';
        } else {
            btnAgent.classList.remove('active');
            btnChatbot.classList.add('active');
            modeHelpText.innerHTML = '<strong>Chatbot Baseline:</strong> Chatbot thông thường không dùng công cụ (Dễ bịa thông tin đặt vé/giá tiền).';
        }
    }

    btnMimo.addEventListener('click', () => switchProvider('mimo'));
    btnGoogle.addEventListener('click', () => switchProvider('google'));
    btnLocal.addEventListener('click', () => switchProvider('local'));
    
    btnAgent.addEventListener('click', () => switchMode('agent'));
    btnChatbot.addEventListener('click', () => switchMode('chatbot'));

    // Set initial description correctly for mimo
    currentModelDesc.textContent = 'Sử dụng mô hình MiMo-v2.5-Pro Token Plan qua cổng Singapore';

    // Toggle API Key Visibility (MiMo)
    toggleMimoApiKeyVisible.addEventListener('click', (e) => {
        e.preventDefault();
        if (mimoApiKeyInput.type === 'password') {
            mimoApiKeyInput.type = 'text';
            mimoEyeIcon.textContent = 'visibility';
        } else {
            mimoApiKeyInput.type = 'password';
            mimoEyeIcon.textContent = 'visibility_off';
        }
    });

    // Toggle API Key Visibility (Gemini)
    toggleApiKeyVisible.addEventListener('click', (e) => {
        e.preventDefault();
        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            eyeIcon.textContent = 'visibility';
        } else {
            apiKeyInput.type = 'password';
            eyeIcon.textContent = 'visibility_off';
        }
    });

    // ─────────────────────────────────────────────────────────────────────────────
    // 2. TEXTAREA & INPUT AUTO-RESIZE & UTILS
    // ─────────────────────────────────────────────────────────────────────────────

    // Auto-resize textbox height as content grows
    userInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight - 4) + 'px';
    });

    // Prevent enter from creating newline, instead submit
    userInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });

    // Clear Chat Feed
    clearChatBtn.addEventListener('click', () => {
        if (isGenerating) return;

        // Remove all bubbles except system message
        const messages = messagesContainer.querySelectorAll('.message:not(.system-message)');
        messages.forEach(msg => msg.remove());

        // Reset telemetry metrics
        telemetryLatency.textContent = '-';
        telemetrySteps.textContent = '-';
        telemetryTokens.textContent = '-';
    });

    // Preset queries handling
    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (isGenerating) return;
            const query = btn.getAttribute('data-query');
            userInput.value = query;
            userInput.style.height = 'auto';
            userInput.style.height = (userInput.scrollHeight - 4) + 'px';
            chatForm.requestSubmit();
        });
    });

    // Check backend server connection on startup
    async function checkServerStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.status === 'ready') {
                serverStatus.className = 'server-status ready';
                serverStatus.innerHTML = '<span class="status-dot green"></span> Đang kết nối';
            }
        } catch (err) {
            serverStatus.className = 'server-status error';
            serverStatus.innerHTML = '<span class="status-dot red"></span> Mất kết nối';
        }
    }

    checkServerStatus();
    setInterval(checkServerStatus, 15000); // Check every 15 seconds

    // ─────────────────────────────────────────────────────────────────────────────
    // 3. CHAT MESSAGE RENDERING & SUBMIT
    // ─────────────────────────────────────────────────────────────────────────────

    function appendUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `
            <div class="bubble">
                <p>${escapeHtml(text)}</p>
            </div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    function createGeneratingBubble() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-message loading-bubble';
        
        const modeBadge = currentMode === 'agent' ? 'REACT AGENT' : 'CHATBOT BASELINE';
        const providerName = currentProvider === 'mimo' ? 'MiMo-v2.5-Pro' : (currentProvider === 'google' ? 'Gemini 3.5' : 'Local Phi-3');

        loadingDiv.innerHTML = `
            <div class="bubble generating-bubble">
                <span class="generating-badge" style="background: var(--gradient-primary); color: #fff; padding: 2px 8px; border-radius: 20px; font-size: 9px; font-weight: 700; margin-bottom: 6px; display: inline-block;">${modeBadge} // ${providerName}</span>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        messagesContainer.appendChild(loadingDiv);
        scrollToBottom();
        return loadingDiv;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const message = userInput.value.trim();
        if (!message || isGenerating) return;

        // Reset input state
        userInput.value = '';
        userInput.style.height = 'auto';

        isGenerating = true;
        setFormDisabled(true);

        // Add user query bubble
        appendUserMessage(message);

        // Add typing/generating status indicator
        const loadingBubble = createGeneratingBubble();

        try {
            let activeApiKey = '';
            if (currentProvider === 'mimo') {
                activeApiKey = mimoApiKeyInput.value.trim();
            } else if (currentProvider === 'google') {
                activeApiKey = apiKeyInput.value.trim();
            }

            const bodyPayload = {
                message: message,
                provider: currentProvider,
                apiKey: activeApiKey,
                mode: currentMode
            };

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(bodyPayload)
            });

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            const data = await response.json();

            // Remove loading bubble
            loadingBubble.remove();

            // Append agent response card
            appendBotResponse(data);

        } catch (error) {
            console.error(error);
            loadingBubble.remove();

            // Render error bubble
            appendErrorBubble(`Không thể kết nối máy chủ hoặc đã xảy ra lỗi: ${error.message}`);
        } finally {
            isGenerating = false;
            setFormDisabled(false);
            userInput.focus();
        }
    });

    function setFormDisabled(disabled) {
        userInput.disabled = disabled;
        sendBtn.disabled = disabled;
        presetBtns.forEach(btn => btn.disabled = disabled);
        if (disabled) {
            sendBtn.style.opacity = '0.5';
        } else {
            sendBtn.style.opacity = '1';
        }
    }

    function appendErrorBubble(errorText) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message bot-message';
        errorDiv.innerHTML = `
            <div class="bubble" style="border-color: var(--error); background: rgba(239, 68, 68, 0.05);">
                <p style="color: var(--error); font-weight: 500;">❌ ${escapeHtml(errorText)}</p>
            </div>
        `;
        messagesContainer.appendChild(errorDiv);
        scrollToBottom();
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // 4. STEP-BY-STEP REACT TRACE & TICKET RENDERING
    // ─────────────────────────────────────────────────────────────────────────────

    function appendBotResponse(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        // A. Primary Badges Header (UX clear indicators)
        const badgeContainer = document.createElement('div');
        badgeContainer.className = 'message-badge-container';
        
        const modeBadgeText = currentMode === 'agent' ? 'REACT AGENT' : 'CHATBOT BASELINE';
        const providerName = currentProvider === 'mimo' ? 'MiMo-v2.5-Pro' : (currentProvider === 'google' ? 'Gemini 3.5' : 'Local Phi-3');
        
        badgeContainer.innerHTML = `
            <span class="mode-badge ${currentMode}">${modeBadgeText}</span>
            <span class="model-badge">${providerName}</span>
        `;
        bubble.appendChild(badgeContainer);

        // B. Primary Answer text
        const answerText = document.createElement('p');
        answerText.innerHTML = formatMarkdown(data.final_answer);
        bubble.appendChild(answerText);

        // C. ReAct thought trace drawer (if steps are present)
        if (data.steps && data.steps.length > 0) {
            const traceContainer = createReActTraceDrawer(data.steps, data.metrics);
            bubble.appendChild(traceContainer);
        }

        messageDiv.appendChild(bubble);
        messagesContainer.appendChild(messageDiv);

        // C. Cinema Booking Ticket Card (if booking occurred successfully)
        checkAndRenderTicket(data.steps);

        // D. Update Telemetry metrics
        if (data.metrics) {
            telemetryLatency.textContent = data.metrics.latency_ms ? `${(data.metrics.latency_ms / 1000).toFixed(2)}s` : '-';
            telemetrySteps.textContent = data.metrics.total_steps || '-';
            telemetryTokens.textContent = data.metrics.total_tokens || '-';
        }

        scrollToBottom();
    }

    function createReActTraceDrawer(steps, metrics) {
        const container = document.createElement('div');
        container.className = 'react-steps-container';

        const stepWord = steps.length === 1 ? 'bước' : 'bước';
        const latencyText = metrics && metrics.latency_ms ? `, ${(metrics.latency_ms / 1000).toFixed(2)}s` : '';

        container.innerHTML = `
            <div class="steps-header">
                <div class="steps-header-left">
                    <span class="material-symbols-outlined">analytics</span>
                    <span>Tiến trình ReAct (${steps.length} ${stepWord}${latencyText})</span>
                </div>
                <div class="steps-header-right">
                    <span>Xem chi tiết</span>
                    <span class="material-symbols-outlined">expand_more</span>
                </div>
            </div>
            <div class="steps-body"></div>
        `;

        const header = container.querySelector('.steps-header');
        header.addEventListener('click', () => {
            container.classList.toggle('open');
            scrollToBottom();
        });

        const body = container.querySelector('.steps-body');

        steps.forEach((step) => {
            const stepBlock = document.createElement('div');
            stepBlock.className = 'step-block';

            let blockContent = `
                <div class="step-number">${step.step}</div>
                <div class="step-thought">
                    <strong>Thought:</strong> ${escapeHtml(step.thought)}
                </div>
            `;

            if (step.action) {
                const paramsStr = step.action_input ? JSON.stringify(step.action_input, null, 2) : '{}';
                blockContent += `
                    <div class="step-action-box">
                        <div class="action-title">
                            <span class="material-symbols-outlined">construction</span>
                            <span>Action: ${escapeHtml(step.action)}</span>
                        </div>
                        <pre class="action-code">${escapeHtml(paramsStr)}</pre>
                    </div>
                `;
            }

            if (step.observation) {
                blockContent += `
                    <div class="step-observation-box">
                        <div class="observation-title">
                            <span class="material-symbols-outlined">visibility</span>
                            <span>Observation:</span>
                        </div>
                        <pre class="observation-code">${escapeHtml(step.observation)}</pre>
                    </div>
                `;
            }

            stepBlock.innerHTML = blockContent;
            body.appendChild(stepBlock);
        });

        return container;
    }

    function checkAndRenderTicket(steps) {
        if (!steps) return;

        // Find if a tool book_movie_ticket returned successful booking data
        let bookingData = null;

        for (const step of steps) {
            if (step.action === 'book_movie_ticket' && step.observation) {
                try {
                    const parsedObs = JSON.parse(step.observation);
                    if (parsedObs && parsedObs.status === 'success' && parsedObs.booking_confirmed) {
                        bookingData = parsedObs;
                        break;
                    }
                } catch (e) {
                    // Ignore parsing errors
                }
            }
        }

        if (!bookingData) return;

        // Render Ticket
        const ticketMessageDiv = document.createElement('div');
        ticketMessageDiv.className = 'message bot-message ticket-container';

        const isVip = bookingData.seat_type.toLowerCase() === 'vip';
        const isPremium = bookingData.seat_type.toLowerCase() === 'premium';

        let seatBadgeHtml = bookingData.seat_type.toUpperCase();
        if (isVip) {
            seatBadgeHtml = `<span class="td-val vip-badge"><span class="material-symbols-outlined">stars</span> VIP</span>`;
        } else if (isPremium) {
            seatBadgeHtml = `<span class="td-val" style="color: var(--secondary);">${bookingData.seat_type.toUpperCase()}</span>`;
        } else {
            seatBadgeHtml = `<span class="td-val">${bookingData.seat_type.toUpperCase()}</span>`;
        }

        const formattedPrice = bookingData.total_price ? bookingData.total_price.toLocaleString('vi-VN') + ' VND' : 'N/A';

        ticketMessageDiv.innerHTML = `
            <div class="ticket">
                <div class="ticket-header">
                    <span class="ticket-title">VÉ XEM PHIM CHI TIẾT</span>
                    <span class="ticket-booking-id">${escapeHtml(bookingData.booking_id)}</span>
                </div>
                <div class="ticket-body">
                    <div class="ticket-movie-name">${escapeHtml(bookingData.movie_name)}</div>
                    <div class="ticket-details-grid">
                        <div class="ticket-detail-item">
                            <span class="td-label">Rạp Chiếu</span>
                            <span class="td-val">${escapeHtml(bookingData.cinema_name)}</span>
                        </div>
                        <div class="ticket-detail-item">
                            <span class="td-label">Suất Chiếu</span>
                            <span class="td-val">${escapeHtml(bookingData.showtime)}</span>
                        </div>
                        <div class="ticket-detail-item">
                            <span class="td-label">Loại Ghế</span>
                            ${seatBadgeHtml}
                        </div>
                        <div class="ticket-detail-item">
                            <span class="td-label">Số Lượng</span>
                            <span class="td-val">${bookingData.quantity} vé</span>
                        </div>
                    </div>
                </div>
                <div class="ticket-footer">
                    <div class="ticket-barcode-container"></div>
                    <div class="ticket-price">${escapeHtml(formattedPrice)}</div>
                </div>
            </div>
        `;

        messagesContainer.appendChild(ticketMessageDiv);
        scrollToBottom();
    }

    // ─────────────────────────────────────────────────────────────────────────────
    // 5. HELPER FUNCTIONS
    // ─────────────────────────────────────────────────────────────────────────────

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatMarkdown(text) {
        if (!text) return '';
        // Escape HTML first to prevent XSS in assistant response text
        let escaped = escapeHtml(text);

        // Convert **bold** to <strong>bold</strong>
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Convert *italic* to <em>italic</em>
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Convert `code` to <code>code</code>
        escaped = escaped.replace(/`(.*?)`/g, '<code>$1</code>');

        // Convert newline \n to <br>
        escaped = escaped.replace(/\n/g, '<br>');

        return escaped;
    }
});
