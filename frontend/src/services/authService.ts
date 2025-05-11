import axios from 'axios';
import { API_URL } from '../config';

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_URL
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
    const response = await api.post('/token', new URLSearchParams({
      username,
      password
    }), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
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
    localStorage.removeItem('token');
    return null;
  }
};

export default api;