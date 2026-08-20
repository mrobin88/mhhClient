// API Configuration for Client Management System
// Handles environment-specific API URLs

// Development stays same-origin and uses Vite's /api proxy. Production builds
// must provide the deployed API host through an environment variable.
const API_BASE_URL = import.meta.env.DEV
  ? ''
  : (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '');

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
