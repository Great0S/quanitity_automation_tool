import axios from 'axios';
import { API_URL } from '../config';

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_URL,
  withCredentials: false // Explicitly set to false for cross-origin requests
});

// Add token to all requests if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const loginUser = async (username: string, password: string) => {
  try {
    console.log(`Attempting to login with username: ${username} to ${API_URL}/token`);
    
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    console.log('Login successful, received token');
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    
    return { username };
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

export const checkAuthStatus = async () => {
  const token = localStorage.getItem('token');
  if (!token) {
    return null;
  }
  
  try {
    // Try to access a protected endpoint to verify token
    const response = await api.get('/platforms');
    return { username: 'user' }; // We don't have user details in the token, so return a placeholder
  } catch (error) {
    console.error('Auth check failed:', error);
    localStorage.removeItem('token');
    return null;
  }
};

export default api;