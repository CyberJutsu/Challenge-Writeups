// Main application entry point with lazy loading
document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI Tabs system with lazy loading
    if (window.UITabs) {
        UITabs.initialize();
    } else {
        // Fallback: load UI tabs module
        const script = document.createElement('script');
        script.src = 'js/ui-tabs.js';
        script.onload = () => {
            if (window.UITabs) {
                UITabs.initialize();
            }
        };
        script.onerror = () => {
            console.error('Failed to load UI tabs module');
        };
        document.head.appendChild(script);
    }
});