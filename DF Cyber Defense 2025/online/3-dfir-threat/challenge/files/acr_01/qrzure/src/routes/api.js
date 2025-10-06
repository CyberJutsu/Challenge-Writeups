const express = require('express');
const qrService = require('../services/qrService');
const upload = require('../middleware/upload');

const router = express.Router();

router.post('/payment', async (req, res) => {
    try {
        const { amount, recipient, message } = req.body;
        
        qrService.validatePaymentData({ amount, recipient });
        
        const paymentData = {
            amount: amount,
            recipient: recipient,
            message: message || '',
            timestamp: new Date().toISOString()
        };
        
        const qrUrl = await qrService.generatePaymentQR(paymentData);
        
        res.json({ qrUrl, paymentData });
    } catch (error) {
        console.error('Payment QR generation error:', error);
        res.status(400).json({ error: error.message });
    }
});

router.post('/scan', upload.single('qrimage'), async (req, res) => {
    try {
        let imageSource;
        let isFile = true;
        
        if (req.file) {
            imageSource = req.file.buffer;
            isFile = true;
        } else if (req.body.imageUrl) {
            imageSource = req.body.imageUrl;
            isFile = false;
        } else {
            return res.status(400).json({ error: 'No image provided. Please upload a file or provide a URL.' });
        }
        
        const result = await qrService.scanQRCode(imageSource, isFile);
        res.json(result);
        
    } catch (error) {
        console.error('QR scan error:', error);
        res.status(400).json({ error: error.message });
    }
});

module.exports = router;