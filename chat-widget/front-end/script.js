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
        //  UPDATED: Use deployed backend URL
        this.apiUrl = this.getApiUrl();
        this.healthUrl = this.getHealthUrl();
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
     *  UPDATED: Get API URL based on environment (local vs production)
     */
    getApiUrl() {
        console.log('🔍 Current hostname:', window.location.hostname);
        console.log('🔍 Current port:', window.location.port);
        
        // Check if running locally (for development)
        const isLocal = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname.includes('192.168.') ||
                       window.location.port;
        
        if (isLocal) {
            // Use local proxy when developing locally
            return "/api/query";
        } else {
            // Use deployed backend when on Vercel
            return "https://optim-finance-chatbot-1.onrender.com/query";
        }
    }

    getHealthUrl() {
        // Check if running locally (for development)
        const isLocal = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname.includes('192.168.') ||
                       window.location.port;
        
        if (isLocal) {
            return "/api/health";
        } else {
            return "https://optim-finance-chatbot-1.onrender.com/health";
        }
    }

    /**
     *  UPDATED: Preconnect with dynamic URL and better error handling
     */
    async preconnect() {
        try {
            const response = await fetch(this.healthUrl, {
                method: 'GET',
                cache: 'no-cache',
                mode: 'cors', // Important for cross-origin requests
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.log('Backend preconnection successful', data);
            } else {
                this.log('Backend preconnection failed with status:', response.status);
            }
        } catch (error) {
            this.log('Backend preconnection failed:', error.message);
            // Don't throw error here, just log it - the widget should still work
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
        this.log(`API URL: ${this.apiUrl}`);
        this.log(`Health URL: ${this.healthUrl}`);
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
     * 🔄 UPDATED: Server communication optimized for cross-origin requests
     */
    async sendMessageToServer(message, requestId) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout for remote server

        try {
            const requestBody = { 
                query: message,             
                search_type: "hybrid",      
                top_k: 5                    
            };

            this.log('Sending request to:', this.apiUrl);
            this.log('Request body:', requestBody);

            const response = await fetch(this.apiUrl, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(requestBody),
                signal: controller.signal,
                mode: 'cors', // Important for cross-origin requests
                cache: 'no-cache'
            });

            clearTimeout(timeoutId);

            this.log('Response status:', response.status);
            this.log('Response headers:', Object.fromEntries(response.headers.entries()));

            if (!response.ok) {
                let errorText;
                try {
                    errorText = await response.text();
                    this.log('Error response body:', errorText);
                } catch (e) {
                    errorText = `HTTP ${response.status}`;
                }
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            this.log('Response data:', data);
            return data;

        } catch (error) {
            clearTimeout(timeoutId);
            this.log('Request error:', error);
            
            if (error.name === 'AbortError') {
                throw new Error('REQUEST_TIMEOUT');
            }
            
            // Better network error detection for cross-origin requests
            if (error.name === 'TypeError' || error.message.includes('fetch') || 
                error.message.includes('CORS') || error.message.includes('network')) {
                throw new Error('NETWORK_ERROR');
            }
            
            throw error;
        }
    }

    /**
     * 🔄 IMPROVED: Better error handling for deployed environment
     */
    handleError(error) {
        let errorMessage = "Je ne peux pas répondre pour le moment. ";
        
        if (error.message === 'REQUEST_TIMEOUT') {
            errorMessage += "La requête a pris trop de temps. Le serveur peut être en cours de réveil.";
        } else if (error.message === 'NETWORK_ERROR') {
            errorMessage += "Problème de connexion réseau.";
        } else if (error.message.includes("HTTP 502") || error.message.includes("HTTP 503")) {
            errorMessage += "Service temporairement indisponible. Veuillez réessayer dans quelques instants.";
        } else if (error.message.includes("HTTP 404")) {
            errorMessage += "Service introuvable.";
        } else if (error.message.includes("Failed to fetch") || error.message.includes("CORS")) {
            errorMessage += "Impossible de contacter le serveur. Vérifiez votre connexion internet.";
        } else if (error.message.includes("HTTP 429")) {
            errorMessage += "Trop de requêtes. Veuillez attendre avant de réessayer.";
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
            requestCount: this.requestCount,
            apiUrl: this.apiUrl,
            healthUrl: this.healthUrl
        };
    }

    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        console.log(`Debug mode: ${this.debugMode ? 'ON' : 'OFF'}`);
        if (this.debugMode) {
            console.log('Current configuration:', {
                apiUrl: this.apiUrl,
                healthUrl: this.healthUrl,
                hostname: window.location.hostname,
                origin: window.location.origin,
                isLocal: window.location.hostname === 'localhost' || 
                        window.location.hostname === '127.0.0.1' ||
                        window.location.hostname.includes('192.168.') ||
                        window.location.port
            });
        }
    }
}

// Optimized initialization
document.addEventListener("DOMContentLoaded", () => {
    console.log(' Initializing OPTIM Finance Chatbot...');
    console.log(' Environment detection:');
    console.log('  - Hostname:', window.location.hostname);
    console.log('  - Origin:', window.location.origin);
    console.log('  - Port:', window.location.port);
    
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
    
    console.log(' Chatbot ready! Use window.chatbotUtils for controls.');
    console.log(' Backend URL:', window.chatbot.apiUrl);
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