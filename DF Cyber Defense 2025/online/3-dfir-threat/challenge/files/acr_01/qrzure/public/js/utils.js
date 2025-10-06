// Core utilities module
const Utils = {
    // Loading state management
    showLoading() {
        document.getElementById('loading').style.display = 'flex';
    },

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    },

    // Toast notification system
    showToast(message, type = 'error', duration = 5000) {
        const toastContainer = document.getElementById('toast-container');

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const closeBtn = document.createElement('span');
        closeBtn.className = 'toast-close';
        closeBtn.innerHTML = '&times;';
        
        const messageDiv = document.createElement('div');
        messageDiv.textContent = message;
        
        toast.appendChild(closeBtn);
        toast.appendChild(messageDiv);

        closeBtn.addEventListener('click', () => {
            this.removeToast(toast);
        });
        
        toast.addEventListener('click', (e) => {
            if (e.target !== closeBtn) {
                this.removeToast(toast);
            }
        });

        toastContainer.appendChild(toast);

        setTimeout(() => {
            this.removeToast(toast);
        }, duration);

        return toast;
    },

    removeToast(toast) {
        if (toast && toast.parentNode) {
            toast.classList.add('hiding');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    },

    showError(message) {
        this.showToast(message, 'error');
        this.hideLoading();
    },

    showSuccess(message) {
        this.showToast(message, 'success', 3000);
    },

    // Helper functions
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },

    isValidImageUrl(url) {
        try {
            new URL(url);
            return /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(url);
        } catch {
            return false;
        }
    },

    validateUrl(imageUrl) {
        try {
            const url = new URL(imageUrl);
            if (!['http:', 'https:'].includes(url.protocol)) {
                return { valid: false, error: 'Please enter a valid HTTP/HTTPS URL' };
            }
            return { valid: true };
        } catch {
            return { valid: false, error: 'Please enter a valid URL' };
        }
    }
};

window.Utils = Utils;