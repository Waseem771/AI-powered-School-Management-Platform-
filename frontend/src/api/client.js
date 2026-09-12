import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token from localStorage if available
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
        localStorage.removeItem('educore_token');
        localStorage.removeItem('educore_user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  login: (username, password) => client.post('/auth/login', { username, password }),
  getMe: () => client.get('/auth/me'),

  // Students
  getStudents: (params) => client.get('/students', { params }),
  getStudent: (id) => client.get(`/students/${id}`),
  createStudent: (data) => client.post('/students', data),
  updateStudent: (id, data) => client.put(`/students/${id}`, data),
  deleteStudent: (id) => client.delete(`/students/${id}`),

  // Fees
  getFees: (params) => client.get('/fees', { params }),
  generateChallan: (data) => client.post('/fees/generate', data),
  payInvoice: (id, data) => client.post(`/fees/${id}/pay`, data),
  getChallanPdfUrl: (invoiceId) => `${API_BASE_URL}/fees/${invoiceId}/pdf`,

  // Results
  getStudentResults: (studentId) => client.get(`/results/${studentId}`),
  enterMarks: (data) => client.post('/results', data),
  getReportCardPdfUrl: (studentId) => `${API_BASE_URL}/results/${studentId}/report-card/pdf`,

  // Dashboard
  getDashboardStats: () => client.get('/dashboard/stats'),

  // AI At-Risk
  getAtRiskStudents: (params) => client.get('/ai/at-risk', { params }),
  getStudentRiskDetail: (studentId) => client.get(`/ai/at-risk/${studentId}`),

  // Chatbot
  askChatbot: (question) => client.post('/chatbot/ask', { question }),
  getChatbotTopics: () => client.get('/chatbot/topics'),
};

export default client;
