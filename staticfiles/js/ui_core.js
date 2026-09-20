// ui_core.js - Phase 7 Global UI Utilities (Toasts, Modals, Loading)

class UICore {
    constructor() {
        this.initToastContainer();
        this.initConfirmModal();
    }

    initToastContainer() {
        this.toastContainer = document.querySelector('.messages');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.className = 'messages';
            document.body.appendChild(this.toastContainer);
        }
    }

    initConfirmModal() {
        // Create the global confirm modal HTML
        const modalHtml = `
            <div id="global-confirm-modal" class="search-modal" style="z-index: 2000;">
                <div class="search-modal-content" style="max-width: 400px; text-align: center; padding: 24px;">
                    <h3 id="confirm-modal-title" style="margin-top: 0;">Confirm Action</h3>
                    <p id="confirm-modal-message" style="color: var(--color-text-secondary); font-size: 14px; margin-bottom: 24px;">Are you sure?</p>
                    <div style="display: flex; gap: 12px; justify-content: center;">
                        <button id="confirm-modal-cancel" class="btn glass" style="flex: 1;">Cancel</button>
                        <button id="confirm-modal-proceed" class="btn primary danger" style="flex: 1;">Proceed</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        this.confirmModal = document.getElementById('global-confirm-modal');
        this.confirmTitle = document.getElementById('confirm-modal-title');
        this.confirmMessage = document.getElementById('confirm-modal-message');
        this.cancelBtn = document.getElementById('confirm-modal-cancel');
        this.proceedBtn = document.getElementById('confirm-modal-proceed');

        this.cancelBtn.addEventListener('click', () => {
            this.closeConfirmModal();
            if (this.onCancelCallback) this.onCancelCallback();
        });

        this.proceedBtn.addEventListener('click', () => {
            this.closeConfirmModal();
            if (this.onProceedCallback) this.onProceedCallback();
        });
    }

    showToast(message, type = 'info') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${type}`;
        
        // Add icons based on type
        const icon = type === 'success' ? '✓ ' : type === 'error' ? '⚠ ' : 'ℹ ';
        msgDiv.innerText = icon + message;
        
        // Setup entrance animation
        msgDiv.style.opacity = '0';
        msgDiv.style.transform = 'translateY(-10px)';
        msgDiv.style.transition = 'all 0.3s ease';
        
        this.toastContainer.appendChild(msgDiv);
        
        // Trigger reflow
        msgDiv.offsetHeight;
        
        msgDiv.style.opacity = '1';
        msgDiv.style.transform = 'translateY(0)';
        
        setTimeout(() => {
            msgDiv.style.opacity = '0';
            msgDiv.style.transform = 'translateY(-10px)';
            setTimeout(() => msgDiv.remove(), 300);
        }, 5000);
    }

    showConfirm(title, message, onProceed, onCancel = null) {
        this.confirmTitle.innerText = title;
        this.confirmMessage.innerText = message;
        this.onProceedCallback = onProceed;
        this.onCancelCallback = onCancel;
        this.confirmModal.classList.add('active');
    }

    closeConfirmModal() {
        this.confirmModal.classList.remove('active');
    }

    setLoading(buttonElement, isLoading, originalText = '') {
        if (isLoading) {
            buttonElement.disabled = true;
            buttonElement.classList.add('loading');
            buttonElement.dataset.originalText = buttonElement.innerText;
            buttonElement.innerText = 'Processing...';
        } else {
            buttonElement.disabled = false;
            buttonElement.classList.remove('loading');
            buttonElement.innerText = originalText || buttonElement.dataset.originalText;
        }
    }
}

// Auto-initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.ui = new UICore();
});
