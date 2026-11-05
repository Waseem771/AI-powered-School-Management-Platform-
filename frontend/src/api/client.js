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
  getStudents: (params, options) => client.get('/students', { params, ...options }),
  getStudent: (id, options) => client.get(`/students/${id}`, options),
  createStudent: (data) => client.post('/students', data),
  updateStudent: (id, data) => client.put(`/students/${id}`, data),
  deleteStudent: (id) => client.delete(`/students/${id}`),
  archiveStudent: (id) => client.post(`/students/${id}/archive`),
  restoreStudent: (id) => client.post(`/students/${id}/restore`),

  // Fees
  getFees: (params, options) => client.get('/fees', { params, ...options }),
  getStudentFeeSummary: (studentId, options) => client.get(`/fees/student/${studentId}/summary`, options),
  getReceiptPdf: (paymentId) =>
    client.get(`/fees/payments/${paymentId}/receipt`, { responseType: 'blob' }).then((response) => response.data),
  getFeeSummary: () => client.get('/fees/summary'),
  getInvoicePayments: (invoiceId, options) => client.get(`/fees/${invoiceId}/payments`, options),
  generateChallan: (data) => client.post('/fees/generate', data),
  payInvoice: (id, data) => client.post(`/fees/${id}/pay`, data),
  getChallanPdf: (invoiceId) =>
    client.get(`/fees/${invoiceId}/pdf`, { responseType: 'blob' }).then((response) => response.data),

  // Results
  getStudentResults: (studentId, params, options) => client.get(`/results/${studentId}`, { params, ...options }),
  getClassMarks: (params, options) => client.get('/results/class', { params, ...options }),
  saveClassMarks: (data) => client.post('/results/class', data),
  enterMarks: (data) => client.post('/results', data),
  getReportCardPdf: (studentId, params) =>
    client
      .get(`/results/${studentId}/report-card/pdf`, { params, responseType: 'blob' })
      .then((response) => response.data),

  // Dashboard
  getDashboardStats: (options) => client.get('/dashboard/stats', options),
  getSchoolInfo: (options) => client.get('/school/info', options),
  getPublicSchool: (options) => client.get('/school/public', options),
  getRecentActivity: (options) => client.get('/dashboard/activity', options),

  // AI At-Risk
  getAtRiskStudents: (params) => client.get('/ai/at-risk', { params }),
  getStudentRiskDetail: (studentId, options) => client.get(`/ai/at-risk/${studentId}`, options),
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
