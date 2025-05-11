// API configuration
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// App configuration
export const APP_NAME = 'Quantity Automation Tool';
export const APP_VERSION = '1.0.0';

// Pagination defaults
export const DEFAULT_PAGE_SIZE = 20;

// Refresh intervals (in milliseconds)
export const TASK_REFRESH_INTERVAL = 10000; // 10 seconds (increased from 2 seconds)
export const PRODUCT_REFRESH_INTERVAL = 30000; // 30 seconds