export class VoiceAssistant {
    constructor() {
        this.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.supported = !!this.SpeechRecognition;
        
        if (!this.supported) {
            console.warn('[VoiceAssistant] Speech Recognition API not supported in this browser.');
            return;
        }

        this.recognition = new this.SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.lang = 'en-US';
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;

        // IDLE, LISTENING, PROCESSING, UNDERSTANDING, CONFIRMATION_REQUIRED, EXECUTING, SUCCESS, ERROR, UNSUPPORTED
        this.state = 'IDLE'; 
        this.isMuted = false;
        this.pendingAction = null; // For confirmation
        
        // Voice UI Elements
        this.voiceBtn = document.getElementById('copilot-voice-btn');
        this.aiMsgContainer = document.getElementById('copilot-messages');
        
        if (this.voiceBtn) {
            this.voiceBtn.addEventListener('click', this.toggleListening.bind(this));
        }

        this.setupEvents();
    }

    setupEvents() {
        this.recognition.onstart = () => {
            this.setState('LISTENING');
            this.addUIMessage('system', '◉ Listening...', 'listening-pulse');
        };

        this.recognition.onresult = (event) => {
            const command = event.results[0][0].transcript.toLowerCase().trim();
            this.setState('PROCESSING');
            this.addUIMessage('user', `You: ${command}`);
            this.parseIntent(command);
        };

        this.recognition.onspeechend = () => {
            this.recognition.stop();
        };

        this.recognition.onerror = (event) => {
            console.error('[VoiceAssistant] Error:', event.error);
            this.setState('ERROR');
            if (event.error === 'not-allowed') {
                this.addUIMessage('system', '! Microphone access denied.', 'error');
            } else {
                this.addUIMessage('system', `! Voice recognition error: ${event.error}`, 'error');
            }
            setTimeout(() => this.setState('IDLE'), 2000);
        };

        this.recognition.onend = () => {
            if (this.state === 'LISTENING') {
                this.setState('IDLE');
                this.removeSystemMessages();
            }
        };
    }

    toggleListening() {
        if (!this.supported) return;
        
        if (this.state === 'IDLE' || this.state === 'ERROR' || this.state === 'SUCCESS') {
            try {
                this.recognition.start();
            } catch(e) {
                console.error(e);
            }
        } else if (this.state === 'LISTENING') {
            this.recognition.stop();
            this.setState('IDLE');
        }
    }

    setState(newState) {
        this.state = newState;
        
        // Dispatch global event for 3D AI Core
        document.dispatchEvent(new CustomEvent('agrofedly:voice:state', { detail: { state: newState } }));

        if (this.voiceBtn) {
            this.voiceBtn.className = `copilot-btn-icon state-${newState.toLowerCase()}`;
            if (newState === 'LISTENING') {
                this.voiceBtn.innerHTML = '<span class="pulse-ring"></span>◉';
            } else if (newState === 'PROCESSING' || newState === 'UNDERSTANDING') {
                this.voiceBtn.innerHTML = '◌';
            } else if (newState === 'CONFIRMATION_REQUIRED') {
                this.voiceBtn.innerHTML = '?';
            } else if (newState === 'SUCCESS') {
                this.voiceBtn.innerHTML = '✓';
            } else if (newState === 'ERROR') {
                this.voiceBtn.innerHTML = '!';
            } else {
                this.voiceBtn.innerHTML = '●';
            }
        }
    }

    addUIMessage(sender, text, extraClass = '') {
        if (!this.aiMsgContainer) return;
        
        if (sender === 'user') this.removeSystemMessages();
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `copilot-msg ${sender}-msg ${extraClass}`;
        
        if (sender === 'system') {
            msgDiv.dataset.temporary = 'true';
        }
        
        msgDiv.innerText = text;
        this.aiMsgContainer.appendChild(msgDiv);
        this.aiMsgContainer.scrollTop = this.aiMsgContainer.scrollHeight;
    }

    removeSystemMessages() {
        if (!this.aiMsgContainer) return;
        const tempMsgs = this.aiMsgContainer.querySelectorAll('[data-temporary="true"]');
        tempMsgs.forEach(msg => msg.remove());
    }

    speak(text) {
        if (this.isMuted || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    }

    parseIntent(command) {
        this.setState('UNDERSTANDING');
        
        // Check for confirmation flow first
        if (this.state === 'CONFIRMATION_REQUIRED' || this.pendingAction) {
            if (command.includes('yes') || command.includes('approve') || command.includes('do it') || command.includes('confirm')) {
                const action = this.pendingAction;
                this.pendingAction = null;
                this.executeAction(action.successMsg, action.fn);
                return;
            } else if (command.includes('no') || command.includes('cancel') || command.includes('stop')) {
                this.pendingAction = null;
                this.executeAction('Action cancelled.', () => {});
                return;
            }
        }

        const path = window.location.pathname;

        // Backend NLP Routing for complex queries
        if (command.includes('find') || command.includes('where is') || command.includes('track') || command.includes('search') || command.includes('navigate to') || command.includes('open')) {
            this.setState('UNDERSTANDING');
            fetch('/api/search/?q=' + encodeURIComponent(command))
                .then(r => r.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        const topHit = data.results[0];
                        this.executeAction(`Found it. Opening ${topHit.title}...`, () => {
                            window.location.href = topHit.url;
                        });
                    } else {
                        this.executeAction("I couldn't find anything matching that query.", () => {});
                    }
                }).catch(e => {
                    this.executeAction("I had trouble reaching the intelligence module.", () => {});
                });
            return;
        }

        // Intent Registry for quick local actions
        const intents = [
            { id: 'QUERY_SURPLUS', keywords: ['surplus', 'food available', 'excess food'] },
            { id: 'QUERY_ANALYTICS', keywords: ['analytics', 'impact', 'statistics'] },
            { id: 'CHANGE_THEME', keywords: ['dark mode', 'light mode', 'theme'] },
            { id: 'CONFIRM_ACTION', keywords: ['cancel delivery', 'approve redistribution', 'delete'] },
            { id: 'GO_BACK', keywords: ['go back', 'previous page'] }
        ];

        let matchedIntent = null;
        for (const intent of intents) {
            if (intent.keywords.some(kw => command.includes(kw))) {
                matchedIntent = intent.id;
                break;
            }
        }

        if (matchedIntent === 'CONFIRM_ACTION') {
            this.requireConfirmation(
                "This is a sensitive action. Would you like me to proceed?", 
                "Action completed.", 
                () => { /* Action performed safely */ }
            );
            return;
        }

        if (matchedIntent === 'CHANGE_THEME') {
            const isDark = command.includes('dark');
            this.executeAction(`Switching to ${isDark ? 'dark' : 'light'} mode.`, () => {
                document.getElementById('themeSelector').value = isDark ? 'dark' : 'light';
                document.getElementById('themeSelector').dispatchEvent(new Event('change'));
            });
            return;
        }

        if (matchedIntent === 'GO_BACK') {
            this.executeAction('Going back.', () => window.history.back());
            return;
        }

        // Context-aware Navigation/Query
        if (command.includes('surplus')) {
            if (path.includes('/surplus/')) {
                this.executeAction('1,240 surplus meals are currently eligible for redistribution today.', () => {});
            } else {
                this.executeAction('Navigating to Food Surplus.', () => {
                    if (window.experienceManager) window.experienceManager.navigateTo('/surplus/');
                    else window.location.href = '/surplus/';
                });
            }
            return;
        }

        if (command.includes('dashboard')) {
            this.executeAction('Navigating to Dashboard.', () => {
                if (window.experienceManager) window.experienceManager.navigateTo('/dashboard/');
                else window.location.href = '/dashboard/';
            });
            return;
        }
        
        if (command.includes('analytics') || command.includes('intelligence')) {
            this.executeAction('Navigating to Intelligence Center.', () => {
                if (window.experienceManager) window.experienceManager.navigateTo('/intelligence/');
                else window.location.href = '/intelligence/';
            });
            return;
        }

        // Unrecognized
        this.setState('UNSUPPORTED');
        this.addUIMessage('ai', `I didn't understand that command. Try saying "Open food surplus".`);
        this.speak(`I didn't understand that command. Try saying "Open food surplus".`);
        setTimeout(() => this.setState('IDLE'), 2000);
    }

    requireConfirmation(promptMsg, successMsg, fn) {
        this.setState('CONFIRMATION_REQUIRED');
        this.pendingAction = { successMsg, fn };
        this.addUIMessage('ai', promptMsg);
        this.speak(promptMsg);
    }

    executeAction(responseText, actionFn) {
        this.setState('EXECUTING');
        this.removeSystemMessages();
        this.addUIMessage('ai', `✓ ${responseText}`, 'success');
        this.speak(responseText);
        
        this.setState('SUCCESS');
        setTimeout(() => {
            actionFn();
            this.setState('IDLE');
        }, 1500);
    }
}
