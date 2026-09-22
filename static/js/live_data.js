/**
 * AgroFedly Live Data Manager
 * Phase 59: Global Auto-Refresh & Real-Time Sync
 * 
 * Features:
 * - Centralized interval management (avoids setInterval spaghetti)
 * - Visibility-aware polling (pauses when tab is inactive)
 * - Network-aware (pauses when offline, handles exponential backoff)
 * - Request deduplication (coalesces duplicate fetch calls)
 */

class LiveDataManager {
    constructor() {
        this.tasks = new Map(); // Registry of periodic polling tasks
        this.cache = new Map(); // Shared local cache
        this.activeRequests = new Map(); // Deduplication registry
        
        this.isOnline = navigator.onLine;
        this.isVisible = document.visibilityState === 'visible';
        
        this.wsConnections = new Map(); // Managed WebSockets
        this.baseBackoff = 2000;
        this.maxBackoff = 30000;
        
        this._bindEvents();
        this._initUI();
    }

    _bindEvents() {
        // Network Events
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateStatusIndicator('online');
            this._resumeAll();
            this._reconnectSockets();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateStatusIndicator('offline');
            this._pauseAll();
        });

        // Visibility Events
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.isVisible = true;
                this._resumeAll();
                this._refreshStaleData();
            } else {
                this.isVisible = false;
                this._pauseAll();
            }
        });
    }

    _initUI() {
        // Find or create global live status indicator in navbar
        this.statusIndicator = document.getElementById('agrofedly-live-status');
        if (!this.statusIndicator) {
            const navbar = document.querySelector('.rd-top-actions');
            if (navbar) {
                const el = document.createElement('div');
                el.id = 'agrofedly-live-status';
                el.className = 'live-status-indicator online';
                el.innerHTML = `<span class="live-dot"></span> <span class="live-text">Live</span>`;
                navbar.insertBefore(el, navbar.firstChild);
                this.statusIndicator = el;
            }
        }
    }

    updateStatusIndicator(state, message = '') {
        if (!this.statusIndicator) return;
        
        const dot = this.statusIndicator.querySelector('.live-dot');
        const text = this.statusIndicator.querySelector('.live-text');
        
        this.statusIndicator.className = `live-status-indicator ${state}`;
        if (state === 'offline') {
            text.textContent = 'Offline';
        } else if (state === 'updating') {
            text.textContent = 'Updating...';
        } else if (state === 'reconnecting') {
            text.textContent = 'Reconnecting...';
        } else {
            text.textContent = message || 'Live';
        }
    }

    /**
     * Register a polling task
     * @param {string} id - Unique identifier for the task
     * @param {number} interval - Polling interval in ms
     * @param {Function} fetchCallback - Async function returning data
     * @param {Function} renderCallback - Function to call when data arrives
     */
    registerPoll(id, interval, fetchCallback, renderCallback) {
        if (this.tasks.has(id)) {
            console.warn(`LiveDataManager: Task ${id} is already registered.`);
            return;
        }

        const task = {
            id,
            interval,
            fetchCallback,
            renderCallback,
            timer: null,
            lastRun: 0,
            backoff: this.baseBackoff
        };

        this.tasks.set(id, task);
        
        // Initial fetch immediately if visible and online
        if (this.isVisible && this.isOnline) {
            this._executeTask(task);
        }
    }

    unregisterPoll(id) {
        const task = this.tasks.get(id);
        if (task && task.timer) {
            clearTimeout(task.timer);
        }
        this.tasks.delete(id);
    }

    async _executeTask(task) {
        if (!this.isVisible || !this.isOnline) {
            this._scheduleNext(task);
            return;
        }

        this.updateStatusIndicator('updating');
        try {
            // Deduplicate: If request is already running, wait for it
            if (!this.activeRequests.has(task.id)) {
                this.activeRequests.set(task.id, task.fetchCallback());
            }
            
            const data = await this.activeRequests.get(task.id);
            this.activeRequests.delete(task.id);

            // Success
            task.backoff = this.baseBackoff; 
            task.lastRun = Date.now();
            task.renderCallback(data);
            
            this.updateStatusIndicator('online', `Updated just now`);
        } catch (error) {
            console.error(`LiveDataManager: Task ${task.id} failed:`, error);
            task.backoff = Math.min(task.backoff * 2, this.maxBackoff);
            this.activeRequests.delete(task.id);
            this.updateStatusIndicator('online', `Update failed. Retrying...`);
        }

        this._scheduleNext(task);
    }

    _scheduleNext(task) {
        if (task.timer) clearTimeout(task.timer);
        const delay = Math.max(task.interval, task.backoff);
        task.timer = setTimeout(() => this._executeTask(task), delay);
    }

    _pauseAll() {
        this.tasks.forEach(task => {
            if (task.timer) {
                clearTimeout(task.timer);
                task.timer = null;
            }
        });
    }

    _resumeAll() {
        this.tasks.forEach(task => {
            if (!task.timer) {
                this._executeTask(task);
            }
        });
    }

    _refreshStaleData() {
        const now = Date.now();
        this.tasks.forEach(task => {
            if (now - task.lastRun > task.interval) {
                this._executeTask(task);
            }
        });
    }

    /**
     * Managed WebSocket connection with org-isolation routing and automatic reconnect
     */
    connectWebSocket(name, url, onMessageCallback) {
        if (this.wsConnections.has(name)) {
            return;
        }

        let ws = null;
        let reconnectTimer = null;
        let backoff = this.baseBackoff;

        const connect = () => {
            if (!this.isOnline) return;
            
            const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + url;
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                backoff = this.baseBackoff;
                this.updateStatusIndicator('online');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    onMessageCallback(data);
                } catch (e) {
                    console.error("LiveDataManager: Error parsing WS message", e);
                }
            };

            ws.onclose = (e) => {
                if (e.code !== 1000) { // Abnormal close
                    this.updateStatusIndicator('reconnecting');
                    if (this.isOnline) {
                        reconnectTimer = setTimeout(connect, backoff);
                        backoff = Math.min(backoff * 2, this.maxBackoff);
                    }
                }
            };
        };

        connect();

        this.wsConnections.set(name, {
            reconnect: connect,
            close: () => {
                if (reconnectTimer) clearTimeout(reconnectTimer);
                if (ws) ws.close(1000);
                this.wsConnections.delete(name);
            },
            send: (payload) => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify(payload));
                }
            }
        });
    }

    _reconnectSockets() {
        this.wsConnections.forEach(conn => {
            conn.reconnect();
        });
    }
}

// Global Singleton Instance
window.agrofedlyLive = new LiveDataManager();
