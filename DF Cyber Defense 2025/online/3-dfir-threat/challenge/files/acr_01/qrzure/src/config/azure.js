const { BlobServiceClient, generateBlobSASQueryParameters, ContainerSASPermissions } = require('@azure/storage-blob');
const { DefaultAzureCredential } = require('@azure/identity');

const AZURE_STORAGE_ACCOUNT_NAME = process.env.AZURE_STORAGE_ACCOUNT_NAME;
const AZURE_STORAGE_CONTAINER_NAME = process.env.AZURE_STORAGE_CONTAINER_NAME || 'qrcodes';

let blobServiceClient, containerClient;

if (AZURE_STORAGE_ACCOUNT_NAME) {
    const credential = new DefaultAzureCredential();
    blobServiceClient = new BlobServiceClient(
        `https://${AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net`,
        credential
    );
    containerClient = blobServiceClient.getContainerClient(AZURE_STORAGE_CONTAINER_NAME);
}

module.exports = {
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_CONTAINER_NAME,
    blobServiceClient,
    containerClient
};