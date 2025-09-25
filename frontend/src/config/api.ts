// API Configuration for Client Management System
// Handles environment-specific API URLs

// PRODUCTION API Configuration - Updated to match your actual Azure deployment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV 
    ? 'http://localhost:8000'  // Development
    : 'https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net'  // Your actual production URL
  );

// Export API configuration
export const apiConfig = {
  baseURL: API_BASE_URL,
  endpoints: {
    clients: '/api/clients/',
    caseNotes: '/api/case-notes/',
    staff: '/api/staff/',
  },
  headers: {
    'Content-Type': 'application/json',
  }
};

// Helper function to get full API URL
export const getApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};

// Export base URL for backward compatibility
export const __API_URL__ = API_BASE_URL;

export default apiConfig;
