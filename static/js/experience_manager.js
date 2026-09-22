javascript
/**
 * AgroFedly Experience Manager
 *
 * Handles:
 * - Global interaction states
 * - Keyboard shortcuts
 * - Global search
 * - WebSocket notifications
 * - Toast notifications
 * - Motion/reveal animations
 *
 * IMPORTANT:
 * Normal Django/browser navigation is intentionally used.
 * We do NOT intercept normal <a> links or manipulate browser history.
 * This keeps Back/Forward buttons working correctly.
 */

export class ExperienceManager {
    constructor() {
        this.mainElement = document.querySelector('main');
        this.isTransitioning = false;

        // State
        this.state = {
            loading: false,
            reducedMotion: window.matchMedia(
                '(prefers-reduced-motion: reduce)'
            ).matches
        };

        this.ws = null;
        this.wsRetryTimer = null;

        this.init();
    }

    init() {
        if (!this.mainElement) {
            console.error(
                '[ExperienceManager] <main> element not found. Disabled.'
            );
            return;
        }

        /*
         * IMPORTANT:
         *
         * Do NOT intercept normal navigation.
         *
         * Django will handle:
         *     /login/
         *     /explore/
         *     /dashboard/
         *     /agriculture/
         *     etc.
         *
         * The browser will therefore handle:
         *     Back
         *     Forward
         *     Refresh
         *
         * correctly.
         */

        // Intentionally disabled:
        // this.setupNavigationInterceptor();
        // window.addEventListener('popstate', ...);

        // Setup WebSocket
        this.initWebSocket();

        // Setup keyboard shortcuts
        this.setupShortcuts();

        // Listen for system motion preferences
        const motionQuery = window.matchMedia(
            '(prefers-reduced-motion: reduce)'
        );

        motionQuery.addEventListener('change', (e) => {
            this.state.reducedMotion = e.matches;

            document.dispatchEvent(
                new CustomEvent('agrofedly:motion:change', {
                    detail: {
                        reducedMotion: e.matches
                    }
                })
            );
        });

        // Engine initialized
        console.log(
            '[ExperienceManager] Initialized with standard browser navigation.'
        );
    }

    /*
     * ---------------------------------------------------------
     * NAVIGATION
     * ---------------------------------------------------------
     *
     * These functions are intentionally kept available in case
     * another part of the project calls them, but normal links
     * are NOT intercepted anymore.
     */

    setupNavigationInterceptor() {
        // Intentionally disabled.
        //
        // Do not use preventDefault() on normal Django links.
        //
        // This prevents problems with browser Back/Forward history.
    }

    async navigateTo(url, pushState = true) {
        /*
         * Standard navigation.
         *
         * Instead of fetching the page and replacing only <main>,
         * allow Django/browser to load the complete page.
         */

        if (!url) {
            return;
        }

        window.location.href = url;
    }

    async fetchPage(url) {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'text/html'
            }
        });

        if (!response.ok) {
            throw new Error(
                `HTTP error! status: ${response.status}`
            );
        }

        return await response.text();
    }

    handlePopState(e) {
        /*
         * Browser handles Back/Forward naturally.
         *
         * We intentionally do nothing here.
         */
    }

    executeScripts(container) {
        /*
         * Kept for compatibility with the old ExperienceManager.
         *
         * Normal Django page loads execute scripts naturally, so
         * this method is not required for normal navigation.
         */

        if (!container) {
            return;
        }

        const scripts = container.querySelectorAll('script');

        scripts.forEach((oldScript) => {
            const newScript = document.createElement('script');

            Array.from(oldScript.attributes).forEach((attr) => {
                newScript.setAttribute(attr.name, attr.value);
            });

            if (oldScript.textContent) {
                newScript.textContent = oldScript.textContent;
            }

            oldScript.parentNode.replaceChild(
                newScript,
                oldScript
            );
        });
    }

    wait(ms) {
        return new Promise((resolve) => {
            setTimeout(resolve, ms);
        });
    }

    /*
     * ---------------------------------------------------------
     * KEYBOARD SHORTCUTS
     * ---------------------------------------------------------
     */

    setupShortcuts() {
        document.addEventListener('keydown', (e) => {

            // Ctrl/Cmd + K → Global Search
            if (
                (e.ctrlKey || e.metaKey) &&
                e.key.toLowerCase() === 'k'
            ) {
                e.preventDefault();
                this.openGlobalSearch();
                return;
            }

            // Ignore single-key shortcuts while typing
            if (
                ['INPUT', 'TEXTAREA', 'SELECT'].includes(
                    e.target.tagName
                ) ||
                e.target.isContentEditable
            ) {
                return;
            }

            // "/" → Global Search
            if (e.key === '/') {
                e.preventDefault();
                this.openGlobalSearch();
                return;
            }

            // "V" → Voice Assistant
            if (e.key.toLowerCase() === 'v') {
                e.preventDefault();

                const voiceBtn =
                    document.getElementById('copilot-voice-btn');

                if (voiceBtn) {
                    const downEvent = new MouseEvent('mousedown');
                    voiceBtn.dispatchEvent(downEvent);

                    const onKeyUp = (kuEvent) => {
                        if (kuEvent.key.toLowerCase() === 'v') {
                            const upEvent = new MouseEvent('mouseup');

                            voiceBtn.dispatchEvent(upEvent);

                            document.removeEventListener(
                                'keyup',
                                onKeyUp
                            );
                        }
                    };

                    document.addEventListener(
                        'keyup',
                        onKeyUp
                    );
                }

                return;
            }

            // Escape → Close search/modal
            if (e.key === 'Escape') {
                this.closeGlobalSearch();
            }
        });
    }

    /*
     * ---------------------------------------------------------
     * GLOBAL SEARCH
     * ---------------------------------------------------------
     */

    openGlobalSearch() {
        const modal =
            document.getElementById('global-search-modal');

        if (!modal) {
            return;
        }

        modal.classList.add('active');

        const input = modal.querySelector('input');

        if (!input) {
            return;
        }

        setTimeout(() => {
            input.focus();
        }, 100);

        // Prevent duplicate event listeners
        if (input.dataset.bound === 'true') {
            return;
        }

        let debounceTimer;

        input.addEventListener('input', (e) => {

            clearTimeout(debounceTimer);

            debounceTimer = setTimeout(async () => {

                const query =
                    e.target.value.trim();

                const resultsContainer =
                    modal.querySelector(
                        '.search-results'
                    );

                if (!resultsContainer) {
                    return;
                }

                // Empty search → Quick Links
                if (!query) {
                    resultsContainer.innerHTML = `
                        <div class="search-category">
                            Quick Links
                        </div>

                        <a href="/surplus/">
                            ▣ Food Surplus
                        </a>

                        <a href="/deliveries/">
                            📦 Deliveries
                        </a>

                        <a href="/intelligence/">
                            ⌁ AI Operations Center
                        </a>

                        <a href="/agriculture/">
                            🌾 Agri Command
                        </a>

                        <a href="/organization/impact/">
                            🌍 Impact Dashboard
                        </a>

                        <a href="/predict/">
                            📈 ML Forecast
                        </a>
                    `;

                    return;
                }

                try {
                    const response = await fetch(
                        `/api/search/?q=${encodeURIComponent(query)}`
                    );

                    if (!response.ok) {
                        throw new Error(
                            `Search HTTP error: ${response.status}`
                        );
                    }

                    const data = await response.json();

                    if (
                        data.results &&
                        data.results.length > 0
                    ) {
                        let html = `
                            <div class="search-category">
                                Results
                            </div>
                        `;

                        data.results.forEach((item) => {
                            html += `
                                <a
                                    href="${item.url}"
                                    class="search-result-item"
                                    style="
                                        display:flex;
                                        justify-content:space-between;
                                        align-items:center;
                                    "
                                >
                                    <span>
                                        ${item.icon}
                                        ${item.title}
                                    </span>

                                    <small
                                        style="
                                            color:
                                            var(
                                                --color-text-secondary
                                            );
                                        "
                                    >
                                        ${item.subtitle}
                                    </small>
                                </a>
                            `;
                        });

                        resultsContainer.innerHTML = html;

                    } else {

                        resultsContainer.innerHTML = `
                            <div
                                style="
                                    padding:1rem;
                                    text-align:center;
                                    color:
                                    var(
                                        --color-text-secondary
                                    );
                                "
                            >
                                No results found.
                            </div>
                        `;
                    }

                } catch (error) {
                    console.error(
                        '[ExperienceManager] Search error:',
                        error
                    );

                    resultsContainer.innerHTML = `
                        <div
                            style="
                                padding:1rem;
                                text-align:center;
                            "
                        >
                            Search temporarily unavailable.
                        </div>
                    `;
                }

            }, 300);
        });

        input.dataset.bound = 'true';
    }

    closeGlobalSearch() {
        const modal =
            document.getElementById('global-search-modal');

        if (modal) {
            modal.classList.remove('active');
        }
    }

    /*
     * ---------------------------------------------------------
     * MOTION UI
     * ---------------------------------------------------------
     */

    reinitMotionUI() {
        const elementsToAnimate =
            document.querySelectorAll(
                '.feature-card, ' +
                '.form-card, ' +
                '.stat-card, ' +
                '.delivery-card, ' +
                '.panel, ' +
                '.live-card, ' +
                '.orbit, ' +
                '.page-head h1'
            );

        elementsToAnimate.forEach((el, index) => {
            el.classList.add('reveal');

            el.style.transitionDelay =
                `${(index % 10) * 0.05}s`;
        });

        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };

        const observer =
            new IntersectionObserver(
                (entries, obs) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add(
                                'active'
                            );

                            obs.unobserve(entry.target);
                        }
                    });
                },
                observerOptions
            );

        document
            .querySelectorAll('.reveal')
            .forEach((el) => {
                observer.observe(el);
            });
    }

    /*
     * ---------------------------------------------------------
     * WEBSOCKET
     * ---------------------------------------------------------
     */

    initWebSocket() {
        // Close an existing socket before creating another
        if (
            this.ws &&
            (
                this.ws.readyState === WebSocket.OPEN ||
                this.ws.readyState === WebSocket.CONNECTING
            )
        ) {
            return;
        }

        const protocol =
            window.location.protocol === 'https:'
                ? 'wss:'
                : 'ws:';

        const wsUrl =
            `${protocol}//${window.location.host}` +
            `/ws/notifications/`;

        try {
            this.ws = new WebSocket(wsUrl);
        } catch (error) {
            console.error(
                '[ExperienceManager] WebSocket creation failed:',
                error
            );

            this.scheduleWebSocketRetry();
            return;
        }

        this.ws.onopen = () => {
            console.log(
                '[ExperienceManager] WebSocket connected.'
            );
        };

        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);

                if (
                    data.message &&
                    data.message.type
                ) {
                    this.showToast(
                        data.message.title,
                        data.message.message,
                        data.message.type
                    );

                    // Specific event handling
                    if (
                        data.message.type ===
                            'SURPLUS_CREATED' ||
                        data.message.type ===
                            'DELIVERY_STATUS_CHANGED'
                    ) {
                        const surplusBadge =
                            document.querySelector(
                                '.metric-card' +
                                '[data-metric="surplus"]' +
                                ' .value'
                            );

                        if (
                            surplusBadge &&
                            data.message.type ===
                                'SURPLUS_CREATED'
                        ) {
                            surplusBadge.classList.add(
                                'flash'
                            );

                            setTimeout(() => {
                                surplusBadge.classList.remove(
                                    'flash'
                                );
                            }, 1000);
                        }
                    }
                }

            } catch (err) {
                console.error(
                    '[ExperienceManager] WebSocket parse error:',
                    err
                );
            }
        };

        this.ws.onerror = (error) => {
            console.error(
                '[ExperienceManager] WebSocket error:',
                error
            );
        };

        this.ws.onclose = () => {
            this.ws = null;

            this.scheduleWebSocketRetry();
        };
    }

    scheduleWebSocketRetry() {
        if (this.wsRetryTimer) {
            return;
        }

        this.wsRetryTimer = setTimeout(() => {
            this.wsRetryTimer = null;
            this.initWebSocket();
        }, 5000);
    }

    /*
     * ---------------------------------------------------------
     * TOAST NOTIFICATIONS
     * ---------------------------------------------------------
     */

    showToast(title, message, type = 'info') {

        const toastContainer =
            document.getElementById(
                'toast-container'
            ) ||
            this.createToastContainer();

        const toast =
            document.createElement('div');

        toast.className =
            `toast toast-${
                type.toLowerCase().split('_')[0]
            } fade-in`;

        let icon = 'ℹ️';

        if (
            type.includes('CREATE') ||
            type === 'success'
        ) {
            icon = '✅';
        }

        if (
            type.includes('UPDATE') ||
            type === 'info'
        ) {
            icon = '🔄';
        }

        if (
            type.includes('ALERT') ||
            type === 'error'
        ) {
            icon = '⚠️';
        }

        toast.innerHTML = `
            <div class="toast-icon">
                ${icon}
            </div>

            <div class="toast-content">
                <strong>
                    ${title || ''}
                </strong>

                <p>
                    ${message || ''}
                </p>
            </div>

            <button
                class="toast-close"
                type="button"
                aria-label="Close notification"
            >
                &times;
            </button>
        `;

        toastContainer.appendChild(toast);

        const closeButton =
            toast.querySelector('.toast-close');

        if (closeButton) {
            closeButton.onclick = () => {
                toast.classList.add('fade-out');

                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.remove();
                    }
                }, 300);
            };
        }

        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('fade-out');

                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.remove();
                    }
                }, 300);
            }
        }, 5000);
    }

    createToastContainer() {
        const container =
            document.createElement('div');

        container.id = 'toast-container';
        container.className =
            'toast-container';

        document.body.appendChild(container);

        return container;
    }
}

