// AgroFedly Base UI interactions

(function() {
    const initUI = () => {
        const drawer = document.getElementById("drawer");
        const backdrop = document.getElementById("backdrop");
        const menuBtn = document.getElementById("menuBtn");
        const closeMenuBtn = document.getElementById("closeMenu");

        const openDrawer = () => {
            if(drawer) drawer.classList.add("open");
            if(backdrop) backdrop.classList.add("show");
        };

        const closeDrawer = () => {
            if(drawer) drawer.classList.remove("open");
            if(backdrop) backdrop.classList.remove("show");
        };
        
        if (menuBtn) {
            // Remove old listener to avoid duplicates if re-injected
            menuBtn.removeEventListener("click", openDrawer);
            menuBtn.addEventListener("click", openDrawer);
        }
        
        if (closeMenuBtn) {
            closeMenuBtn.removeEventListener("click", closeDrawer);
            closeMenuBtn.addEventListener("click", closeDrawer);
        }
        
        if (backdrop) {
            backdrop.removeEventListener("click", closeDrawer);
            backdrop.addEventListener("click", closeDrawer);
        }

        const searchModal = document.getElementById("global-search-modal");
        const searchInput = document.getElementById("global-search-input");
        
        const closeSearch = () => {
            if(searchModal) searchModal.classList.remove("active");
        };

        document.addEventListener("keydown", e => {
            if (e.key === "Escape") {
                closeDrawer();
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
