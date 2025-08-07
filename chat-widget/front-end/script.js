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
        this.debugMode = true; // Activer pour voir les logs détaillés
        
        // Tracking
        this.currentRequestId = null;
        this.requestHistory = [];
        
        // Initialize
        this.bindEvents();
        this.initializeChat();
    }

    /**
     * Système de logging frontend
     */
    logStep(step, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            requestId: this.currentRequestId,
            step,
            message,
            data: data ? JSON.stringify(data).substring(0, 200) : null
        };

        // Colors pour les logs
        const colors = {
            'USER_INPUT': 'color: #2196F3; font-weight: bold;',
            'VALIDATION': 'color: #FF9800; font-weight: bold;',
            'REQUEST_START': 'color: #4CAF50; font-weight: bold;',
            'REQUEST_SENT': 'color: #9C27B0; font-weight: bold;',
            'RESPONSE_RECEIVED': 'color: #00BCD4; font-weight: bold;',
            'RESPONSE_PROCESSED': 'color: #8BC34A; font-weight: bold;',
            'ERROR': 'color: #F44336; font-weight: bold;',
            'UI_UPDATE': 'color: #607D8B; font-weight: bold;'
        };

        const style = colors[step] || 'color: #666;';
        
        if (this.debugMode) {
            console.log(
                `%c[FRONTEND${this.currentRequestId ? '-' + this.currentRequestId.substring(0,8) : ''}] ${step}: ${message}`, 
                style
            );
            if (data) {
                console.log(`%c  └─ Data: ${logEntry.data}`, 'color: #999; font-size: 11px;');
            }
        }

        // Garder un historique des logs pour debugging
        if (this.currentRequestId) {
            const requestLog = this.requestHistory.find(r => r.requestId === this.currentRequestId);
            if (requestLog) {
                requestLog.steps.push(logEntry);
            }
        }
    }

    /**
     * Démarrer le tracking d'une nouvelle requête
     */
    startRequestTracking(userMessage) {
        this.currentRequestId = this.generateRequestId();
        const requestLog = {
            requestId: this.currentRequestId,
            userMessage: userMessage.substring(0, 100),
            startTime: new Date(),
            steps: [],
            endTime: null,
            success: null,
            response: null
        };

        this.requestHistory.push(requestLog);
        
        // Limiter l'historique à 50 requêtes
        if (this.requestHistory.length > 50) {
            this.requestHistory.shift();
        }

        this.logStep('REQUEST_START', `Nouvelle requête démarrée`, { 
            messageLength: userMessage.length,
            requestId: this.currentRequestId
        });

        return this.currentRequestId;
    }

    /**
     * Terminer le tracking d'une requête
     */
    finishRequestTracking(success, response = null, error = null) {
        if (!this.currentRequestId) return;

        const requestLog = this.requestHistory.find(r => r.requestId === this.currentRequestId);
        if (requestLog) {
            requestLog.endTime = new Date();
            requestLog.duration = requestLog.endTime - requestLog.startTime;
            requestLog.success = success;
            requestLog.response = response ? response.substring(0, 100) : null;
            requestLog.error = error;
        }

        const status = success ? 'SUCCÈS' : 'ÉCHEC';
        const color = success ? 'color: #4CAF50; font-weight: bold;' : 'color: #F44336; font-weight: bold;';
        
        if (this.debugMode) {
            console.log(
                `%c[FRONTEND-${this.currentRequestId.substring(0,8)}] REQUÊTE TERMINÉE - ${status}`, 
                color
            );
            if (requestLog) {
                console.log(`%c  └─ Durée: ${requestLog.duration}ms`, 'color: #666; font-size: 11px;');
                console.log(`%c  └─ Étapes: ${requestLog.steps.length}`, 'color: #666; font-size: 11px;');
            }
        }

        this.currentRequestId = null;
    }

    /**
     * Générer un ID de requête unique
     */
    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Méthode publique pour voir l'historique des requêtes
     */
    getRequestHistory() {
        return this.requestHistory.map(r => ({
            requestId: r.requestId,
            userMessage: r.userMessage,
            duration: r.duration,
            success: r.success,
            stepsCount: r.steps.length,
            timestamp: r.startTime
        }));
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        this.chatButton.addEventListener("click", () => {
            this.logStep('UI_UPDATE', 'Bouton chat cliqué');
            this.toggleChat();
        });
        
        this.closeBtn.addEventListener("click", () => {
            this.logStep('UI_UPDATE', 'Bouton fermeture cliqué');
            this.closeChat();
        });
        
        this.chatForm.addEventListener("submit", (e) => this.handleSubmit(e));
        
        document.addEventListener("click", (e) => {
            if (this.isOpen && 
                !this.chatBox.contains(e.target) && 
                !this.chatButton.contains(e.target)) {
                this.logStep('UI_UPDATE', 'Fermeture par clic externe');
                this.closeChat();
            }
        });

        this.userInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.chatForm.dispatchEvent(new Event("submit"));
            }
        });

        this.userInput.addEventListener("input", (e) => {
            this.validateInput(e.target.value);
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && this.isOpen) {
                this.logStep('UI_UPDATE', 'Fermeture par touche Échap');
                this.closeChat();
            }
        });

        // Ajouter un raccourci pour voir les logs en appuyant sur Ctrl+Shift+D
        document.addEventListener("keydown", (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'D') {
                this.showDebugInfo();
            }
        });
    }

    /**
     * Afficher les informations de debug
     */
    showDebugInfo() {
        const history = this.getRequestHistory();
        console.group('🔍 CHATBOT DEBUG INFO');
        console.log('📊 Historique des requêtes:', history);
        console.log('⚡ Requête actuelle:', this.currentRequestId);
        console.log('🔧 Mode debug:', this.debugMode);
        console.log('📡 API URL:', this.apiUrl);
        console.log('💬 Chat ouvert:', this.isOpen);
        console.log('⏳ En cours:', this.isLoading);
        console.groupEnd();
    }

    /**
     * Initialize chat with welcome state
     */
    initializeChat() {
        this.logStep('UI_UPDATE', 'Widget chatbot initialisé');
    }

    /**
     * Toggle chat visibility
     */
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    /**
     * Open chat
     */
    openChat() {
        this.chatBox.classList.remove("hidden");
        this.isOpen = true;
        this.userInput.focus();
        this.logStep('UI_UPDATE', 'Chat ouvert');
    }

    /**
     * Close chat
     */
    closeChat() {
        this.chatBox.classList.add("hidden");
        this.isOpen = false;
        this.logStep('UI_UPDATE', 'Chat fermé');
    }

    /**
     * Handle form submission avec traçabilité complète
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isLoading) {
            this.logStep('VALIDATION', 'Requête ignorée - traitement en cours');
            return;
        }
        
        const message = this.userInput.value.trim();
        
        // Démarrer le tracking
        const requestId = this.startRequestTracking(message);
        
        this.logStep('USER_INPUT', 'Message utilisateur capturé', { 
            messageLength: message.length,
            isEmpty: !message,
            tooLong: message.length > 500
        });

        // Validation
        this.logStep('VALIDATION', 'Début de la validation');
        
        if (!message) {
            this.logStep('ERROR', 'Message vide détecté');
            this.showError("Veuillez saisir un message.");
            this.finishRequestTracking(false, null, 'Message vide');
            return;
        }

        if (message.length > 500) {
            this.logStep('ERROR', 'Message trop long détecté');
            this.showError("Le message est trop long (maximum 500 caractères).");
            this.finishRequestTracking(false, null, 'Message trop long');
            return;
        }

        this.logStep('VALIDATION', 'Validation réussie');

        // Mise à jour UI
        this.logStep('UI_UPDATE', 'Ajout du message utilisateur');
        this.appendMessage("user", message);
        this.userInput.value = "";
        this.setLoading(true);
        
        this.logStep('UI_UPDATE', 'Indicateur de frappe affiché');
        this.showTypingIndicator();

        try {
            this.logStep('REQUEST_SENT', 'Envoi de la requête au backend', {
                url: this.apiUrl,
                method: 'POST'
            });

            const response = await this.sendMessageToServer(message, requestId);
            
            this.logStep('RESPONSE_RECEIVED', 'Réponse reçue du backend', {
                hasResponse: !!response.response,
                hasError: !!response.error,
                responseLength: response.response ? response.response.length : 0,
                backendRequestId: response.requestId
            });
            
            this.removeTypingIndicator();
            
            if (response.response) {
                this.logStep('RESPONSE_PROCESSED', 'Traitement de la réponse réussie');
                this.appendMessage("bot", response.response);
                this.finishRequestTracking(true, response.response);
            } else if (response.error) {
                this.logStep('ERROR', 'Erreur dans la réponse', { error: response.error });
                this.appendError(`Erreur: ${response.error}`);
                this.finishRequestTracking(false, null, response.error);
            } else {
                this.logStep('ERROR', 'Réponse invalide du serveur');
                this.appendError("Réponse invalide du serveur");
                this.finishRequestTracking(false, null, 'Réponse invalide');
            }
            
        } catch (error) {
            this.logStep('ERROR', `Erreur lors de l'envoi: ${error.message}`, {
                errorName: error.name,
                errorType: typeof error
            });
            
            console.error(`[FRONTEND-${requestId.substring(0,8)}] ERREUR CHAT:`, error);
            this.removeTypingIndicator();
            this.handleError(error);
            this.finishRequestTracking(false, null, error.message);
        } finally {
            this.logStep('UI_UPDATE', 'Remise à zéro de l\'état de chargement');
            this.setLoading(false);
        }
    }

    /**
     * Send message to server avec ID de tracking
     */
    async sendMessageToServer(message, requestId) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 secondes

        try {
            this.logStep('REQUEST_SENT', 'Appel fetch en cours', {
                timeout: '30s',
                hasAbortController: true
            });

            const response = await fetch(this.apiUrl, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": requestId // Envoyer l'ID de tracking
                },
                body: JSON.stringify({ 
                    message,
                    clientRequestId: requestId // Double sécurité
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            this.logStep('RESPONSE_RECEIVED', `Réponse HTTP reçue`, {
                status: response.status,
                statusText: response.statusText,
                ok: response.ok
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            this.logStep('RESPONSE_PROCESSED', 'JSON parsé avec succès', {
                hasResponse: !!data.response,
                backendRequestId: data.requestId,
                processingTime: data.processingTime
            });

            return data;

        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                this.logStep('ERROR', 'Timeout de la requête (30s)');
                throw new Error('REQUEST_TIMEOUT');
            }
            
            this.logStep('ERROR', `Erreur fetch: ${error.message}`);
            throw error;
        }
    }

    /**
     * Handle different types of errors
     */
    handleError(error) {
        let errorMessage = "Désolé, je ne peux pas répondre pour le moment. ";
        
        if (error.message === 'REQUEST_TIMEOUT') {
            errorMessage += "La requête a pris trop de temps.";
        } else if (error.name === "TypeError" && error.message.includes("fetch")) {
            errorMessage += "Vérifiez que le serveur est démarré.";
        } else if (error.message.includes("404")) {
            errorMessage += "Service non trouvé.";
        } else if (error.message.includes("500")) {
            errorMessage += "Erreur du serveur.";
        } else if (error.message.includes("Failed to fetch")) {
            errorMessage += "Problème de connexion réseau.";
        } else {
            errorMessage += "Veuillez réessayer plus tard.";
        }
        
        this.appendError(errorMessage);
        this.logStep('UI_UPDATE', 'Message d\'erreur affiché à l\'utilisateur');
    }

    /**
     * Validate user input
     */
    validateInput(value) {
        const length = value.length;
        const maxLength = 500;
        
        if (length > maxLength) {
            this.userInput.style.borderColor = "#f44336";
            this.showInputError(`${length}/${maxLength} caractères (trop long)`);
        } else if (length > maxLength * 0.8) {
            this.userInput.style.borderColor = "#ff9800";
            this.showInputError(`${length}/${maxLength} caractères`);
        } else {
            this.userInput.style.borderColor = "#e0e0e0";
            this.hideInputError();
        }
    }

    /**
     * Show input error
     */
    showInputError(message) {
        let errorEl = document.getElementById("input-error");
        if (!errorEl) {
            errorEl = document.createElement("div");
            errorEl.id = "input-error";
            errorEl.style.cssText = `
                font-size: 11px;
                color: #f44336;
                margin-top: 4px;
                text-align: right;
            `;
            this.userInput.parentNode.appendChild(errorEl);
        }
        errorEl.textContent = message;
    }

    /**
     * Hide input error
     */
    hideInputError() {
        const errorEl = document.getElementById("input-error");
        if (errorEl) {
            errorEl.remove();
        }
    }

    /**
     * Show a simple error message to user
     */
    showError(message) {
        alert(message);
    }

    /**
     * Append user or bot message
     */
    appendMessage(sender, text) {
        const messageEl = document.createElement("div");
        messageEl.className = `message ${sender}`;
        messageEl.textContent = text;
        
        // Add timestamp
        const timeEl = document.createElement("div");
        timeEl.className = "message-time";
        timeEl.textContent = this.getCurrentTime();
        messageEl.appendChild(timeEl);
        
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
        
        this.logStep('UI_UPDATE', `Message ${sender} ajouté`, { 
            textLength: text.length 
        });
    }

    /**
     * Append error message
     */
    appendError(text) {
        const messageEl = document.createElement("div");
        messageEl.className = "error-message";
        messageEl.textContent = text;
        this.chatMessages.appendChild(messageEl);
        this.scrollToBottom();
        
        this.logStep('UI_UPDATE', 'Message d\'erreur ajouté', { 
            errorText: text.substring(0, 50) 
        });
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        const typingEl = document.createElement("div");
        typingEl.className = "message typing";
        typingEl.id = "typing-indicator";
        typingEl.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        this.chatMessages.appendChild(typingEl);
        this.scrollToBottom();
    }

    /**
     * Remove typing indicator
     */
    removeTypingIndicator() {
        const typingEl = document.getElementById("typing-indicator");
        if (typingEl) {
            typingEl.remove();
        }
    }

    /**
     * Set loading state
     */
    setLoading(loading) {
        this.isLoading = loading;
        this.sendBtn.disabled = loading;
        this.userInput.disabled = loading;
        
        if (loading) {
            this.userInput.placeholder = "Traitement en cours...";
            this.sendBtn.classList.add("loading");
        } else {
            this.userInput.placeholder = "Posez votre question...";
            this.sendBtn.classList.remove("loading");
            setTimeout(() => this.userInput.focus(), 100);
        }
        
        this.logStep('UI_UPDATE', `État de chargement: ${loading ? 'activé' : 'désactivé'}`);
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    /**
     * Get current time for timestamps
     */
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    /**
     * Public method to send a programmatic message
     */
    sendMessage(message) {
        if (typeof message === 'string' && message.trim()) {
            this.logStep('USER_INPUT', 'Message programmatique envoyé', { 
                source: 'external',
                message: message.substring(0, 50)
            });
            this.userInput.value = message.trim();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    /**
     * Public method to clear chat
     */
    clearChat() {
        this.chatMessages.innerHTML = '';
        this.logStep('UI_UPDATE', 'Chat vidé');
    }

    /**
     * Public method to get chat status
     */
    getStatus() {
        return {
            isOpen: this.isOpen,
            isLoading: this.isLoading,
            apiUrl: this.apiUrl,
            messagesCount: this.chatMessages.children.length,
            currentRequestId: this.currentRequestId,
            requestHistoryCount: this.requestHistory.length,
            debugMode: this.debugMode
        };
    }

    /**
     * Méthode pour activer/désactiver le mode debug
     */
    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        console.log(`%c🔧 Mode debug ${this.debugMode ? 'ACTIVÉ' : 'DÉSACTIVÉ'}`, 
                   'color: #FF5722; font-weight: bold; font-size: 14px;');
        
        if (this.debugMode) {
            console.log('%c💡 Utilisez Ctrl+Shift+D pour voir les infos de debug', 
                       'color: #2196F3; font-size: 12px;');
        }
    }
}

// Initialize the chatbot widget when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
    console.log('%c🚀 OPTIM Finance Chatbot Widget - Initialisation...', 
               'color: #4CAF50; font-weight: bold; font-size: 16px;');
    
    // Create global chatbot instance
    window.chatbot = new ChatbotWidget();
    
    // Optional: Add some global functions for external access
    window.chatbotUtils = {
        open: () => window.chatbot.openChat(),
        close: () => window.chatbot.closeChat(),
        send: (message) => window.chatbot.sendMessage(message),
        clear: () => window.chatbot.clearChat(),
        status: () => window.chatbot.getStatus(),
        history: () => window.chatbot.getRequestHistory(),
        debug: () => window.chatbot.showDebugInfo(),
        toggleDebug: () => window.chatbot.toggleDebugMode()
    };
    
    console.log('%c✅ OPTIM Finance Chatbot Widget chargé avec succès!', 
               'color: #4CAF50; font-weight: bold;');
    console.log('%c🔧 Utilisez window.chatbotUtils pour accéder aux fonctions avancées', 
               'color: #2196F3; font-size: 12px;');
    console.log('%c📊 Utilisez Ctrl+Shift+D pour voir les informations de debug', 
               'color: #FF9800; font-size: 12px;');
});

// Handle page visibility changes
document.addEventListener("visibilitychange", () => {
    if (document.hidden && window.chatbot && window.chatbot.isOpen) {
        console.log('%c👁️ Page cachée - chat toujours ouvert', 'color: #666; font-size: 11px;');
    } else if (!document.hidden && window.chatbot && window.chatbot.isOpen) {
        console.log('%c👁️ Page visible - chat ouvert', 'color: #666; font-size: 11px;');
    }
});

// Handle window resize
window.addEventListener("resize", () => {
    if (window.chatbot && window.chatbot.isOpen) {
        window.chatbot.scrollToBottom();
    }
});