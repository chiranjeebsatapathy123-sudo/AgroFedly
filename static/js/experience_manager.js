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

        // Setup Keyboard Shortcuts
        this.setupShortcuts();

        // Listen for system motion preferences
        window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {
            this.state.reducedMotion = e.matches;
            document.dispatchEvent(new CustomEvent('agrofedly:motion:change', { detail: { reducedMotion: e.matches } }));
        });

        console.log('[ExperienceManager] Initialized.');
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
                
                // Close navigation drawer if it's open
                const drawer = document.getElementById('drawer');
                if (drawer && drawer.classList.contains('open')) {
                    drawer.classList.remove('open');
                    const backdrop = document.getElementById('backdrop');
                    if (backdrop) backdrop.classList.remove('show');
                }

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
            // Ignore if typing in an input
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
            if (input) setTimeout(() => input.focus(), 100);
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
}
