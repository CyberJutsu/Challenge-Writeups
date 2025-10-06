const QRCode = require('qrcode');
const Jimp = require('jimp');
const QrCode = require('qrcode-reader');
const ejs = require('ejs');
const { containerClient, blobServiceClient, AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_CONTAINER_NAME } = require('../config/azure');
const { generateBlobSASQueryParameters, ContainerSASPermissions } = require('@azure/storage-blob');

class QRService {
    async generatePaymentQR(paymentData) {
        const jsonString = JSON.stringify(paymentData);
        console.log('Generating QR for data:', jsonString);
        
        // Generate QR with specific options for better scanning
        const qrBuffer = await QRCode.toBuffer(jsonString, { 
            type: 'png',
            width: 300,
            margin: 4,
            color: {
                dark: '#000000',
                light: '#FFFFFF'
            },
            errorCorrectionLevel: 'M'
        });
        
        console.log('Generated QR buffer size:', qrBuffer.length);
        
        if (containerClient) {
            return await this.uploadToAzure(qrBuffer);
        } else {
            const base64 = qrBuffer.toString('base64');
            console.log('Generated base64 length:', base64.length);
            return `data:image/png;base64,${base64}`;
        }
    }

    async uploadToAzure(qrBuffer) {
        await containerClient.createIfNotExists();
        const blobName = `qr_${Date.now()}_${Math.floor(Math.random()*10000)}.png`;
        const blockBlobClient = containerClient.getBlockBlobClient(blobName);
        
        await blockBlobClient.uploadData(qrBuffer, {
            blobHTTPHeaders: { blobContentType: 'image/png' }
        });

        const userDelegationKey = await blobServiceClient.getUserDelegationKey(
            new Date(),
            new Date(new Date().valueOf() + 60 * 60 * 1000)
        );

        const sasOptions = {
            containerName: AZURE_STORAGE_CONTAINER_NAME,
            permissions: ContainerSASPermissions.parse("rl"),
            startsOn: new Date(),
            expiresOn: new Date(new Date().valueOf() + 60 * 60 * 1000),
        };

        const sasToken = generateBlobSASQueryParameters(
            sasOptions,
            userDelegationKey,
            AZURE_STORAGE_ACCOUNT_NAME
        ).toString();

        return `${blockBlobClient.url}?${sasToken}`;
    }

    async scanQRCode(imageSource, isFile = true) {
        try {
            console.log('Scanning QR code, isFile:', isFile);
            
            let originalImage;
            if (isFile) {
                console.log('Reading image from buffer, size:', imageSource.length);
                originalImage = await Jimp.read(imageSource);
            } else {
                console.log('Reading image from URL:', imageSource);
                originalImage = await Jimp.read(imageSource);
            }
            
            console.log('Original image:', originalImage.bitmap.width, 'x', originalImage.bitmap.height);
            
            // Try multiple preprocessing approaches
            const preprocessingMethods = [
                (img) => img.clone().greyscale(), // Simple grayscale
                (img) => img.clone().greyscale().contrast(0.5), // Grayscale with contrast
                (img) => img.clone().greyscale().normalize(), // Normalized grayscale
                (img) => img.clone().greyscale().contrast(0.8).brightness(0.1), // High contrast
                (img) => {
                    // Resize if too small
                    const minSize = 200;
                    if (img.bitmap.width < minSize || img.bitmap.height < minSize) {
                        const scale = minSize / Math.min(img.bitmap.width, img.bitmap.height);
                        return img.clone().scale(scale).greyscale();
                    }
                    return img.clone().greyscale();
                },
                (img) => {
                    // Resize if too large
                    const maxSize = 800;
                    if (img.bitmap.width > maxSize || img.bitmap.height > maxSize) {
                        const scale = maxSize / Math.max(img.bitmap.width, img.bitmap.height);
                        return img.clone().scale(scale).greyscale();
                    }
                    return img.clone().greyscale();
                }
            ];
            
            // Try each preprocessing method
            for (let i = 0; i < preprocessingMethods.length; i++) {
                try {
                    console.log(`Trying preprocessing method ${i + 1}/${preprocessingMethods.length}`);
                    const processedImage = preprocessingMethods[i](originalImage);
                    console.log('Processed image size:', processedImage.bitmap.width, 'x', processedImage.bitmap.height);
                    
                    const result = await this.tryDecodeQR(processedImage);
                    if (result) {
                        console.log('Successfully decoded with method', i + 1);
                        return result;
                    }
                } catch (error) {
                    console.log(`Method ${i + 1} failed:`, error.message);
                    continue;
                }
            }
            
            throw new Error('Could not decode QR code with any preprocessing method. Please ensure the image contains a clear, readable QR code.');
            
        } catch (imageError) {
            console.error('Image processing error:', imageError);
            throw new Error(`Failed to process image: ${imageError.message}`);
        }
    }

    async tryDecodeQR(image) {
        return new Promise((resolve, reject) => {
            const qr = new QrCode();
            
            // Set a shorter timeout for each attempt
            const timeout = setTimeout(() => {
                reject(new Error('Decode timeout'));
            }, 3000);
            
            qr.callback = function(err, value) {
                clearTimeout(timeout);
                
                if (err) {
                    return reject(new Error(`Decode error: ${err.message || err}`));
                }
                
                if (!value || !value.result) {
                    return reject(new Error('No QR data found'));
                }
                
                let scanQrData = value.result;
                console.log('Successfully decoded QR data:', scanQrData);
                
                // Try to parse as JSON, but don't require it
                let dataObj = {};
                try {
                    dataObj = JSON.parse(scanQrData);
                    console.log('Parsed as JSON:', dataObj);
                } catch (e) {
                    console.log('QR data is plain text, not JSON');
                    return resolve({ 
                        scanQrData, 
                        scanMessage: scanQrData,
                        message: scanQrData 
                    });
                }
                
                // Render message template if it exists
                let scanMessage = '';
                try {
                    scanMessage = ejs.render(dataObj.message || '', {});
                } catch (e) {
                    console.warn('EJS render error:', e.message);
                    scanMessage = dataObj.message || '';
                }
                
                resolve({ scanQrData, scanMessage, ...dataObj });
            };
            
            try {
                qr.decode(image.bitmap);
            } catch (decodeError) {
                clearTimeout(timeout);
                reject(new Error(`Decode exception: ${decodeError.message}`));
            }
        });
    }

    validatePaymentData(data) {
        const { amount, recipient } = data;
        
        if (!amount || !recipient) {
            throw new Error('Amount and recipient are required');
        }
        
        if (isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
            throw new Error('Amount must be a positive number');
        }
        
        if (typeof recipient !== 'string' || recipient.trim().length === 0) {
            throw new Error('Recipient must be a valid string');
        }
        
        return true;
    }
}

module.exports = new QRService();