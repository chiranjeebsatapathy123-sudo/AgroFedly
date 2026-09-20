/**
 * AgroFedly Experience Manager
 * Handles cinematic page transitions, SPA routing, and global interaction states.
 */

export class ExperienceManager {
    constructor() {
        this.mainElement = document.querySelector('main');
        this.cache = new Map(); // Simple page cache
        this.isTransitioning = false;
        
        // State
        this.state = {
            loading: false,
            reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        };

        this.init();
    }

    init() {
        if (!this.mainElement) {
            console.error('[ExperienceManager] <main> element not found. Disabled.');
            return;
        }

        // Setup routing
        this.setupNavigationInterceptor();
        window.addEventListener('popstate', (e) => this.handlePopState(e));

        // Setup WebSocket
        this.initWebSocket();

        // Setup Keyboard Shortcuts
        this.setupShortcuts();

        // Listen for system motion preferences
        window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {
            this.state.reducedMotion = e.matches;
            document.dispatchEvent(new CustomEvent('agrofedly:motion:change', { detail: { reducedMotion: e.matches } }));
        });

        // Engine initialized
    }

    setupNavigationInterceptor() {
        document.body.addEventListener('click', (e) => {
            // Find closest anchor tag
            const a = e.target.closest('a');
            if (!a || !a.href) return;

            // Check if link should be handled
            const url = new URL(a.href);
            const isLocal = url.origin === window.location.origin;
            const isTargetBlank = a.target === '_blank';
            const hasDownload = a.hasAttribute('download');
            const isNoPjax = a.hasAttribute('data-no-pjax');
            const isHash = a.getAttribute('href').startsWith('#');

            if (isLocal && !isTargetBlank && !hasDownload && !isNoPjax && !isHash) {
                // Allow specific extensions to pass through normally
                const ext = url.pathname.split('.').pop().toLowerCase();
                if (['pdf', 'jpg', 'png', 'zip', 'csv'].includes(ext)) return;

                e.preventDefault();
                
                this.navigateTo(url.pathname + url.search);
            }
        });
    }

    async navigateTo(url, pushState = true) {
        if (this.isTransitioning || url === window.location.pathname + window.location.search) return;
        this.isTransitioning = true;
        this.state.loading = true;

        // Emit leaving event (3D engine / Voice can react)
        document.dispatchEvent(new CustomEvent('agrofedly:page:leave', { detail: { nextUrl: url } }));

        try {
            // 1. Start out-transition
            if (!this.state.reducedMotion) {
                this.mainElement.classList.add('page-exit');
                await this.wait(300); // Wait for fade-out
            }

            // 2. Fetch new content
            const html = await this.fetchPage(url);
            
            // 3. Parse HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newMain = doc.querySelector('main');
            
            if (!newMain) {
                throw new Error("No <main> tag found in response.");
            }

            // 4. Update History
            if (pushState) {
                history.pushState({ url }, doc.title, url);
            }
            document.title = doc.title;

            // 5. Replace Content
            this.mainElement.innerHTML = newMain.innerHTML;
            
            // 6. Execute Scripts
            this.executeScripts(this.mainElement);
            
            // Trigger DOMContentLoaded for new scripts that bind to it
            document.dispatchEvent(new Event("DOMContentLoaded"));

            // 7. Start in-transition
            window.scrollTo({ top: 0, behavior: this.state.reducedMotion ? 'auto' : 'smooth' });
            
            if (!this.state.reducedMotion) {
                this.mainElement.classList.remove('page-exit');
                this.mainElement.classList.add('page-enter');
                
                // Force reflow
                void this.mainElement.offsetWidth;
                
                this.mainElement.classList.remove('page-enter');
                this.mainElement.classList.add('page-enter-active');
                
                await this.wait(400); // Wait for fade-in
                this.mainElement.classList.remove('page-enter-active');
            }

            // Emit enter event
            document.dispatchEvent(new CustomEvent('agrofedly:page:enter', { detail: { url } }));

            // Re-trigger scroll animations (Motion UI)
            this.reinitMotionUI();

        } catch (error) {
            console.error('[ExperienceManager] Navigation failed:', error);
            // Fallback to standard navigation
            window.location.href = url;
        } finally {
            this.isTransitioning = false;
            this.state.loading = false;
        }
    }

    async fetchPage(url) {
        // Optional: Implement caching for instantaneous back/forward
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest', // Helps Django identify AJAX
                'Accept': 'text/html'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.text();
    }

    handlePopState(e) {
        if (e.state && e.state.url) {
            this.navigateTo(e.state.url, false);
        } else {
            this.navigateTo(window.location.pathname + window.location.search, false);
        }
    }

    executeScripts(container) {
        const scripts = container.querySelectorAll('script');
        scripts.forEach(oldScript => {
            const newScript = document.createElement('script');
            Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
            
            // Do not re-execute module scripts that define global classes (they are already in memory)
            if (oldScript.type === 'module') {
                 // Actually, scene specific modules inside <main> need to run.
                 // We'll let them run. For custom modules, the browser handles it.
            }

            newScript.appendChild(document.createTextNode(oldScript.innerHTML));
            oldScript.parentNode.replaceChild(newScript, oldScript);
        });
    }

    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    setupShortcuts() {
        document.addEventListener('keydown', (e) => {
            // 'Ctrl/Cmd + K' -> Global Search
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                this.openGlobalSearch();
                return;
            }

            // Ignore if typing in an input for single-key shortcuts
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) || e.target.isContentEditable) {
                return;
            }

            // '/' -> Global Search
            if (e.key === '/') {
                e.preventDefault();
                this.openGlobalSearch();
            }

            // 'v' or 'V' -> Voice Assistant
            if (e.key.toLowerCase() === 'v') {
                e.preventDefault();
                const voiceBtn = document.getElementById('copilot-voice-btn');
                if (voiceBtn) {
                    // Simulate holding the voice button
                    const downEvent = new MouseEvent('mousedown');
                    voiceBtn.dispatchEvent(downEvent);
                    
                    // Add a keyup listener to release
                    const onKeyUp = (kuEvent) => {
                        if (kuEvent.key.toLowerCase() === 'v') {
                            const upEvent = new MouseEvent('mouseup');
                            voiceBtn.dispatchEvent(upEvent);
                            document.removeEventListener('keyup', onKeyUp);
                        }
                    };
                    document.addEventListener('keyup', onKeyUp);
                }
            }
            
            // 'Escape' -> Close modals/search
            if (e.key === 'Escape') {
                this.closeGlobalSearch();
            }
        });
    }

    openGlobalSearch() {
        const modal = document.getElementById('global-search-modal');
        if (modal) {
            modal.classList.add('active');
            const input = modal.querySelector('input');
            if (input) {
                setTimeout(() => input.focus(), 100);
                
                // Bind input event if not already bound
                if (!input.dataset.bound) {
                    let debounceTimer;
                    input.addEventListener('input', (e) => {
                        clearTimeout(debounceTimer);
                        debounceTimer = setTimeout(async () => {
                            const query = e.target.value.trim();
                            const resultsContainer = modal.querySelector('.search-results');
                            if (!query) {
                                resultsContainer.innerHTML = '<div class="search-category">Quick Links</div><a href="/surplus/">▣ Food Surplus</a><a href="/deliveries/">📦 Deliveries</a><a href="/intelligence/">⌁ AI Operations Center</a><a href="/agriculture/">🌾 Agri Command</a><a href="/organization/impact/">🌍 Impact Dashboard</a><a href="/predict/">📈 ML Forecast</a>';
                                return;
                            }
                            
                            try {
                                const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
                                const data = await response.json();
                                
                                if (data.results && data.results.length > 0) {
                                    let html = '<div class="search-category">Results</div>';
                                    data.results.forEach(item => {
                                        html += `
                                            <a href="${item.url}" class="search-result-item" style="display:flex; justify-content:space-between; align-items:center;">
                                                <span>${item.icon} ${item.title}</span>
                                                <small style="color:var(--color-text-secondary);">${item.subtitle}</small>
                                            </a>
                                        `;
                                    });
                                    resultsContainer.innerHTML = html;
                                } else {
                                    resultsContainer.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--color-text-secondary);">No results found.</div>';
                                }
                            } catch (error) {
                                console.error('Search error:', error);
                            }
                        }, 300);
                    });
                    input.dataset.bound = "true";
                }
            }
        }
    }

    closeGlobalSearch() {
        const modal = document.getElementById('global-search-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    reinitMotionUI() {
        // Re-run the Motion UI observer from app.js on new elements
        const elementsToAnimate = document.querySelectorAll('.feature-card, .form-card, .stat-card, .delivery-card, .panel, .live-card, .orbit, .page-head h1');
        elementsToAnimate.forEach((el, index) => {
            el.classList.add('reveal');
            el.style.transitionDelay = `${(index % 10) * 0.05}s`;
        });

        const observerOptions = { root: null, rootMargin: '0px', threshold: 0.1 };
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    obs.unobserve(entry.target);
                }
            });
        }, observerOptions);

        document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.message && data.message.type) {
                    this.showToast(data.message.title, data.message.message, data.message.type);
                    
                    // Specific event handling
                    if (data.message.type === 'SURPLUS_CREATED' || data.message.type === 'DELIVERY_STATUS_CHANGED') {
                        // Optimistically update some counters or triggers if they exist on the page
                        const surplusBadge = document.querySelector('.metric-card[data-metric="surplus"] .value');
                        if (surplusBadge && data.message.type === 'SURPLUS_CREATED') {
                            // In a real app we'd parse the number, for demo we just trigger a flash animation
                            surplusBadge.classList.add('flash');
                            setTimeout(() => surplusBadge.classList.remove('flash'), 1000);
                        }
                    }
                }
            } catch (err) {
                console.error("WS Parse Error:", err);
            }
        };

        this.ws.onclose = (e) => {
            // Socket closed, retrying in 5s
            setTimeout(() => this.initWebSocket(), 5000);
        };
    }

    showToast(title, message, type = 'info') {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type.toLowerCase().split('_')[0]} fade-in`;
        
        let icon = 'ℹ️';
        if (type.includes('CREATE') || type === 'success') icon = '✅';
        if (type.includes('UPDATE') || type === 'info') icon = '🔄';
        if (type.includes('ALERT') || type === 'error') icon = '⚠️';
        
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                <strong>${title}</strong>
                <p>${message}</p>
            </div>
            <button class="toast-close">&times;</button>
        `;
        
        toastContainer.appendChild(toast);
        
        toast.querySelector('.toast-close').onclick = () => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        };
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
}
