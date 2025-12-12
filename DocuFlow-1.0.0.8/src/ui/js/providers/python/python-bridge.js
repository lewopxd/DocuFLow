// js/python-bridge.js
/**
 * Project: DocuFlow
 * File:  python-bridge.js
 * Created: 2025-10-29 (Renamed from bridge.js)
 * Author: @lewopxd 
 *
 * Description:
 * Low-level communication bridge to the pywebview backend.
 * Manages message queues, retries, and handshake.
 * This script runs globally and creates 'window.bridgePy'.
 */

class BridgePy {
    constructor() {
        this.messageQueue = [];
        this.pendingMessages = new Map();
        this.isReady = false;
        this.maxRetries = 3;
        this.retryDelay = 100;  // Reduced from 1000ms for faster response
        this.queueLocked = false;

        this.init();
    }

    async init() {
        // Wait for pywebview to be available
        await this.waitForPywebview();

        // Perform handshake
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

                // Process pending queue
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
                        // Error - retry
                        messageInfo.retries++;

                        if (messageInfo.retries >= messageInfo.maxRetries) {
                            messageInfo.reject(new Error(response.content.error || 'Unknown error'));
                            this.pendingMessages.delete(messageInfo.message.id);
                            this.messageQueue.shift();
                        } else {
                            console.warn(`⚠️ Retrying message (${messageInfo.retries}/${messageInfo.maxRetries})`);
                            await this.delay(this.retryDelay);
                        }
                    }
                } else {
                    console.warn('⚠️ Response ID mismatch');
                    await this.delay(this.retryDelay);
                }
            } catch (error) {
                messageInfo.retries++;

                if (messageInfo.retries >= messageInfo.maxRetries) {
                    messageInfo.reject(error);
                    this.pendingMessages.delete(messageInfo.message.id);
                    this.messageQueue.shift();
                } else {
                    console.warn(`⚠️ Retrying on error (${messageInfo.retries}/${messageInfo.maxRetries})`);
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
        console.log('📨 Message from Python:', message);
        // Emit events or call callbacks here
        window.dispatchEvent(new CustomEvent('python-message', { detail: message }));
    }

    clearQueue() {
        this.messageQueue = [];
        this.pendingMessages.forEach(info => {
            info.reject(new Error('Queue cleared'));
        });
        this.pendingMessages.clear();
        console.log('🧹 Message queue cleared');
    }
}

// Create global instance
window.bridgePy = new BridgePy();