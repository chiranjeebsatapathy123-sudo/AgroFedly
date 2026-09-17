// AgroFedly Base UI interactions

(function() {
    const initUI = () => {
        const searchInput = document.querySelector(".rd-search input");

        document.addEventListener("keydown", e => {
            if (e.key === "Escape") {
                if(document.activeElement === searchInput) {
                    searchInput.blur();
                }
            }
            if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
                e.preventDefault();
                if(searchInput) {
                    searchInput.focus();
                }
            }
        });
        
        // Auto remove messages
        setTimeout(() => document.querySelectorAll(".message").forEach(x => {
            x.style.opacity = '0';
            setTimeout(() => x.remove(), 300);
        }), 5000);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUI);
    } else {
        initUI();
    }
})();

// Dark Theme Persistence for Redesign
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('agro_theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
    
    const themeBtn = document.querySelector('.rd-top-actions .fa-sun')?.parentElement;
    if (themeBtn) {
        // Remove the inline onclick attribute
        themeBtn.removeAttribute('onclick');
        themeBtn.addEventListener('click', () => {
            document.body.classList.toggle('dark-theme');
            const isDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('agro_theme', isDark ? 'dark' : 'light');
        });
    }
});
