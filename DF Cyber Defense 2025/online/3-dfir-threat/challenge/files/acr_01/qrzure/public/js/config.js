// API Configuration
const API_BASE_URL = '/api';

// API Endpoints
const API_ENDPOINTS = {
    PAYMENT: `${API_BASE_URL}/payment`,
    SCAN: `${API_BASE_URL}/scan`
};

// Export for use in other modules
window.API_BASE_URL = API_BASE_URL;
window.API_ENDPOINTS = API_ENDPOINTS;