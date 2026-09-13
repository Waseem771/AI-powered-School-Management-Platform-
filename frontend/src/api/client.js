import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? 'https://whassanshaikh--educore-ai-school-platform-fastapi-app.modal.run'
    : 'http://localhost:8000');

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
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
  logout: () => client.post('/auth/logout'),
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
  getDashboardStats: (options) => client.get('/dashboard/stats', options),

  // AI At-Risk
  getAtRiskStudents: (params) => client.get('/ai/at-risk', { params }),
  getStudentRiskDetail: (studentId) => client.get(`/ai/at-risk/${studentId}`),

  // Chatbot
  askChatbot: (payload, options) => {
    const body = typeof payload === 'string' ? { question: payload } : payload;
    return client.post('/chatbot/ask', body, options);
  },
  getChatHistory: (sessionId) => client.get(`/chatbot/history/${sessionId}`),
  clearChatHistory: (sessionId) => client.delete(`/chatbot/history/${sessionId}`),
  getChatbotTopics: () => client.get('/chatbot/topics'),
};

export default client;
