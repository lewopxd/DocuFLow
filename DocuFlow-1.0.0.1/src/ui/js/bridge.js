class BridgePy {
    constructor() {
        this.messageQueue = [];
        this.pendingMessages = new Map();
        this.isReady = false;
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.queueLocked = false;
        
        this.init();
    }
    
    async init() {
        // Esperar a que pywebview esté disponible
        await this.waitForPywebview();
        
        // Realizar handshake
        await this.performHandshake();
    }
    
    waitForPywebview() {
        return new Promise((resolve) => {
            const check = () => {
                if (window.pywebview && window.pywebview.api) {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }
    
    async performHandshake() {
        console.log('🤝 Iniciando handshake con Python...');
        
        try {
            const response = await this.send('handshake', {
                client: 'DocuFlow UI',
                timestamp: new Date().toISOString()
            });
            
            if (response.status === 'ready') {
                this.isReady = true;
                console.log('✅ Handshake completado - Python listo');
                console.log('📡 Bridge activo y escuchando');
                
                // Procesar cola pendiente
                this.processQueue();
            } else {
                console.error('❌ Handshake falló');
            }
        } catch (error) {
            console.error('❌ Error en handshake:', error);
        }
    }
    
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    send(msg, content = {}, options = {}) {
        const id = this.generateId();
        const message = { id, msg, content };
        
        return new Promise((resolve, reject) => {
            const messageInfo = {
                message,
                resolve,
                reject,
                retries: 0,
                maxRetries: options.maxRetries || this.maxRetries,
                timestamp: Date.now()
            };
            
            this.pendingMessages.set(id, messageInfo);
            this.messageQueue.push(messageInfo);
            
            if (!this.queueLocked) {
                this.processQueue();
            }
        });
    }
    
    async processQueue() {
        if (this.queueLocked || this.messageQueue.length === 0) return;
        
        this.queueLocked = true;
        
        while (this.messageQueue.length > 0) {
            const messageInfo = this.messageQueue[0];
            
            try {
                const response = await this.sendMessage(messageInfo.message);
                
                if (response.id === messageInfo.message.id) {
                    if (response.response === 'ok') {
                        messageInfo.resolve(response.content);
                        this.pendingMessages.delete(messageInfo.message.id);
                        this.messageQueue.shift();
                    } else {
                        // Error - reintentar
                        messageInfo.retries++;
                        
                        if (messageInfo.retries >= messageInfo.maxRetries) {
                            messageInfo.reject(new Error(response.content.error || 'Error desconocido'));
                            this.pendingMessages.delete(messageInfo.message.id);
                            this.messageQueue.shift();
                        } else {
                            console.warn(`⚠️ Reintentando mensaje (${messageInfo.retries}/${messageInfo.maxRetries})`);
                            await this.delay(this.retryDelay);
                        }
                    }
                } else {
                    console.warn('⚠️ ID de respuesta no coincide');
                    await this.delay(this.retryDelay);
                }
            } catch (error) {
                messageInfo.retries++;
                
                if (messageInfo.retries >= messageInfo.maxRetries) {
                    messageInfo.reject(error);
                    this.pendingMessages.delete(messageInfo.message.id);
                    this.messageQueue.shift();
                } else {
                    console.warn(`⚠️ Reintentando por error (${messageInfo.retries}/${messageInfo.maxRetries})`);
                    await this.delay(this.retryDelay);
                }
            }
        }
        
        this.queueLocked = false;
    }
    
    async sendMessage(message) {
        return await window.pywebview.api.handle_message(message);
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    receiveFromPython(message) {
        console.log('📨 Mensaje desde Python:', message);
        // Aquí puedes emitir eventos o llamar callbacks
        window.dispatchEvent(new CustomEvent('python-message', { detail: message }));
    }
    
    clearQueue() {
        this.messageQueue = [];
        this.pendingMessages.forEach(info => {
            info.reject(new Error('Cola limpiada'));
        });
        this.pendingMessages.clear();
        console.log('🧹 Cola de mensajes limpiada');
    }
}

// Crear instancia global
window.bridgePy = new BridgePy();