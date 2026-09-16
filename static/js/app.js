// AgroFedly Base UI interactions

(function() {
    const initUI = () => {
        const searchModal = document.getElementById("global-search-modal");
        const searchInput = document.getElementById("global-search-input");
        
        const closeSearch = () => {
            if(searchModal) searchModal.classList.remove("active");
        };

        document.addEventListener("keydown", e => {
            if (e.key === "Escape") {
                closeSearch();
            }
            if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
                e.preventDefault();
                if(searchModal) {
                    searchModal.classList.add("active");
                    if(searchInput) setTimeout(() => searchInput.focus(), 100);
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
