// UI Tab management module
const UITabs = {
    currentTab: 'generate',
    currentScanTab: 'upload',

    switchTab(tabName) {
        // Validate tabName to prevent injection
        if (!/^[a-zA-Z0-9_-]+$/.test(tabName)) {
            console.error('Invalid tab name:', tabName);
            return;
        }
        
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            if (btn.onclick && btn.onclick.toString().includes(`switchTab('${tabName}')`)) {
                btn.classList.add('active');
            }
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const targetTab = document.getElementById(tabName + '-tab');
        if (targetTab) {
            targetTab.classList.add('active');
            this.currentTab = tabName;
            
            // Lazy load tab-specific functionality
            this.loadTabModule(tabName);
        }
    },

    switchScanTab(scanTabName) {
        // Validate scanTabName to prevent injection
        if (!/^[a-zA-Z0-9_-]+$/.test(scanTabName)) {
            console.error('Invalid scan tab name:', scanTabName);
            return;
        }
        
        // Update scan tab buttons
        document.querySelectorAll('.scan-tab-button').forEach(btn => {
            btn.classList.remove('active');
            if (btn.onclick && btn.onclick.toString().includes(`switchScanTab('${scanTabName}')`)) {
                btn.classList.add('active');
            }
        });

        // Update scan tab content
        document.querySelectorAll('.scan-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const targetTab = document.getElementById('scan-' + scanTabName + '-tab');
        if (targetTab) {
            targetTab.classList.add('active');
            this.currentScanTab = scanTabName;
        }
    },

    async loadTabModule(tabName) {
        try {
            switch(tabName) {
                case 'generate':
                    if (!window.QRGenerator) {
                        await this.loadScript('js/qr-generator.js');
                    }
                    if (window.QRGenerator) {
                        QRGenerator.initializeForm();
                    }
                    break;
                case 'scan':
                    if (!window.QRScanner) {
                        await this.loadScript('js/qr-scanner.js');
                    }
                    if (window.QRScanner) {
                        QRScanner.initializeFileUpload();
                        QRScanner.initializeUrlScan();
                    }
                    break;
            }
        } catch (error) {
            console.error('Error loading module for tab:', tabName, error);
        }
    },

    loadScript(src) {
        return new Promise((resolve, reject) => {
            // Check if script is already loaded
            if (document.querySelector(`script[src="${src}"]`)) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    },

    initialize() {
        // Load utilities first (always needed)
        this.loadScript('js/utils.js').then(() => {
            // Initialize the default tab
            this.loadTabModule(this.currentTab);
        }).catch(error => {
            console.error('Error loading utilities:', error);
        });
    }
};

// Make functions globally available for HTML onclick handlers
window.switchTab = (tabName) => UITabs.switchTab(tabName);
window.switchScanTab = (scanTabName) => UITabs.switchScanTab(scanTabName);

window.UITabs = UITabs;