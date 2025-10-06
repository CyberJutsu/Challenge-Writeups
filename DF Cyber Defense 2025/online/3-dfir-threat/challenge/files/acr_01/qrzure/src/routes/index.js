const express = require('express');
const { AZURE_STORAGE_ACCOUNT_NAME } = require('../config/azure');

const router = express.Router();

router.get('/', (req, res) => {
    res.render('main', {
        title: 'Payment QR & Scan',
        activeTab: 'generate',
        error: null,
        qrData: null,
        paymentData: null,
        scanError: null,
        scanQrData: null,
        scanMessage: null,
        storageAccount: AZURE_STORAGE_ACCOUNT_NAME
    });
});

module.exports = router;