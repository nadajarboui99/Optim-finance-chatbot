class ChatbotWidget {
    constructor() {
        // DOM elements
        this.chatButton = document.getElementById("chat-button");
        this.chatBox = document.getElementById("chat-box");
        this.closeBtn = document.getElementById("close-btn");
        this.chatForm = document.getElementById("chat-form");
        this.userInput = document.getElementById("user-input");
        this.chatMessages = document.getElementById("chat-messages");
        this.sendBtn = document.getElementById("send-btn");
        
        // State
        this.isLoading = false;
        this.apiUrl = "http://localhost:3000/chat";
        this.isOpen = false;
        this.debugMode = false; // Disabled by default for performance
        
        // Performance optimization
        this.requestQueue = [];
        this.isProcessingQueue = false;
        this.lastRequestTime = 0;
        this.minRequestInterval = 500; // Prevent rapid requests
        
        // Reduced tracking (only essential data)
        this.currentRequestId = null;
        this.requestCount = 0;
        
        // Initialize
        this.bindEvents();
        this.initializeChat();
        this.preconnect(); // Establish connection early
    }

    /**
     * Preconnect to backend to reduce first request latency
     */
    async preconnect() {
        try {
            await fetch(`http://localhost:3000/health`, {
                method: 'GET',
                cache: 'no-cache'
            });
            this.log('Backend preconnection successful');
        } catch (error) {
            this.log('Backend preconnection failed:', error.message);
        }
    }

    /**
     * Minimal logging system (only when debug mode is on)
     */
    log(message, data = null) {
        if (this.debugMode) {
            console.log(`[CHATBOT] ${message}`, data || '');
        }
    }

    /**
     * Bind essential events only
     */
    bindEvents() {
        // Use passive listeners where possible for better performance
        this.chatButton.addEventListener("click", () => this.toggleChat());
        this.closeBtn.addEventListener("click", () => this.closeChat());
        this.chatForm.addEventListener("submit", (e) => this.handleSubmit(e));
        
        // Optimized input handling with debouncing
        let inputTimeout;
        this.userInput.addEventListener("input", (e) => {
            clearTimeout(inputTimeout);
            inputTimeout = setTimeout(() => this.validateInput(e.target.value), 150);
        });

        // Essential keyboard shortcuts only
        this.userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.chatForm.dispatchEvent(new Event("submit"));
            }
        });

        // Optimized outside click handler
        document.addEventListener("click", (e) => {
            if (this.isOpen && 
                !this.chatBox.contains(e.target) && 
                !this.chatButton.contains(e.target)) {
                this.closeChat();
            }
        }, { passive: true });

        // ESC key to close
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && this.isOpen) {
                this.closeChat();
            }
        });
    }

    initializeChat() {
        this.log('Chatbot widget initialized');
    }

    toggleChat() {
        this.isOpen ? this.closeChat() : this.openChat();
    }

    openChat() {
        this.chatBox.classList.remove("hidden");
        this.isOpen = true;
        // Use requestAnimationFrame for smooth focus
        requestAnimationFrame(() => this.userInput.focus());
        this.log('Chat opened');
    }

    closeChat() {
        this.chatBox.classList.add("hidden");
        this.isOpen = false;
        this.log('Chat closed');
    }

    /**
     * Optimized form submission with request queuing
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isLoading) {
            this.log('Request ignored - already processing');
            return;
        }
        
        const message = this.userInput.value.trim();
        
        // Fast validation
        if (!message) {
            this.showError("Veuillez saisir un message.");
            return;
        }

        if (message.length > 500) {
            this.showError("Message trop long (max 500 caractères).");
            return;
        }

        // Throttling to prevent spam
        const now = Date.now();
        if (now - this.lastRequestTime < this.minRequestInterval) {
            this.showError("Veuillez attendre avant d'envoyer un autre message.");
            return;
        }
        this.lastRequestTime = now;

        // Generate simple request ID
        this.currentRequestId = `req_${++this.requestCount}_${Date.now()}`;
        
        this.log(`Processing message: "${message.substring(0, 50)}..."`);

        // Update UI immediately for responsiveness
        this.appendMessage("user", message);
        this.userInput.value = "";
        this.setLoading(true);
        this.showTypingIndicator();

        try {
            const startTime = Date.now();
            const response = await this.sendMessageToServer(message, this.currentRequestId);
            const responseTime = Date.now() - startTime;
            
            this.log(`Response received in ${responseTime}ms`);
            
            this.removeTypingIndicator();
            
            if (response.response) {
                this.appendMessage("bot", response.response);
            } else {
                this.appendError("Réponse invalide du serveur");
            }
            
        } catch (error) {
            this.log(`Request failed: ${error.message}`);
            this.removeTypingIndicator();
            this.handleError(error);
        } finally {
            this.setLoading(false);
            this.currentRequestId = null;
        }
    }

    /**
     * Optimized server communication
     */
    async sendMessageToServer(message, requestId) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 25000); // 25s timeout

        try {
            const response = await fetch(this.apiUrl, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({ 
                    message,
                    clientRequestId: requestId
                }),
                signal: controller.signal,
                // Performance optimizations
                cache: 'no-cache',
                keepalive: false
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                throw new Error('REQUEST_TIMEOUT');
            }
            
            throw error;
        }
    }

    /**
     * Optimized error handling
     */
    handleError(error) {
        let errorMessage = "Je ne peux pas répondre pour le moment. ";
        
        if (error.message === 'REQUEST_TIMEOUT') {
            errorMessage += "La requête a pris trop de temps.";
        } else if (error.name === "TypeError" && error.message.includes("fetch")) {
            errorMessage += "Vérifiez que le serveur est démarré.";
        } else if (error.message.includes("Failed to fetch")) {
            errorMessage += "Problème de connexion réseau.";
        } else {
            errorMessage += "Veuillez réessayer.";
        }
        
        this.appendError(errorMessage);
    }

    /**
     * Fast input validation with visual feedback
     */
    validateInput(value) {
        const length = value.length;
        const maxLength = 500;
        
        if (length > maxLength) {
            this.userInput.style.borderColor = "#f44336";
        } else if (length > maxLength * 0.8) {
            this.userInput.style.borderColor = "#ff9800";
        } else {
            this.userInput.style.borderColor = "#e0e0e0";
        }
    }

    showError(message) {
        // Use a more user-friendly notification instead of alert
        const existingError = this.chatMessages.querySelector('.temp-error');
        if (existingError) existingError.remove();
        
        const errorEl = document.createElement("div");
        errorEl.className = "message error temp-error";
        errorEl.textContent = message;
        errorEl.style.cssText = "background: #ffebee; color: #c62828; padding: 8px; margin: 4px 0; border-radius: 4px; font-size: 14px;";
        
        this.chatMessages.appendChild(errorEl);
        this.scrollToBottom();
        
        // Auto-remove after 3 seconds
        setTimeout(() => errorEl.remove(), 3000);
    }

    /**
     * Optimized message appending with minimal DOM manipulation
     */
    appendMessage(sender, text) {
        const messageEl = document.createElement("div");
        messageEl.className = `message ${sender}`;
        
        // Create message content efficiently
        const textNode = document.createTextNode(text);
        messageEl.appendChild(textNode);
        
        // Add timestamp (simplified)
        const timeEl = document.createElement("div");
        timeEl.className = "message-time";
        timeEl.textContent = new Date().toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        messageEl.appendChild(timeEl);
        
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    appendError(text) {
        const messageEl = document.createElement("div");
        messageEl.className = "error-message";
        messageEl.textContent = text;
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
    }

    /**
     * Lightweight typing indicator
     */
    showTypingIndicator() {
        // Remove existing indicator first
        this.removeTypingIndicator();
        
        const typingEl = document.createElement("div");
        typingEl.className = "message typing";
        typingEl.id = "typing-indicator";
        typingEl.innerHTML = `
            <div class="typing-indicator">
                <span>●</span><span>●</span><span>●</span>
            </div>
        `;
        
        this.chatMessages.appendChild(typingEl);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingEl = document.getElementById("typing-indicator");
        if (typingEl) {
            typingEl.remove();
        }
    }

    /**
     * Optimized loading state management
     */
    setLoading(loading) {
        this.isLoading = loading;
        this.sendBtn.disabled = loading;
        this.userInput.disabled = loading;
        
        if (loading) {
            this.userInput.placeholder = "Traitement...";
            this.sendBtn.classList.add("loading");
        } else {
            this.userInput.placeholder = "Posez votre question...";
            this.sendBtn.classList.remove("loading");
            // Delayed focus to prevent issues
            setTimeout(() => {
                if (!this.isLoading) this.userInput.focus();
            }, 100);
        }
    }

    /**
     * Optimized scrolling with debouncing
     */
    scrollToBottom() {
        // Use RAF for smooth scrolling
        requestAnimationFrame(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        });
    }

    // Public API methods (simplified)
    sendMessage(message) {
        if (typeof message === 'string' && message.trim()) {
            this.userInput.value = message.trim();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    clearChat() {
        this.chatMessages.innerHTML = '';
    }

    getStatus() {
        return {
            isOpen: this.isOpen,
            isLoading: this.isLoading,
            messagesCount: this.chatMessages.children.length,
            requestCount: this.requestCount
        };
    }

    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        console.log(`Debug mode: ${this.debugMode ? 'ON' : 'OFF'}`);
    }
}

// Optimized initialization
document.addEventListener("DOMContentLoaded", () => {
    console.log('🚀 Initializing OPTIM Finance Chatbot...');
    
    // Create global instance
    window.chatbot = new ChatbotWidget();
    
    // Minimal global utilities
    window.chatbotUtils = {
        open: () => window.chatbot.openChat(),
        close: () => window.chatbot.closeChat(),
        send: (msg) => window.chatbot.sendMessage(msg),
        clear: () => window.chatbot.clearChat(),
        status: () => window.chatbot.getStatus(),
        debug: () => window.chatbot.toggleDebugMode()
    };
    
    console.log('✅ Chatbot ready! Use window.chatbotUtils for controls.');
});

// Optimized visibility handling
document.addEventListener("visibilitychange", () => {
    if (!document.hidden && window.chatbot?.isOpen) {
        window.chatbot.scrollToBottom();
    }
}, { passive: true });

// Optimized resize handling with debouncing
let resizeTimeout;
window.addEventListener("resize", () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (window.chatbot?.isOpen) {
            window.chatbot.scrollToBottom();
        }
    }, 100);
}, { passive: true });