// QR Scanner module
const QRScanner = {
    async scan(imageData, isFile = true) {
        try {
            Utils.showLoading();
            
            const formData = new FormData();
            if (isFile) {
                formData.append('qrimage', imageData);
            } else {
                formData.append('imageUrl', imageData);
            }

            const response = await fetch(API_ENDPOINTS.SCAN, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Failed to scan QR code (${response.status})`);
            }

            const result = await response.json();
            this.displayResult(result);
            Utils.showSuccess('QR code scanned successfully!');

        } catch (error) {
            console.error('QR scan error:', error);
            Utils.showError(error.message || 'Failed to scan QR code');
        } finally {
            Utils.hideLoading();
        }
    },

    displayResult(result) {
        const container = document.getElementById('scan-result');
        if (!container) return;

        container.innerHTML = '';
        
        const h3 = document.createElement('h3');
        h3.textContent = 'QR Code Scanned Successfully';
        
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'scan-details';
        
        // Display structured data if available
        if (result.amount) {
            const amountP = document.createElement('p');
            amountP.innerHTML = '<strong>Amount:</strong> $';
            amountP.appendChild(document.createTextNode(result.amount));
            detailsDiv.appendChild(amountP);
        }
        
        if (result.recipient) {
            const recipientP = document.createElement('p');
            recipientP.innerHTML = '<strong>Recipient:</strong> ';
            recipientP.appendChild(document.createTextNode(result.recipient));
            detailsDiv.appendChild(recipientP);
        }
        
        if (result.message) {
            const messageP = document.createElement('p');
            messageP.innerHTML = '<strong>Message:</strong> ';
            messageP.appendChild(document.createTextNode(result.message));
            detailsDiv.appendChild(messageP);
        }
        
        if (result.scanMessage && result.scanMessage !== result.message) {
            const renderedP = document.createElement('p');
            renderedP.innerHTML = '<strong>Rendered Message:</strong> ';
            renderedP.appendChild(document.createTextNode(result.scanMessage));
            detailsDiv.appendChild(renderedP);
        }
        
        if (result.timestamp) {
            const timestampP = document.createElement('p');
            timestampP.innerHTML = '<strong>Generated:</strong> ';
            timestampP.appendChild(document.createTextNode(new Date(result.timestamp).toLocaleString()));
            detailsDiv.appendChild(timestampP);
        }
        
        
        container.appendChild(h3);
        container.appendChild(detailsDiv);

        container.style.display = 'block';
    },

    updateFileDropZone(file) {
        const dropZone = document.getElementById('dropZone');
        dropZone.innerHTML = '';
        
        const p = document.createElement('p');
        p.textContent = `Selected: ${file.name} (${Utils.formatFileSize(file.size)})`;
        dropZone.appendChild(p);
    },

    initializeFileUpload() {
        const form = document.getElementById('scanForm');
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('qrimage');

        if (!form || !dropZone || !fileInput || form.dataset.uploadInitialized) return;
        form.dataset.uploadInitialized = 'true';

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const file = fileInput.files[0];
            
            if (!file) {
                Utils.showError('Please select an image file');
                return;
            }
            
            if (!file.type.startsWith('image/')) {
                Utils.showError('Please select a valid image file');
                return;
            }
            
            this.scan(file, true);
        });

        dropZone.addEventListener('click', () => {
            fileInput.click();
        });

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                this.updateFileDropZone(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.updateFileDropZone(e.target.files[0]);
            }
        });
    },

    initializeUrlScan() {
        const form = document.getElementById('scanUrlForm');
        const imageUrlInput = document.getElementById('imageUrl');
        const urlPreview = document.getElementById('urlPreview');
        const urlPreviewImg = document.getElementById('urlPreviewImg');

        if (!form || !imageUrlInput || form.dataset.urlInitialized) return;
        form.dataset.urlInitialized = 'true';

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const imageUrl = imageUrlInput.value.trim();
            
            if (!imageUrl) {
                Utils.showError('Please enter an image URL');
                return;
            }
            
            const validation = Utils.validateUrl(imageUrl);
            if (!validation.valid) {
                Utils.showError(validation.error);
                return;
            }
            
            this.scan(imageUrl, false);
        });

        if (urlPreview && urlPreviewImg && !imageUrlInput.dataset.previewInitialized) {
            imageUrlInput.dataset.previewInitialized = 'true';
            imageUrlInput.addEventListener('input', (e) => {
                const url = e.target.value;
                if (url && Utils.isValidImageUrl(url)) {
                    urlPreviewImg.src = url;
                    urlPreview.style.display = 'block';
                    
                    urlPreviewImg.onerror = function() {
                        urlPreview.style.display = 'none';
                    };
                } else {
                    urlPreview.style.display = 'none';
                }
            });
        }
    }
};

window.QRScanner = QRScanner;