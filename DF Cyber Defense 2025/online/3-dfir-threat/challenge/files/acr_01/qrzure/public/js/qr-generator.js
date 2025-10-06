// QR Generation module
const QRGenerator = {
    async generate(formData) {
        try {
            Utils.showLoading();

            const response = await fetch(API_ENDPOINTS.PAYMENT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Failed to generate QR code (${response.status})`);
            }

            const result = await response.json();
            this.displayResult(result);
            Utils.showSuccess('QR code generated successfully!');

        } catch (error) {
            console.error('QR generation error:', error);
            const errorMessage = error.message || 'Failed to generate QR code';
            Utils.showError(errorMessage);
        } finally {
            Utils.hideLoading();
        }
    },

    displayResult(result) {
        const container = document.getElementById('generate-result');
        const { qrUrl, paymentData } = result;
        
        // Update the QR preview image
        document.getElementById('qrImage').src = qrUrl;
        
        // Clear container
        container.innerHTML = '';
        
        // Create elements safely
        const h3 = document.createElement('h3');
        h3.textContent = 'Payment QR Code Generated';
        
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'payment-details';
        
        const amountP = document.createElement('p');
        amountP.innerHTML = '<strong>Amount:</strong> $';
        amountP.appendChild(document.createTextNode(paymentData.amount));
        
        const recipientP = document.createElement('p');
        recipientP.innerHTML = '<strong>Recipient:</strong> ';
        recipientP.appendChild(document.createTextNode(paymentData.recipient));
        
        const messageP = document.createElement('p');
        messageP.innerHTML = '<strong>Message:</strong> ';
        messageP.appendChild(document.createTextNode(paymentData.message || 'No message'));
        
        const timestampP = document.createElement('p');
        timestampP.innerHTML = '<strong>Generated:</strong> ';
        timestampP.appendChild(document.createTextNode(new Date(paymentData.timestamp).toLocaleString()));
        
        detailsDiv.appendChild(amountP);
        detailsDiv.appendChild(recipientP);
        detailsDiv.appendChild(messageP);
        detailsDiv.appendChild(timestampP);
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'qr-actions';
        
        const downloadLink = document.createElement('a');
        downloadLink.href = qrUrl;
        downloadLink.download = 'payment-qr.png';
        downloadLink.className = 'btn';
        downloadLink.textContent = 'Download QR Code';
        
        actionsDiv.appendChild(downloadLink);
        
        container.appendChild(h3);
        container.appendChild(detailsDiv);
        container.appendChild(actionsDiv);
        
        container.style.display = 'block';
    },

    updatePreview() {
        const amount = document.getElementById('amount').value;
        const recipient = document.getElementById('recipient').value;
        const message = document.getElementById('message').value;
        
        if (amount && recipient) {
            const previewData = `Payment: $${amount} to ${recipient}${message ? ` - ${message}` : ''}`;
            const encodedData = encodeURIComponent(previewData);
            document.getElementById('qrImage').src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodedData}`;
        } else {
            document.getElementById('qrImage').src = "https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=Example";
        }
    },

    initializeForm() {
        const form = document.getElementById('generateForm');
        if (!form || form.dataset.initialized) return;
        form.dataset.initialized = 'true';

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const formData = {
                amount: document.getElementById('amount').value,
                recipient: document.getElementById('recipient').value,
                message: document.getElementById('message').value
            };
            
            if (!formData.amount || !formData.recipient) {
                Utils.showError('Please fill in all required fields');
                return;
            }
            
            const amount = parseFloat(formData.amount);
            if (isNaN(amount) || amount <= 0) {
                Utils.showError('Amount must be a positive number');
                return;
            }
            
            this.generate(formData);
        });

        ['amount', 'recipient', 'message'].forEach(id => {
            const element = document.getElementById(id);
            if (element && !element.dataset.previewInitialized) {
                element.dataset.previewInitialized = 'true';
                element.addEventListener('input', this.updatePreview);
            }
        });
    }
};

window.QRGenerator = QRGenerator;