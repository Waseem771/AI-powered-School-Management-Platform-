import axios from 'axios';
import { clearSession } from '../lib/session';

// Production builds get this from VITE_API_URL (see frontend/.env.production).
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically attach Bearer token from localStorage for cross-domain auth
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('educore_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept 401s and redirect to login if session expires
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // If unauthorized on protected route, redirect to login
      if (window.location.pathname !== '/login') {
        clearSession();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  login: (username, password) => client.post('/auth/login', { username, password }),
  logout: () => client.post('/auth/logout'),
  changePassword: (currentPassword, newPassword) =>
    client.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
  getMe: () => client.get('/auth/me'),

  // Students
  getStudents: (params) => client.get('/students', { params }),
  getStudent: (id) => client.get(`/students/${id}`),
  createStudent: (data) => client.post('/students', data),
  updateStudent: (id, data) => client.put(`/students/${id}`, data),
  deleteStudent: (id) => client.delete(`/students/${id}`),
  archiveStudent: (id) => client.post(`/students/${id}/archive`),
  restoreStudent: (id) => client.post(`/students/${id}/restore`),

  // Fees
  getFees: (params) => client.get('/fees', { params }),
  getFeeSummary: () => client.get('/fees/summary'),
  getInvoicePayments: (invoiceId) => client.get(`/fees/${invoiceId}/payments`),
  generateChallan: (data) => client.post('/fees/generate', data),
  payInvoice: (id, data) => client.post(`/fees/${id}/pay`, data),
  getChallanPdf: (invoiceId) =>
    client.get(`/fees/${invoiceId}/pdf`, { responseType: 'blob' }).then((response) => response.data),

  // Results
  getStudentResults: (studentId, params) => client.get(`/results/${studentId}`, { params }),
  enterMarks: (data) => client.post('/results', data),
  getReportCardPdf: (studentId, params) =>
    client
      .get(`/results/${studentId}/report-card/pdf`, { params, responseType: 'blob' })
      .then((response) => response.data),

  // Dashboard
  getDashboardStats: (options) => client.get('/dashboard/stats', options),

  // AI At-Risk
  getAtRiskStudents: (params) => client.get('/ai/at-risk', { params }),
  getStudentRiskDetail: (studentId) => client.get(`/ai/at-risk/${studentId}`),
  simulateRisk: (payload, options) => client.post('/ai/simulate', payload, options),

  // Chatbot
  askChatbot: (payload, options) => {
    const body = typeof payload === 'string' ? { question: payload } : payload;
    return client.post('/chatbot/ask', body, options);
  },
  getChatHistory: (sessionId) => client.get(`/chatbot/history/${sessionId}`),
  clearChatHistory: (sessionId) => client.delete(`/chatbot/history/${sessionId}`),
  getChatbotTopics: () => client.get('/chatbot/topics'),
  getChatbotStatus: () => client.get('/chatbot/status'),
};

export default client;
